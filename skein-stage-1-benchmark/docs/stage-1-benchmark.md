# Stage 1 Benchmark: Realistic Repository Fixture

## Objective

Measure whether Skein can answer structural repository questions with substantially less context than a whole-repository prompt, while preserving the relevant caller evidence.

## Fixture

`benchmarks/fixtures/commerce_service` is a deterministic e-commerce service corpus with:

- API controllers
- domain models
- order/payment/customer repositories
- order/payment/query services
- event workers
- tests
- architecture and operations documentation

It contains 27 ingestible source/document files and, in the current implementation, produces 100 graph nodes and 74 edges.

## Benchmark design

Six fixed questions use the Stage 1 structural query family:

1. what calls `create_order`?
2. what calls `pay_order`?
3. what calls `authorize_payment`?
4. what calls `cancel_order`?
5. what calls `get_order`?
6. what calls `health_check`?

For each question, the benchmark compares:

### Baseline

The complete supported repository text is supplied as context.

### Skein

The graph returns the target node plus its incoming `CALLS` relationships. Cross-file unresolved calls are resolved against unique function symbols and tagged `INFERRED`.

## Metrics

### Context efficiency

`token_reduction_pct = (1 - graph_tokens / raw_tokens) * 100`

Tokens are whitespace-delimited tokens. This is intentionally model-independent; a future evaluation can add tokenizer-specific counts.

### Retrieval precision

Of all function definitions represented in the retrieved context, what fraction are in the gold caller set?

### Retrieval recall

Of all gold callers, what fraction are represented in the retrieved context?

### F1

Harmonic mean of precision and recall.

## Current result

The generated report is `benchmarks/stage-1-commerce-results.json`.

Current measured result on the fixture:

| Metric | Whole repository | Skein graph context |
|---|---:|---:|
| Average context | 669.0 tokens | 31.83 tokens |
| Average reduction | — | **95.24%** |
| Average precision | 4.38% | **100%** |
| Average recall | 100% | **91.67%** |
| Average F1 | 8.38% | **94.44%** |

The result is deliberately treated as a Stage 1 engineering benchmark, not a claim about general LLM answer quality. The fixture and gold labels are fixed so changes to the parser/retrieval implementation can be compared reproducibly.

## Run it

```bash
python -m skein.cli init benchmarks/fixtures/commerce_service
python -m skein.cli ingest benchmarks/fixtures/commerce_service
python -m skein.cli benchmark-suite benchmarks/fixtures/commerce_service --output benchmarks/stage-1-commerce-results.json
```

## What this exposes

The benchmark demonstrates the intended value proposition, but it also exposes remaining Stage 1 gaps:

- method-call resolution is heuristic until Tree-sitter dependencies are available
- symbol resolution is intentionally conservative and only resolves unique names
- the benchmark measures structural evidence retrieval, not LLM answer correctness
- the current schema still uses `EXTRACTED` as a containment edge with a separate `confidence` attribute; this should be revisited before a schema 2.x contract

The next benchmark increment should add 30–50 questions spanning CALLS, IMPORTS, TESTS, traceability, and document-to-code links, plus a tokenizer-specific cost model.
