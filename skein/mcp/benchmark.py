from __future__ import annotations

def measure_duplicate_context(agent_count:int=3, shared:bool=True)->dict:
    # Baseline: each agent independently builds repository context. Shared mode builds once and reuses it.
    baseline_calls=agent_count
    shared_calls=1
    return {'agents':agent_count,'baseline_context_calls':baseline_calls,'shared_graph_context_calls':shared_calls,'calls_reduced':baseline_calls-shared_calls,'reduction_pct':(1-shared_calls/baseline_calls)*100}
