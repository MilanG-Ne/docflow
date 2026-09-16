# Approved sample

These files were downloaded from DocFlow after generating the fictional Meridian Supply proposal and approving revision 1. They contain no real client data. The review was made by the seeded Jamie Lee demo account.

`approval-record.json` stores the decision, revision content hash, and the SHA-256 hashes of the exact Word and PDF bytes. The documents themselves are not modified after approval. To verify the sample from the repository root:

```sh
python3 - <<'PY'
import hashlib
import json
from pathlib import Path

folder = Path('examples/generated')
record = json.loads((folder / 'approval-record.json').read_text())
for kind, expected in record['artifact_hashes'].items():
    actual = hashlib.sha256((folder / f'approved-proposal.{kind}').read_bytes()).hexdigest()
    assert actual == expected, f'{kind} does not match the approval record'
    print(f'{kind}: verified')
PY
```

Generating the same content again can produce different bytes because document metadata and conversion output can vary. Compare each download with its own approval record rather than expecting every run to match this fixture.
