
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

A future Loki pipeline can ingest these JSON fields and use the request ID for correlation; future OpenTelemetry instrumentation can add real trace context. Neither is installed or simulated here.
