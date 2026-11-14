# Document QA Prototype

This application is part of a pet project exploring document question answering with retrieval-augmented generation. Upload a text document and ask questions using retrieved context. The local defaults use a stub LLM and hash embeddings; the private AWS deployment is configured for OpenRouter.

## Quickstart

From the repository root, using Python 3.12:

```sh
cd document-qa-prototype
python3.12 -m venv .venv
.venv/bin/python -m pip install -e '.[dev]'
LLM_PROVIDER=stub EMBEDDING_PROVIDER=hash OTEL_EXPORTER_OTLP_TRACES_ENDPOINT="" .venv/bin/python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --no-access-log
```

Open [http://127.0.0.1:8000/demo](http://127.0.0.1:8000/demo). Run the tests with `.venv/bin/python -m pytest -q` from the prototype directory.

## Observability

See the [metrics, dashboard, SLOs and deployment guide](../document-qa/deploy/grafana/README.md).

### Structured application logs

Application events are compact JSON lines on stdout. Every event has `timestamp` (UTC), `level`, `event`, and `request_id` (null outside a request). `LOG_LEVEL` defaults to `INFO`. The events are `http_request_completed` (bounded method, route template, status and duration in milliseconds), `http_request_failed` (safe `unexpected_error` classification), `llm_call_completed` (provider, configured model ID, outcome, duration and bounded failure reason), and `llm_usage_reported` (valid provider-reported input and/or output tokens). Health checks and metric scrapes do not emit completion events. Uvicorn access logs are disabled in the production container; its startup and error logs remain enabled and are not application JSON events.

A supplied `X-Request-ID` is accepted only when it consists of 1–64 ASCII letters, digits, underscores or hyphens; otherwise a random UUID-based ID is generated. The ID is returned in the response and follows calls into the synchronous route thread. Treat caller-provided IDs as public correlation identifiers, not credentials or sensitive content. Configure the model ID as a public provider model identifier, never a secret. No request bodies, raw paths, query strings, questions, excerpts, answers, credentials, provider messages or exception text are intentionally included in application events. Unexpected errors receive a generic response and a bounded error event; detailed exception traces are intentionally unavailable in those events.

For a deployment in namespace `qa`, inspect logs through authorized cluster access, for example:

```sh
kubectl logs -n qa deployment/qa-prototype --since=15m
kubectl logs -n qa deployment/qa-prototype --since=15m | jq -R 'fromjson? | select(.request_id == "example-id")'
kubectl logs -n qa deployment/qa-prototype --since=15m | jq -R 'fromjson? | select(.event == "llm_call_completed")'
kubectl logs -n qa deployment/qa-prototype --since=15m | jq -R 'fromjson? | select(.event == "http_request_failed" or (.event == "llm_call_completed" and .outcome != "success"))'
```

In the AWS deployment, Alloy forwards application logs to Loki for Grafana queries. OpenTelemetry tracing can export spans directly to Tempo; it is disabled locally when `OTEL_EXPORTER_OTLP_TRACES_ENDPOINT` is empty. See the [logging and tracing guide](../document-qa/deploy/logging/README.md) for endpoints and operational details.

## Demo console

From `document-qa-prototype`, start the service with `.venv/bin/python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --no-access-log` and open [http://localhost:8000/demo](http://localhost:8000/demo). The default StubLLM needs no credentials. Select **Load sample**, **Upload document**, and **Ask** to try the suggested question. You can instead paste text or select a local `.txt` file. The service is intended for private access; the console adds no authentication or public ingress.

### Local k6 load test

With k6 installed, start the API in one terminal and run the test in another, both from the repository root. The script is fixed to `127.0.0.1:8000`, uploads one synthetic document, and repeatedly asks a fixed relevant question using the local stub and hash providers:

```sh
# Terminal 1
cd document-qa-prototype
LLM_PROVIDER=stub EMBEDDING_PROVIDER=hash OTEL_EXPORTER_OTLP_TRACES_ENDPOINT="" .venv/bin/python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --no-access-log
```

```sh
# Terminal 2
cd document-qa-prototype
k6 run loadtest/ask.js
```

The single workload ramps to 5 VUs over 5 seconds, ramps to 10 VUs over the next 5 seconds, holds 10 VUs for 30 seconds, then ramps down to 0 over 10 seconds. k6 reports `/ask` throughput, latency percentiles and error rate; thresholds require HTTP failures below 1%, p95 under 1,000 ms and successful checks above 99%. These results measure the local FastAPI/RAG pipeline, not real OpenRouter latency or cloud capacity.

#### Local k6 benchmark — 8 November 2026

| Metric | Result |
| --- | --- |
| Throughput | 1,407 HTTP requests/second |
| RAG questions (`POST /ask`) | 70,369 |
| p95 HTTP latency | 8.2 ms |
| Average HTTP latency | 5.64 ms |
| HTTP failure rate | 0.00% |
| Successful checks | 100% (140,738 / 140,738) |
| k6 thresholds | All passed |

This 50-second run used one ramping-VUs scenario with a maximum of 10 VUs against the local FastAPI server using StubLLM and hash embeddings. It measures the local API and retrieval pipeline, not semantic embedding API calls, real LLM inference latency, or AWS capacity. Results depend on the test environment and workload.

The response keeps `answer` and `source_chunks` and adds `llm`. `invoked` is false for answers resolved locally. For a call, the provider and configured request model come from the selected adapter, latency is measured on the server, and the actual model, token counts and cost are included only when reported and valid. Router IDs such as `openrouter/free` are not treated as the actual responding model. Stub calls identify the actual model as `stub`, without token or cost estimates. OpenRouter usage can be absent, and reported cost may not represent the final account invoice. HTTP duration in the activity table is measured separately in the browser. Activity stays in memory in the current tab; restarting the service or Pod removes uploaded documents.

To correlate a request, copy its request ID from the session activity table and search in Grafana Explore using the Loki datasource and the private log stream, for example `{namespace="qa",app="qa-prototype",container="api"} | json | request_id="your-request-id"`. See the [logging guide](../document-qa/deploy/logging/README.md) for access, examples and retention limitations.

### Compare with and without document context

Leave **Use document context (RAG)** checked for the existing document-grounded path, or uncheck it to ask the configured generative provider without uploading a document. **Compare both** requires an uploaded document and sends two independent requests with the same question, configured model and temperature. The comparison shows each result, timings and request ID separately; source chunks appear only for RAG. Model routing may still select different actual models on separate provider calls, which is shown when reported. The context-free request sends only a general instruction and the question; it does not retrieve or send document content.

The default StubLLM supports RAG only: context-free requests return HTTP 501 with an explanation, and comparison displays that error beside the RAG result. For a full comparison, configure the existing `openrouter` provider and a suitable model locally using `LLM_PROVIDER`, `OPENROUTER_MODEL`, and `OPENROUTER_API_KEY` in your shell or other private secret mechanism before starting the server; never commit the key. Provider availability and billing depend on the configured account and model.

## Embeddings and retrieval

`EMBEDDING_PROVIDER=hash` (the default unless overridden in Helm values) uses deterministic 128-dimensional SHA-256 word hashing. This is a lexical baseline, not a semantic model. The existing lexical relevance gate and positive-cosine rule remain in place for it. Set `EMBEDDING_PROVIDER=openrouter`, `OPENROUTER_EMBEDDING_MODEL=openai/text-embedding-3-small` (the default model), and `OPENROUTER_API_KEY` through a private secret mechanism to use semantic embeddings independently of `LLM_PROVIDER`; StubLLM can still generate from the retrieved chunks. OpenRouter receives document text and questions and may charge for embeddings; review its [embedding API](https://openrouter.ai/docs/api/api-reference/embeddings/create-embeddings) and current model pricing before enabling it. Do not send sensitive content without considering the provider's data policies.

Semantic indexing accepts at most 256 chunks per document and returns HTTP 413 before any provider request when that limit is exceeded; the hash baseline has no chunk limit. Documents are embedded in batches of at most 32 chunks. Each response must report the configured model (or the known shortened OpenRouter name for `openai/text-embedding-3-small`) and contain one valid indexed finite vector per input, with consistent dimensions; semantic zero vectors are rejected. Documents are saved only after all batches succeed. Each document records provider, model and dimensions. At query time the current configuration and returned dimensions must match, otherwise the service returns 503 and the document must be re-uploaded under the new configuration. There is no automatic hash fallback. A provider timeout, rate limit, invalid response, or unavailable service also returns a safe 503. Embedding calls have a 20-second per-request timeout.

Semantic results are ranked by cosine similarity without an arbitrary cutoff or the lexical gate; even weak or negative similarities can be returned, so a retrieved chunk does not guarantee relevance. Empty/non-indexable documents are rejected; for the hash baseline, zero or non-overlapping query vectors and the lexical gate produce the existing local “I don't know” response without an LLM call. `/ask` includes optional `retrieval` metadata (provider, model and retrieval duration), and context-free requests do not invoke embeddings. The console identifies the retrieval method. `embedding_requests_total{provider,outcome}`, `embedding_request_duration_seconds{provider}`, and `embedding_tokens_total{provider}` are independent from LLM metrics. Tokens are counted only when valid provider input usage is reported. `embedding_request_completed` and `embedding_usage_reported` JSON events carry the request ID and safe operational fields; text and vectors are not logged.

Mock-vector tests check plumbing, compatibility and ranking, not real embedding model quality. To opt into a **paid, external** smoke test using only the script's synthetic text, configure the key privately and run:

```sh
RUN_OPENROUTER_EMBEDDING_TEST=1 .venv/bin/python -m scripts.manual_semantic_embeddings
```

The optional `OPENROUTER_EMBEDDING_MODEL` selects the model; the check passes only if the dog document scores above the train document and prints their cosine scores. This script is never run by the test suite. Restarting the Pod still loses documents and vectors; no deployment change is made by this configuration work.
