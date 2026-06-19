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

| Variável | Obrigatória | Default (testes) | Descrição |
|----------|-------------|------------------|-----------|
| `JWT_SECRET` | Sim (produção) | `test-jwt-secret` | Chave HS256 para assinatura dos access tokens |
| `JWT_EXPIRES_MINUTES` | Não | `60` | TTL do access token em minutos |
| `STRAVA_CLIENT_ID` | Sim (OAuth) | — | Client ID da app Strava |
| `STRAVA_CLIENT_SECRET` | Sim (OAuth) | — | Client secret Strava |
| `STRAVA_REDIRECT_URI` | Sim (OAuth) | — | Redirect URI registrado no Strava |

### OAuth Strava + JWT (SPEC-002 / SPEC-013)

1. Crie uma aplicação em [developers.strava.com](https://developers.strava.com) → **My API Application**.
2. Configure **Authorization Callback Domain** compatível com o redirect (ex.: `localhost` em dev).
3. Exporte as variáveis:

```bash
export STRAVA_CLIENT_ID="seu-client-id"
export STRAVA_CLIENT_SECRET="seu-client-secret"
export STRAVA_REDIRECT_URI="http://localhost:8000/auth/strava/callback"
export JWT_SECRET="sua-chave-secreta-com-pelo-menos-32-caracteres"
```

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
