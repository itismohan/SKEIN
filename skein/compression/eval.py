from __future__ import annotations
import json
from pathlib import Path
from .core import compress

def run_eval(path: Path) -> dict:
    cases=json.loads(path.read_text(encoding='utf-8'))
    outcomes=[]; misses=0; total=0; saved=[]
    for c in cases:
        r=compress(c['text'], aggressiveness=c.get('aggressiveness','balanced'))
        expected=set(x.lower() for x in c.get('must_contain',[]))
        actual=r.compressed.lower()
        missing=sorted(x for x in expected if x not in actual)
        misses += len(missing); total += len(expected)
        outcomes.append({'id':c['id'],'outcome':r.outcome,'missing':missing,'original_tokens':r.original_tokens,'compressed_tokens':r.compressed_tokens})
        saved.append(max(0,r.original_tokens-r.compressed_tokens))
    false_negative_rate=misses/total if total else 0
    return {'cases':len(cases),'checklist_items':total,'missed_items':misses,'false_negative_rate':false_negative_rate,'avg_tokens_saved':sum(saved)/len(saved) if saved else 0,'passed':misses==0,'outcomes':outcomes}
