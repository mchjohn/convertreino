# ConverTreino Backend

Fundação do backend (SPEC-001), OAuth Strava (SPEC-002) e autenticação JWT (SPEC-013).

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

### Chat (SPEC-014 / SPEC-017)

Perguntas em linguagem natural sobre treinos (requer JWT e chave do provider LLM ativo):

```bash
# OpenAI (default)
export LLM_PROVIDER=openai
export OPENAI_API_KEY=sk-...

# Groq Cloud (alternativa)
# export LLM_PROVIDER=groq
# export GROQ_API_KEY=gsk_...
# export GROQ_MODEL=llama-3.3-70b-versatile

```bash
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

## Testes

```bash
# Unitários + contrato (sem banco)
uv run pytest -m "not integration"

# Todos (inclui integração com PostgreSQL)
export TEST_DATABASE_URL=postgresql+psycopg://convertreino:convertreino@localhost:5432/convertreino_test
export STRAVA_CLIENT_ID=fake-client-id
export STRAVA_CLIENT_SECRET=fake-client-secret
export STRAVA_REDIRECT_URI=http://localhost:8000/auth/strava/callback
uv run pytest
```

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
