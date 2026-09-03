# Local Kubernetes overlay

Runs the whole stack on a single-node dev cluster (kind or minikube) with 1 replica
per service, `DJANGO_DEBUG=true`, permissive `DJANGO_ALLOWED_HOSTS`, and the ZapSign
and AI gateways in **fake** mode — so no sandbox token and no OpenAI key are needed.

> For plain day-to-day development prefer `docker compose up` (see `deploy/`).
> This overlay exists to prove the manifests actually run.

## 1. Build the images locally

From the repository root:

```bash
docker build -t zapsign-backend:local  ./backend
docker build -t zapsign-frontend:local ./frontend
```

## 2. Load them into the cluster

The overlay pins `zapsign-backend:local` / `zapsign-frontend:local` and the base sets
`imagePullPolicy: IfNotPresent`, so the node-local image is used and nothing is
pulled from a registry.

**kind**

```bash
kind load docker-image zapsign-backend:local zapsign-frontend:local
```

**minikube**

```bash
minikube image load zapsign-backend:local
minikube image load zapsign-frontend:local
# or build straight into the daemon: eval $(minikube docker-env) before step 1
```

## 3. Create the Secret

`base/secret.example.yaml` contains placeholders only and is rendered by the build —
fine for a local cluster (fake providers ignore the API keys), but override it with
real values if you want to talk to the ZapSign sandbox:

```bash
kubectl -n zapsign create secret generic zapsign-secrets \
  --from-literal=DJANGO_SECRET_KEY="$(openssl rand -base64 48)" \
  --from-literal=POSTGRES_PASSWORD='localdev' \
  --from-literal=OPENAI_API_KEY='sk-...' \
  --from-literal=N8N_WEBHOOK_SECRET='localdev' \
  --from-literal=SEED_PASSWORD='localdev' \
  --dry-run=client -o yaml | kubectl apply -f -
```

## 4. Apply

```bash
kubectl apply -k deploy/k8s/overlays/local
```

Preview what would be applied without touching the cluster:

```bash
kubectl kustomize deploy/k8s/overlays/local
```

## 5. Ingress + hosts entry

An ingress-nginx controller must be installed:

```bash
# kind
kubectl apply -f https://raw.githubusercontent.com/kubernetes/ingress-nginx/main/deploy/static/provider/kind/deploy.yaml
# minikube
minikube addons enable ingress
```

Then point the host at the cluster:

```bash
echo '127.0.0.1 zapsign.local' | sudo tee -a /etc/hosts   # kind
# minikube: use `minikube ip` instead of 127.0.0.1
```

Open <http://zapsign.local>; the API is at <http://zapsign.local/api/> and the health
check at <http://zapsign.local/api/health/>.

## 6. Migrations

`zapsign-migrate` runs `manage.py migrate --noinput && manage.py seed_user` once. A
Job's pod template is immutable, so re-running means deleting it first:

```bash
kubectl -n zapsign delete job zapsign-migrate --ignore-not-found
kubectl apply -k deploy/k8s/overlays/local
kubectl -n zapsign logs job/zapsign-migrate
```

## Troubleshooting

```bash
kubectl -n zapsign get pods,svc,ingress
kubectl -n zapsign logs deploy/backend
kubectl -n zapsign port-forward svc/backend 8000:8000   # then curl localhost:8000/api/health/
```

Backend pods stuck `0/1 Running` almost always means `/api/health/` is returning 503,
i.e. the database is unreachable — check `kubectl -n zapsign logs sts/postgres`.

## Tear down

```bash
kubectl delete -k deploy/k8s/overlays/local
kubectl -n zapsign delete pvc -l app.kubernetes.io/name=postgres   # wipes the DB volume
```
