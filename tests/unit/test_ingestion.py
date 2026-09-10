from pathlib import Path
from skein.ingestion.pipeline import IncrementalIngester
from skein.store import LocalGraphStore

def test_incremental_ingestion(tmp_path: Path):
    (tmp_path/"app.py").write_text("def b():\n    return 1\n\ndef a():\n    return b()\n")
    s=LocalGraphStore(); ing=IncrementalIngester(tmp_path,s)
    r=ing.ingest(); assert r.added_files==1
    assert any(d.get('type')=='CALLS' for _,_,d in s.graph.edges(data=True))
    r2=ing.ingest(); assert r2.unchanged_files==1
    (tmp_path/"app.py").write_text("def b():\n    return 2\n\ndef a():\n    return b()\n")
    r3=ing.ingest(); assert r3.changed_files==1
