from pathlib import Path
from skein.compression.eval import run_eval

def test_release_eval_gate():
    result=run_eval(Path('eval/compression_eval.json'))
    assert result['cases'] >= 100
    assert result['false_negative_rate'] == 0
    assert result['passed']
