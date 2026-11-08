# Document QA observability

The Grafana Argo CD Application combines chart 13.5.0 with the Git-managed Kustomize ConfigMap. The chart mounts the JSON and provisions it through a file provider, so the dashboard survives Pod recreation without Grafana persistence. The Prometheus datasource UID is `prometheus`. ConfigMap volume refresh and the provider's 30-second poll can delay updates. No sidecar or additional RBAC is needed.

HTTP metrics retain their names and labels; unmatched paths use `unmatched`, nonstandard methods use `OTHER`, and scrapes are excluded. `llm_calls_total{provider,outcome}` counts stub and OpenRouter calls with outcomes `success`, `error`, `timeout`, `rate_limited`; `llm_call_duration_seconds{provider}` times successes and failures. `llm_tokens_total{provider,direction}` records only valid input/output usage returned by OpenRouter. No cost metric is emitted because no trusted cost or configured pricing is available. No sensitive content or model names are labels.

Token counters represent provider-reported consumption, including valid usage returned with a provider error or a response that fails subsequent validation. They do not represent only successful answers; absent or invalid usage is not estimated, and the stub produces no token counts.

## Lab SLOs and Prometheus alerts

These are demonstration targets, not long-term service commitments:

- Availability: at least 99% of eligible HTTP requests return non-5xx over a rolling 24 hours.
- LLM latency: OpenRouter call p95 stays below 20 seconds.
- Monitoring: the `document-qa` scrape target remains reachable.

Eligible HTTP requests exclude `/healthz` and `/metrics`. Example queries for the first two targets:

```promql
1 - (sum(increase(http_requests_total{job="document-qa",route!~"/healthz|/metrics",status=~"5.."}[24h])) or vector(0)) / sum(increase(http_requests_total{job="document-qa",route!~"/healthz|/metrics"}[24h]))
```

```promql
histogram_quantile(0.95, sum by (le) (rate(llm_call_duration_seconds_bucket{job="document-qa",provider="openrouter"}[24h])))
```

The pinned Prometheus chart loads `serverFiles.alerting_rules.yml` from `/etc/config/alerting_rules.yml`. It contains exactly three rules: `DocumentQADown` fires when `up{job="document-qa"} == 0` for 2 minutes; `DocumentQAHighErrorRate` fires when eligible 5xx exceed 1% over 5 minutes, only with at least 20 requests in that window, for 5 minutes; and `DocumentQASlowLLM` fires when OpenRouter p95 exceeds 20 seconds over 10 minutes, only with at least 20 calls in that window, for 5 minutes. The minimum-volume guards avoid reacting to unstable percentages or quantiles from a handful of calls.

Prometheus is configured for **24-hour retention**, capped at 256 MiB, on ephemeral storage; a restart or node loss can erase that history. The availability and latency views are best-effort lab measurements: with little or no traffic, the volume guards can keep alerts inactive and targets may be unevaluable, not successful. `DocumentQADown` detects failed scrapes, but does not fire if its time series disappears entirely. Alertmanager remains disabled: Prometheus evaluates and displays pending/firing states under **Alerts**, but sends no email, Slack, pager, or other notifications.

Runbook: check target availability and scrape configuration first; inspect HTTP route/status and latency panels, then LLM failures and latency. Check application and provider logs without exposing prompts or credentials. For rate limits/timeouts check provider status and configuration; for application errors inspect recent changes and roll back if needed. Confirm recovery and review impact. If data is missing, check Prometheus retention, restart history and scraping before interpreting an SLO.

## Validation and operation

From the repository root run `(cd document-qa-prototype && .venv/bin/python -m pytest)`, `python -m json.tool document-qa/deploy/grafana/document-qa.json`, and `kubectl kustomize document-qa/deploy/grafana` (or `kustomize build`). Render chart 13.5.0 with the Application's Helm values when the chart is available. Check the Argo CD diff and sync health. Use existing private access to Grafana, open **Document QA — Service Overview**, verify target UP and exercise a request; compare panel data with Explore and `/metrics`. Token panels can legitimately have no data.

The Applications are manually bootstrapped: after reviewing and committing a revision available at `main`, the operator must apply the updated `document-qa/deploy/argocd/grafana.yaml` Application once using their approved Argo CD bootstrap procedure. A Git push alone does not update that Application. Argo CD then syncs the chart and Git dashboard source. Do not expose the services publicly.

For rollback, revert the reviewed Git changes and apply the previous Grafana Application manifest through the same bootstrap procedure, then sync and inspect Argo CD. The old Application removes the dashboard mount/provider; because prune is disabled, the ConfigMap may remain and can be removed separately by an operator after verification. Roll back the application deployment to its prior revision using its normal Argo CD procedure.
