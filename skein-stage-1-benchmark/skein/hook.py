from pathlib import Path
HOOK='''#!/bin/sh\n# Skein incremental post-commit hook\nskein ingest .\n'''
def install(root:Path):
    path=root/".git"/"hooks"/"post-commit"
    if not path.parent.exists(): raise FileNotFoundError(f"Not a git repository: {root}")
    path.write_text(HOOK); path.chmod(0o755); return path
