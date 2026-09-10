# Commerce Service Benchmark Fixture

A small but realistic Python service used by Skein's Stage 1 retrieval benchmark.
It models an e-commerce order flow with API, domain, service, repository, worker,
test, and architecture documentation layers.

This fixture is intentionally deterministic and self-contained. It is not a
production application; it is a benchmark corpus designed to test whether a
repository graph can answer structural questions with less context than a
whole-repository prompt.
