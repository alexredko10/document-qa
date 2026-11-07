# QA prototype Helm chart

This chart deploys the **already tested `document-qa-prototype`** image, not the unimplemented main `document-qa` scaffold.

- One replica only: documents/vectors are kept in process memory. Every Pod restart loses uploaded documents. It is NOT a durable or highly available application.
- Image is pinned by GHCR digest, not `latest`. Set `image.digest` for each deployment, or (later) commit it to a GitOps values file.
- `values-dev.yaml`: `stub`, works without credentials.
- `values-prod.yaml`: `openrouter`, references Kubernetes Secret `qa-openrouter` (`OPENROUTER_API_KEY` key). The Secret must be created out-of-band; do not commit secrets.
- No public ingress is created. `kubectl port-forward` is used for the local smoke test. Cloudflare Access/Tunnel is a later step.
- `Recreate` strategy avoids overlapping copies of the in-memory service during upgrades but creates downtime and loses all document data.
- Readiness/liveness check only `/healthz`, not upstream LLM health. Monitoring and provider observability are future tasks.

Local chart lint, with the actual GHCR image digest:

```bash
helm lint ./document-qa-prototype/deploy/charts/qa-prototype \
  -f ./document-qa-prototype/deploy/charts/qa-prototype/values-dev.yaml \
  --set-string image.digest="$DIGEST"
```
