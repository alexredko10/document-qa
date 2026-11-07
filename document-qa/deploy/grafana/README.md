# Document QA observability

The Grafana Argo CD Application combines chart 13.5.0 with the Git-managed Kustomize ConfigMap. The chart mounts the JSON and provisions it through a file provider, so the dashboard survives Pod recreation without Grafana persistence. The Prometheus datasource UID is `prometheus`. ConfigMap volume refresh and the provider's 30-second poll can delay updates. No sidecar or additional RBAC is needed.

HTTP metrics retain their names and labels; unmatched paths use `unmatched`, nonstandard methods use `OTHER`, and scrapes are excluded. `llm_calls_total{provider,outcome}` counts stub and OpenRouter calls with outcomes `success`, `error`, `timeout`, `rate_limited`; `llm_call_duration_seconds{provider}` times successes and failures. `llm_tokens_total{provider,direction}` records only valid input/output usage returned by OpenRouter. No cost metric is emitted because no trusted cost or configured pricing is available. No sensitive content or model names are labels.

Token counters represent provider-reported consumption, including valid usage returned with a provider error or a response that fails subsequent validation. They do not represent only successful answers; absent or invalid usage is not estimated, and the stub produces no token counts.

## SLOs and proposed alerts

Eligible requests exclude `route=~"/healthz|/metrics"`. Evaluate these only with at least 30 days of retained samples; the current Prometheus has **24-hour retention and ephemeral storage**, so it cannot evaluate these 30-day SLOs reliably, especially across restarts. Durable 30-day storage is a separate operational decision. Missing data or no requests means insufficient data, not a successful SLO.

Availability objective: at least 99.5% of eligible requests return non-5xx in 30 days:

```promql
1 - (sum(increase(http_requests_total{route!~"/healthz|/metrics",status=~"5.."}[30d])) or vector(0)) / sum(increase(http_requests_total{route!~"/healthz|/metrics"}[30d]))
```

Latency objective: at least 95% of eligible requests finish at or below 1 second in 30 days (the `le="1.0"` histogram bucket includes its boundary):

```promql
sum(increase(http_request_duration_seconds_bucket{route!~"/healthz|/metrics",le="1.0"}[30d])) / sum(increase(http_request_duration_seconds_count{route!~"/healthz|/metrics"}[30d]))
```

Proposed alert expressions, after sufficient retention and traffic, are the respective expressions above followed by `< 0.995` and `< 0.95`, with `for: 15m`. Also alert separately on `up{job="document-qa"} == 0` and `absent(up{job="document-qa"})`. These are proposals only; alert rules and delivery are not deployed. A 30-day trailing SLO breach is slow to detect; add burn-rate alerts once alerting and reliable storage exist.

Runbook: check target availability and scrape configuration first; inspect HTTP route/status and latency panels, then LLM failures and latency. Check application and provider logs without exposing prompts or credentials. For rate limits/timeouts check provider status and configuration; for application errors inspect recent changes and roll back if needed. Confirm recovery and review impact. If data is missing, check Prometheus retention, restart history and scraping before interpreting an SLO.

## Validation and operation

From the repository root run `(cd document-qa-prototype && .venv/bin/python -m pytest)`, `python -m json.tool document-qa/deploy/grafana/document-qa.json`, and `kubectl kustomize document-qa/deploy/grafana` (or `kustomize build`). Render chart 13.5.0 with the Application's Helm values when the chart is available. Check the Argo CD diff and sync health. Use existing private access to Grafana, open **Document QA — Service Overview**, verify target UP and exercise a request; compare panel data with Explore and `/metrics`. Token panels can legitimately have no data.

The Applications are manually bootstrapped: after reviewing and committing a revision available at `main`, the operator must apply the updated `document-qa/deploy/argocd/grafana.yaml` Application once using their approved Argo CD bootstrap procedure. A Git push alone does not update that Application. Argo CD then syncs the chart and Git dashboard source. Do not expose the services publicly.

For rollback, revert the reviewed Git changes and apply the previous Grafana Application manifest through the same bootstrap procedure, then sync and inspect Argo CD. The old Application removes the dashboard mount/provider; because prune is disabled, the ConfigMap may remain and can be removed separately by an operator after verification. Roll back the application deployment to its prior revision using its normal Argo CD procedure. No changes here deploy alerts or alter infrastructure.
