import hashlib
import subprocess
from pathlib import Path
from tempfile import TemporaryDirectory
from zipfile import BadZipFile, ZipFile

from docxtpl import DocxTemplate
from jinja2 import StrictUndefined, TemplateError
from jinja2.sandbox import SandboxedEnvironment
from lxml.etree import XMLSyntaxError

from .schemas import ProposalContent


class InvalidTemplate(Exception):
    """Permanent failure: retrying the same template cannot fix it."""


class ConversionError(Exception):
    """Potentially transient failure from the external converter."""


def file_hash(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def money(cents: int, currency: str) -> str:
    return f"{currency} {cents // 100:,}.{cents % 100:02d}"


def render_docx(
    template: Path, output: Path, content: ProposalContent, number: int, reference: str
):
    try:
        with ZipFile(template) as archive:
            if sum(i.file_size for i in archive.infolist()) > 10_000_000:
                raise InvalidTemplate("The template exceeds the 10 MB uncompressed limit")
            if "word/document.xml" not in archive.namelist():
                raise InvalidTemplate("The template is not a Word document")
        doc = DocxTemplate(template)
        context = content.model_dump(mode="json")
        context.update(
            {
                "revision": number,
                "reference": reference,
                "total": money(content.total_cents, content.currency),
                "fees": [
                    {
                        "description": row.description,
                        "background": "F6F6F6" if index % 2 == 0 else "FFFFFF",
                        "quantity": format(row.quantity, "f"),
                        "unit_price": money(row.unit_cents, content.currency),
                        "total": money(row.total_cents, content.currency),
                    }
                    for index, row in enumerate(content.line_items)
                ],
            }
        )
        doc.render(
            context,
            jinja_env=SandboxedEnvironment(undefined=StrictUndefined, autoescape=True),
            autoescape=True,
        )
        doc.save(output)
    except InvalidTemplate:
        raise
    except (BadZipFile, KeyError, TemplateError, XMLSyntaxError, ValueError) as exc:
        raise InvalidTemplate(
            "The Word template is invalid or contains an undefined field"
        ) from exc


def convert_pdf(docx: Path, output_dir: Path, binary: str) -> Path:
    with TemporaryDirectory(prefix="docflow-lo-") as profile:
        try:
            result = subprocess.run(
                [
                    binary,
                    f"-env:UserInstallation={Path(profile).as_uri()}",
                    "--headless",
                    "--nologo",
                    "--nodefault",
                    "--norestore",
                    "--convert-to",
                    "pdf:writer_pdf_Export",
                    "--outdir",
                    str(output_dir),
                    str(docx),
                ],
                capture_output=True,
                timeout=60,
                check=False,
            )
        except (OSError, subprocess.TimeoutExpired) as exc:
            raise ConversionError(
                "PDF conversion could not finish; check the document worker"
            ) from exc
    pdf = output_dir / f"{docx.stem}.pdf"
    if result.returncode or not pdf.is_file() or not pdf.read_bytes().startswith(b"%PDF-"):
        raise ConversionError("LibreOffice did not produce a valid PDF")
    return pdf


def generate(
    template: Path, directory: Path, content: dict, number: int, reference: str, binary: str
):
    directory.mkdir(parents=True, exist_ok=False)
    docx = directory / "proposal.docx"
    render_docx(template, docx, ProposalContent.model_validate(content), number, reference)
    pdf = convert_pdf(docx, directory, binary)
    return {"docx": docx, "pdf": pdf}
