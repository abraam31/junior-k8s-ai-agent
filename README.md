# Junior

Junior is a read-only Kubernetes troubleshooting agent. It checks pod status
in a namespace, pulls logs when needed, and returns a structured diagnosis of
what's wrong (or flags issues as needing deeper, application-level
investigation).

## Layout

- `junior/` — the package: agent loop (`agent.py`), system prompt
  (`prompts.py`), Kubernetes tools (`tools/k8s.py`, `tools/schemas.py`), plus
  placeholders for a diagnosis cache (`cache.py`) and a FastAPI endpoint
  (`api.py`).
- `manifests/` — placeholder Kubernetes manifests to deploy Junior.
- `Dockerfile` — placeholder image build.

## Status

Early scaffolding. The CLI agent loop works end to end; the cache and API
layers are not implemented yet.
