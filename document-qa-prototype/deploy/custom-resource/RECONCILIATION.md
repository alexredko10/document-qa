# DocumentQAService reconciliation design

**This is a locally validated Custom Resource API and reconciliation DESIGN. No controller is implemented or deployed, so creating a DocumentQAService does not yet create workloads.** The schema and example have not been validated by a Kubernetes API server. The API group `platform.example.com` is an example DNS name; a real platform must use a domain it controls before installation.

`llmProvider` selects `stub` or `openrouter`; `embeddingProvider` selects `hash` or `openrouter`. Optional `llmModel` and `embeddingModel` map to `OPENROUTER_MODEL` and `OPENROUTER_EMBEDDING_MODEL`, respectively. When omitted, the platform uses the chart defaults `openrouter/free` and `openai/text-embedding-3-small`. Models are relevant only to their OpenRouter provider. The optional `openRouterSecretName` is the name of an existing Secret in the same namespace, containing the `OPENROUTER_API_KEY` key. It is required by the future controller when either provider is `openrouter`; this cross-field requirement is not enforced by the schema. For example, set `llmProvider: openrouter` and `openRouterSecretName: qa-openrouter` to use an existing Secret. Never put the key in the resource.

The platform controls the image repository and immutable digest, one replica, resources, tracing configuration, and service port. These are intentionally not user fields. The controller would read a trusted platform-managed digest, then derive a Deployment and ClusterIP Service from the prototype chart: port 80 to container port 8000, one replica and `Recreate`, `/healthz` readiness and liveness probes, existing resource requests and limits, and the chart's non-root user/group 10001, runtime-default seccomp, read-only root filesystem, disabled privilege escalation, and dropped capabilities. Set `LLM_PROVIDER` and `EMBEDDING_PROVIDER`; set model variables as in the chart and inject `OPENROUTER_API_KEY` with `secretKeyRef` only when an OpenRouter provider is selected. A replacement Pod loses its in-memory documents and vectors.

The future controller watches create, update and delete events for the custom resource, as well as owned Deployments and Services and referenced Secrets. It checks configuration and Secret existence/key without logging secret values. It compares desired and actual owned resources and creates or patches drift. It must not adopt an unrelated resource with a conflicting name. It writes `status.observedGeneration` for the generation it processed and a `Ready` condition with a bounded reason, message and transition time; `Ready=True` requires an available Deployment, not merely a successful API write. On missing configuration or Secret it reports `Ready=False` and retries on changes or with backoff. Image pull failures are reported as not ready from Pod/Deployment state and retried; Kubernetes itself retries pulls.

```text
on event or retry:
  fetch resource; if deleted, return
  validate providers and required Secret; resolve platform image digest
  if invalid: update Ready=False and observedGeneration; retry
  build desired Deployment and Service with owner references
  create or patch owned resources if different
  observe Deployment availability; update Ready and observedGeneration
  retry transient errors with backoff
```

Namespaced owner references let Kubernetes garbage-collect the Deployment and Service on deletion. No finalizer is needed because this design creates no external resources requiring cleanup. Secret changes should trigger reconciliation and a controlled Pod restart so environment variables refresh.

Argo CD must not manage the same Deployment or Service fields. In a future migration, Argo CD would manage the CRD, controller and custom resource, while the controller owns the generated workloads; remove the existing Helm release's ownership before handing over those names. Until such a migration is designed and performed, the existing Helm/Argo CD deployment remains the runtime.
