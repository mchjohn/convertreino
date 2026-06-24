# ConverTreino Backend

Fundação do backend (SPEC-001), OAuth Strava (SPEC-002), JWT (SPEC-013), chat LLM (SPEC-014/017/020) e debug Phoenix (SPEC-019).

## Requisitos

- Python 3.12+
- [uv](https://docs.astral.sh/uv/)
- Docker (para PostgreSQL local)

## Setup

```bash
cd backend
docker compose up -d
uv sync --all-extras --dev
uv run alembic upgrade head
```

### Variáveis de ambiente

Copie o template e preencha os valores:

```bash
cp .env.example .env
```

O arquivo `backend/.env` é carregado automaticamente ao iniciar a API, rodar migrations (`alembic`) ou importar módulos de configuração. Variáveis já definidas no shell têm prioridade sobre o `.env`.

| Variável | Obrigatória | Default (testes) | Descrição |
|----------|-------------|------------------|-----------|
| `JWT_SECRET` | Sim (produção) | `test-jwt-secret` | Chave HS256 para assinatura dos access tokens |
| `JWT_EXPIRES_MINUTES` | Não | `60` | TTL do access token em minutos |
| `LLM_PROVIDER` | Não | `openai` | Provider LLM ativo: `openai` ou `groq` |
| `OPENAI_API_KEY` | Sim* (provider=openai) | `test-openai-key` | Chave da API OpenAI para o endpoint de chat |
| `OPENAI_MODEL` | Não | `gpt-4o-mini` | Modelo OpenAI para Chat Completions |
| `GROQ_API_KEY` | Sim* (provider=groq) | `test-groq-key` | Chave da API Groq Cloud |
| `GROQ_MODEL` | Não | `llama-3.3-70b-versatile` | Modelo Groq com suporte a tool calling |
| `CHAT_MAX_TOOL_ITERATIONS` | Não | `5` | Máximo de rodadas LLM↔tools por request de chat |
| `PHOENIX_ENABLED` | Não | `false` | Exporta traces LLM para Phoenix (somente dev local) |
| `PHOENIX_COLLECTOR_ENDPOINT` | Não | `http://localhost:6006/v1/traces` | Endpoint OTLP HTTP do Phoenix |
| `PHOENIX_PROJECT_NAME` | Não | `convertreino-dev` | Nome do projeto no UI Phoenix |
| `STRAVA_CLIENT_ID` | Sim (OAuth) | — | Client ID da app Strava |
| `STRAVA_CLIENT_SECRET` | Sim (OAuth) | — | Client secret Strava |
| `STRAVA_REDIRECT_URI` | Sim (OAuth) | — | Redirect URI registrado no Strava |
| `STRAVA_MOBILE_REDIRECT_URI` | Não | valor de `STRAVA_REDIRECT_URI` | Redirect URI usado na troca do `code` OAuth emitido pelo app mobile (ex.: `convertreino://oauth/callback`) |

\* A chave do provider ativo (`OPENAI_API_KEY` ou `GROQ_API_KEY`) é obrigatória em produção.

### OAuth Strava + JWT (SPEC-002 / SPEC-013)

1. Crie uma aplicação em [developers.strava.com](https://developers.strava.com) → **My API Application**.
2. Configure **Authorization Callback Domain** compatível com o redirect (ex.: `localhost` em dev).
3. Configure as variáveis em `.env` (veja `.env.example`) ou exporte no shell.

4. Inicie a API e abra a URL de autorização:

```bash
uv run uvicorn convertreino.api.main:app --reload --app-dir src
curl http://localhost:8000/auth/strava/authorize
```

5. Após consentir no Strava, o callback retorna:

```json
{
  "user_id": "<uuid>",
  "access_token": "<jwt>",
  "token_type": "bearer",
  "expires_in": 3600
}
```

6. Use o JWT em endpoints protegidos (ex.: sync Strava):

```bash
TOKEN="<access_token do callback>"
USER_ID="<user_id do callback>"
curl -X POST "http://localhost:8000/users/${USER_ID}/sync/strava" \
  -H "Authorization: Bearer ${TOKEN}"
```

### OAuth mobile (SPEC-015)

O app Expo troca o `code` capturado via deep link em `POST /auth/strava/token` (mesmo schema de resposta do callback web). Quando o redirect mobile difere do web, configure:

```bash
export STRAVA_MOBILE_REDIRECT_URI="convertreino://oauth/callback"
```

```bash
curl -X POST "http://localhost:8000/auth/strava/token" \
  -H "Content-Type: application/json" \
  -d '{"code":"<authorization_code>"}'
```

### Chat (SPEC-014 / SPEC-017 / SPEC-020)

Perguntas em linguagem natural sobre treinos (requer JWT e chave do provider LLM ativo).

As definições de tools enviadas ao LLM usam schemas compactos em `application/llm/chat_tool_schemas.py` (SPEC-020). O servidor MCP (`/mcp`) continua com descrições verbosas — contratos distintos para o mesmo handler analítico.

```bash

# OpenAI (default)
export LLM_PROVIDER=openai
export OPENAI_API_KEY=sk-...

# Groq Cloud (alternativa)
# export LLM_PROVIDER=groq
# export GROQ_API_KEY=gsk_...
# export GROQ_MODEL=llama-3.3-70b-versatile

curl -X POST "http://localhost:8000/chat/messages" \
  -H "Authorization: Bearer ${TOKEN}" \
  -H "Content-Type: application/json" \
  -d '{"messages":[{"role":"user","content":"Qual foi minha corrida mais longa?"}]}'
```

Resposta esperada (`200`):

```json
{
  "message": {
    "role": "assistant",
    "content": "..."
  },
  "tool_calls_made": ["get_longest_run"]
}
```

### Debug com Phoenix (SPEC-019)

Observabilidade LLM opcional para inspecionar prompts, completions e execução de tools no fluxo de chat.

1. Suba o Phoenix com o profile `observability`:

```bash
cd backend
docker compose --profile observability up -d
```

2. Instale as dependências de observabilidade:

```bash
uv sync --extra observability --dev
```

3. Habilite no `.env`:

```env
PHOENIX_ENABLED=true
# PHOENIX_COLLECTOR_ENDPOINT=http://localhost:6006/v1/traces
# PHOENIX_PROJECT_NAME=convertreino-dev
```

4. Inicie a API e envie mensagens de chat (mobile ou curl acima).

5. Abra o UI em [http://localhost:6006](http://localhost:6006) e inspecione os traces.

Smoke test manual sugerido:

1. "Qual foi minha corrida mais longa?" — deve aparecer span de tool `get_longest_run`
2. "Quanto corri essa semana?" — span de tool de volume
3. "Olá!" — apenas spans LLM, sem tool

**Nota:** Phoenix é somente para desenvolvimento local. Não habilite `PHOENIX_ENABLED` em produção.

## Testes

```bash
# Unitários + contrato (sem banco)
uv run pytest -m "not integration"

# Todos (inclui integração com PostgreSQL; exclui E2E com LLM real)
export TEST_DATABASE_URL=postgresql+psycopg://convertreino:convertreino@localhost:5432/convertreino_test
export STRAVA_CLIENT_ID=fake-client-id
export STRAVA_CLIENT_SECRET=fake-client-secret
export STRAVA_REDIRECT_URI=http://localhost:8000/auth/strava/callback
uv run pytest -m "not e2e"
```

### E2E de acurácia do chat (SPEC-021)

Testes nightly com LLM real que validam roteamento de intenção (`tool_calls_made`) contra a matriz em `tests/e2e/fixtures/chat_intent_matrix.yaml`. Excluídos do CI de PR.

Requer `E2E_LLM=1` e a API key do provider ativo:

| Variável | Descrição |
|----------|-----------|
| `E2E_LLM` | Deve ser `1` para habilitar os testes E2E (sem isso, são ignorados) |
| `LLM_PROVIDER` | Opcional: `openai` ou `groq` — filtra um provider (nightly usa matrix) |
| `OPENAI_API_KEY` | Obrigatória para casos com `provider=openai` |
| `GROQ_API_KEY` | Obrigatória para casos com `provider=groq` |
| `OPENAI_MODEL` | Default `gpt-4o-mini` |
| `GROQ_MODEL` | Default `llama-3.3-70b-versatile` |

```bash
# OpenAI
E2E_LLM=1 OPENAI_API_KEY=sk-... uv run pytest -m e2e --tb=short -v

# Groq
E2E_LLM=1 LLM_PROVIDER=groq GROQ_API_KEY=gsk_... uv run pytest -m e2e --tb=short -v
```

O job nightly (`.github/workflows/nightly.yml`) rota às 06:00 UTC, executa a matriz por provider e falha se a acurácia ficar abaixo de 90% (≥ 9/10 casos). Cada caso falho recebe 1 retry antes de contar como falha definitiva.

## API

```bash
uv run uvicorn convertreino.api.main:app --reload --app-dir src
curl http://localhost:8000/health
curl http://localhost:8000/auth/strava/authorize
```

## Expor API local (ngrok)

Para testar o app mobile em dispositivo físico ou receber webhooks do Strava, exponha a API com [ngrok](https://ngrok.com/download):

```bash
# Terminal 1 — API
uv run uvicorn convertreino.api.main:app --reload --app-dir src

# Terminal 2 — túnel público
ngrok http 8000
```

Use a URL HTTPS gerada (ex.: `https://abcd-1234.ngrok-free.app`):

| Caso de uso | Configuração |
|-------------|--------------|
| App mobile em celular real | `EXPO_PUBLIC_API_BASE_URL=https://abcd-1234.ngrok-free.app` em `mobile/.env` (reinicie o Expo com `npx expo start -c`) |
| OAuth web via ngrok | `STRAVA_REDIRECT_URI=https://abcd-1234.ngrok-free.app/auth/strava/callback` e registre o domínio no painel Strava |
| Webhooks Strava | `STRAVA_WEBHOOK_CALLBACK_URL=https://abcd-1234.ngrok-free.app/webhooks/strava` |

No plano gratuito, a URL muda a cada execução do ngrok — atualize as variáveis quando reiniciar o túnel.
