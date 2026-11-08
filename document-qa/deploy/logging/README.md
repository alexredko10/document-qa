# Centralized Document QA logs

The `api` container's stdout flows through Alloy's Kubernetes API log stream to Loki, then Grafana Explore. Loki chart **21.0.0** (Loki 3.7.9) uses one monolithic replica, filesystem TSDB v13 and a 2 GiB `emptyDir`; Alloy chart **1.15.0** (Alloy 1.21.3) uses one Deployment replica and a 128 MiB `emptyDir` for state. Loki requests 100m CPU/256 MiB and is limited to 1 CPU/1 GiB; Alloy requests 50m/128 MiB and is limited to 500m/512 MiB. These are limits, not measured usage. Check available node capacity and ephemeral disk before enabling. Retention is configured for 24 hours with the compactor; deletion is asynchronous, not an exact deadline. Storage fills before then if traffic is too high. Pod recreation or node loss can erase logs and Alloy's positions; gaps or duplicate ingestion can occur. This is a lab, not durable log storage.

Loki has authentication disabled and trusts every client that can reach its ClusterIP. Alloy's UI Service is also private. Neither is exposed through ingress or a load balancer; ClusterIP alone is not tenant isolation or encryption. Use authorized private cluster access (e.g. the existing SSM route), restrict network access where appropriate, and do not send sensitive logs. Alloy discovers only Pods in `qa` with both `app.kubernetes.io/name=qa-prototype` and `app.kubernetes.io/instance=qa-prototype`, and keeps only container `api`. The `monitoring/alloy` ServiceAccount has a Role in `qa` for Pod discovery and `pods/log` read access; it has no Secret permissions or cluster-wide Role. The Argo CD installation and AppProject must allow the cross-namespace Role and RoleBinding. The chart creates a private `monitoring/loki` Service on port 3100. No host log directories or privileged containers are used.

## Bootstrap after review

These Applications are manually bootstrapped, not managed by an App-of-Apps. Commit and push the reviewed changes through your normal process, then using an authorized cluster session from that checked-out revision run:

```sh
kubectl apply -f document-qa/deploy/argocd/loki.yaml
kubectl apply -f document-qa/deploy/argocd/alloy.yaml
kubectl apply -f document-qa/deploy/argocd/grafana.yaml
```

The last command is required once to update the existing Grafana Application; a Git push alone does not update its spec. These are operator instructions, not commands run by this change. Existing Grafana credentials are untouched. Argo CD fetches both pinned charts and must be able to reach their repositories and chart archives. Ensure namespace `qa` exists and Argo CD has permission to manage the cross-namespace Role/RoleBinding. Argo CD's automatic sync reconciles the Applications; check its UI or:

```sh
kubectl -n argocd get applications loki alloy grafana
kubectl -n argocd describe application loki
kubectl -n argocd describe application alloy
kubectl -n monitoring get pods,svc
kubectl -n monitoring top pods
kubectl -n monitoring logs statefulset/loki --tail=100
kubectl -n monitoring logs deployment/alloy --tail=100
kubectl -n monitoring port-forward svc/loki 3100:3100
# In a separate terminal while port-forward runs:
curl -fsS http://127.0.0.1:3100/ready
```

Use existing private Grafana access, open Explore, select **Loki**, and choose a time range covering a newly generated request. Logs emitted before deployment are not necessarily ingested retroactively. For example, send an authorized request to the existing private application endpoint with `X-Request-ID: aws-demo-001`, then select **Last 15 minutes** in Explore and run:

```logql
{namespace="qa",app="qa-prototype",container="api"}
{namespace="qa",app="qa-prototype",container="api"} | json | request_id="aws-demo-001"
{namespace="qa",app="qa-prototype",container="api"} | json | event="llm_call_completed"
{namespace="qa",app="qa-prototype",container="api"} | json | event="http_request_failed" or (event="llm_call_completed" and outcome!="success")
```

For the final filter, the parentheses group the parsed field comparisons; `http_request_failed` covers unexpected exceptions, while handled 4xx/5xx can be found with `| json | event="http_request_completed" | status_code >= 400`. Request IDs remain JSON fields and are never indexed stream labels. A successful request that does not invoke an LLM will not produce an LLM event.

## Diagnosis and rollback

Check Argo CD sync/health and events first. For discovery, inspect Alloy logs and `kubectl -n qa get pods -l 'app.kubernetes.io/name=qa-prototype,app.kubernetes.io/instance=qa-prototype'`; verify container `api` and permissions with `kubectl auth can-i --as=system:serviceaccount:monitoring:alloy list pods -n qa` and `kubectl auth can-i --as=system:serviceaccount:monitoring:alloy get pods --subresource=log -n qa` (impersonation itself requires authorization). Check the Alloy ServiceAccount, `qa` Role and RoleBinding if denied. Check Loki readiness, disk usage, logs, and Alloy write/retry errors if ingestion fails. If Grafana cannot query Loki, inspect its provisioned datasource URL, Service endpoints and Loki readiness, and confirm the existing Prometheus datasource and dashboard still work. Generated chart configuration can be inspected with `kubectl -n monitoring get configmap alloy loki -o yaml`.

For rollback, first restore and reapply the prior Grafana Application manifest and verify the Prometheus datasource/dashboard. Remove the Alloy and Loki Applications using the organization's Argo CD removal procedure; choose cascading deletion only if deletion of their managed resources and ephemeral logs is intended. With non-cascading removal or prune disabled, managed resources, including the `qa` Role/RoleBinding, may remain and need explicit operator cleanup. Stop Alloy before deleting Loki to avoid retries. Loki data is disposable and rollback is irreversible for logs stored only in its Pod. Do not delete `grafana-admin`, Grafana, or Prometheus resources.
