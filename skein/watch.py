from __future__ import annotations
import time
from pathlib import Path
from .ingestion.pipeline import IncrementalIngester
from .store import LocalGraphStore

def watch(root:Path, interval:float=2.0):
    graph=root/".skein"/"graph.json"; store=LocalGraphStore.load(graph) if graph.exists() else LocalGraphStore()
    ing=IncrementalIngester(root,store)
    while True:
        report=ing.ingest(); store.save(graph)
        if report.changed_files or report.added_files or report.removed_files: print(report)
        time.sleep(interval)
