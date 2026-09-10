from pathlib import Path
import os
from skein.versioning import VersionedGraphStore
from skein.pr_report import markdown_report

root=Path(os.environ.get("SKEIN_ROOT", "."))
base=os.environ.get("SKEIN_BASE")
head=os.environ.get("SKEIN_HEAD")
if not base:
    raise SystemExit("SKEIN_BASE is required")
text=markdown_report(VersionedGraphStore(root/".skein"/"history"), base, head)
out=Path(os.environ.get("SKEIN_REPORT", "skein-pr-report.md"))
out.write_text(text, encoding="utf-8")
print(out)
