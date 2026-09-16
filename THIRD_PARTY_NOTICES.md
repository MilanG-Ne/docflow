# Third-party notices

DocFlow's project code is MIT-licensed. Dependencies and upstream assets retain their own licenses; the project's license does not replace them.

- The components in `frontend/components/ui/` are adapted from [shadcn/ui](https://github.com/shadcn-ui/ui), copyright shadcn, under the MIT license. Their underlying primitives are provided by [Base UI](https://github.com/mui/base-ui).
- Icons are from [Lucide](https://github.com/lucide-icons/lucide), under the ISC license.
- The React/Vinext frontend began with the OpenAI Sites starter. DocFlow builds it as static assets for the local FastAPI server.
- The proposal template's page geometry and cover/table styles were adapted from the supplied OpenAI **Investment Committee Memo** document template. Proposal text, placeholders, and demo organizations are fictional.
- [docxtpl](https://github.com/elapouya/python-docx-template) is distributed under LGPL-2.1-only; [python-docx](https://github.com/python-openxml/python-docx) is MIT-licensed. These packages are installed as dependencies, without changes to their source.
- The Docker image installs [LibreOffice](https://www.libreoffice.org/about-us/licenses/) and Liberation fonts from Debian packages. Their license/copyright files are included with those packages under `/usr/share/doc/` in the image.

Other dependencies, including FastAPI, SQLAlchemy, Alembic, Psycopg, PostgreSQL, React, Vinext, and the build tools, retain their upstream notices. Exact JavaScript and Python versions are recorded in the committed lockfiles.

## MIT notice for adapted shadcn/ui components

Copyright (c) 2023 shadcn

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
