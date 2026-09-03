# Consumindo a API pelo n8n (a partir do schema OpenAPI)

Gerado a partir de `GET /api/schema/` — a fonte da verdade é o schema servido pela
aplicação, não este arquivo. Regenere com o snippet no final.

A API expõe:

- **`/api/schema/`** — OpenAPI 3.0 (YAML)
- **`/api/docs/`** — Swagger UI, para explorar no navegador

Todos os endpoints abaixo declaram `ApiKeyAuth` no schema: header
`Authorization: Api-Key <chave>`, gerada com `manage.py create_api_key "<nome>"`.

> A base é `http://backend:8000` porque é assim que o n8n (no mesmo compose network)
> enxerga a API. De fora dos containers use `http://localhost:8000`.

## Como usar no n8n

Nó **HTTP Request** → menu do nó → **Import cURL** → cole um dos comandos abaixo.
O n8n preenche método, URL, headers e corpo sozinho.

```bash
# automation_documents_create
curl -X POST 'http://backend:8000/api/automation/documents/' \
  -H 'Authorization: Api-Key <SUA_API_KEY>' \
  -H 'Content-Type: application/json' \
  -d '{"company": "<UUID da empresa>", "name": "<name>", "pdf_url": "https://exemplo.test/contrato.pdf", "signers": [{"name": "Ana Souza", "email": "ana@example.com"}]}'
```

```bash
# automation_documents_analyze_create
curl -X POST 'http://backend:8000/api/automation/documents/<UUID do documento>/analyze/' \
  -H 'Authorization: Api-Key <SUA_API_KEY>'
```

```bash
# automation_documents_report_retrieve
curl -X GET 'http://backend:8000/api/automation/documents/<UUID do documento>/report/' \
  -H 'Authorization: Api-Key <SUA_API_KEY>'
```

```bash
# automation_reports_summary_retrieve
curl -X GET 'http://backend:8000/api/automation/reports/summary/' \
  -H 'Authorization: Api-Key <SUA_API_KEY>'
```

## Regenerar este arquivo

```bash
curl -s localhost:8000/api/schema/ -o /tmp/schema.yaml
# veja deploy/n8n/openapi-curl.md no repositório para o gerador
```
