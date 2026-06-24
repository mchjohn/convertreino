# SPEC-013 — JWT: autenticação Bearer para API do app

| Campo          | Valor                                              |
|----------------|----------------------------------------------------|
| **Status**     | Draft                                              |
| **Autor**      | @convertreino                                      |
| **Revisor**    | —                                                  |
| **Criada em**  | 2026-06-19                                         |
| **Camada**     | Application + API + Infra (config)                 |
| **Depende de** | SPEC-001, SPEC-002                                 |
| **Bloqueia**   | SPEC-014 (API de chat)                             |
| **Épico**      | Infra / Conversacional                             |

---

## Contexto

As specs MCP (SPEC-007 a SPEC-012) assumem que `user_id` será **injetado pelo orchestrator de chat** após autenticação — o LLM não deve inferir esse valor. Porém a SPEC-002 retorna apenas `{ "user_id": "<uuid>" }` no callback OAuth, sem credencial reutilizável para chamadas subsequentes. O endpoint `POST /users/{user_id}/sync/strava` (SPEC-003) permanece aberto, sem verificação de identidade.

Antes de expor a API de chat (SPEC-014), o app mobile precisa provar que é o dono de um `user_id` em cada requisição autenticada. Esta spec introduz JWT Bearer stateless como mecanismo de autenticação da API do app.

---

## Escopo

### Incluído

- `JwtTokenService` em `application/jwt_token_service.py`:
  - `create_access_token(user_id: UUID) -> str`
  - `decode_access_token(token: str) -> UUID` (levanta `InvalidTokenError`)
- Nova exceção `InvalidTokenError` em `domain/exceptions.py`
- Configuração em `infrastructure/config.py`:
  - `JWT_SECRET` (obrigatório em runtime; default fixo apenas em testes)
  - `JWT_EXPIRES_MINUTES` (default: `60`)
- Dependência FastAPI `get_current_user_id` em `api/dependencies.py` via `HTTPBearer`
- Override de teste `set_jwt_service_override` (padrão existente em `dependencies.py`)
- Callback OAuth ampliado em `api/routes/strava_auth.py` — response 200 inclui JWT além de `user_id`
- Proteção de `POST /users/{user_id}/sync/strava` em `api/routes/strava_sync.py`:
  - Header `Authorization: Bearer <token>` obrigatório
  - `user_id` do path deve coincidir com `sub` do JWT
- Dependência direta `pyjwt[crypto]` em `pyproject.toml`
- Testes unitários e de integração (TDD a partir dos comportamentos abaixo)
- Cobertura mínima Application: **80%** (guia seção 8)
- Atualização de `backend/README.md` com novas env vars e fluxo curl com Bearer

### Excluído (explicitamente fora desta spec)

- API de chat / `ChatOrchestrator` / integração LLM → **SPEC-014**
- Abstração provider-agnostic de LLM → **SPEC-014**
- `period_resolver.py` — LLM converte períodos nas tools MCP (padrão SPEC-010/012)
- Refresh token, rotação, blacklist, logout / revogação
- Tabela `UserSession` no banco (JWT stateless)
- Proteção de `/mcp`, webhooks Strava, `/health`, `/auth/strava/authorize`
- Criptografia de `JWT_SECRET` (env var em texto, padrão POC)
- Alteração das MCP tools (`user_id` permanece no schema até SPEC-014 injetar in-process)
- Proteção de endpoints futuros além do sync (chat na SPEC-014)

---

## Contrato

### Claims JWT

| Claim     | Valor                                      |
|-----------|--------------------------------------------|
| `sub`     | `str(user_id)` — UUID do usuário interno   |
| `iat`     | timestamp UTC de emissão                   |
| `exp`     | `iat + JWT_EXPIRES_MINUTES`                |
| Algoritmo | `HS256`                                    |

### `JwtTokenService`

```python
# application/jwt_token_service.py
@dataclass(frozen=True, slots=True)
class JwtSettings:
    secret: str
    expires_minutes: int

class JwtTokenService:
    def __init__(self, settings: JwtSettings) -> None: ...

    def create_access_token(self, user_id: UUID) -> str: ...
    def decode_access_token(self, token: str) -> UUID: ...
```

| Método                 | Input              | Output   | Erro                          |
|------------------------|--------------------|----------|-------------------------------|
| `create_access_token`  | `user_id: UUID`    | `str`    | —                             |
| `decode_access_token`  | `token: str`       | `UUID`   | `InvalidTokenError`           |

`decode_access_token` levanta `InvalidTokenError` para: token malformado, assinatura inválida, `exp` expirado, `sub` ausente ou não parseável como UUID.

### Configuração

| Variável              | Obrigatória | Default (testes)     | Descrição                          |
|-----------------------|-------------|----------------------|------------------------------------|
| `JWT_SECRET`          | Sim*        | `"test-jwt-secret"`  | Chave HS256 (mín. 32 chars recomendado em prod) |
| `JWT_EXPIRES_MINUTES` | Não         | `60`                 | TTL do access token em minutos     |

\* Em runtime de produção, `JWT_SECRET` vazio deve impedir inicialização do `JwtTokenService` (falha explícita no startup ou na primeira construção do serviço).

### Dependência FastAPI

```python
# api/dependencies.py
security = HTTPBearer(auto_error=False)

def get_jwt_token_service() -> JwtTokenService: ...

def get_current_user_id(
    credentials: HTTPAuthorizationCredentials | None = Depends(security),
    jwt_service: JwtTokenService = Depends(get_jwt_token_service),
) -> UUID: ...
```

| Condição                              | HTTP | `detail` sugerido              |
|---------------------------------------|------|--------------------------------|
| Header `Authorization` ausente        | 401  | `"Not authenticated"`          |
| Scheme diferente de `Bearer`          | 401  | `"Not authenticated"`          |
| Token inválido ou expirado            | 401  | `"Invalid or expired token"`   |

### API — Callback OAuth (alteração SPEC-002)

| Método | Path                              | Auth | Response 200                                                                 |
|--------|-----------------------------------|------|------------------------------------------------------------------------------|
| GET    | `/auth/strava/callback?code=...`  | Não  | Ver schema abaixo                                                            |

**Response 200 (estendido):**

```json
{
  "user_id": "<uuid>",
  "access_token": "<jwt>",
  "token_type": "bearer",
  "expires_in": 3600
}
```

| Campo          | Tipo     | Descrição                                              |
|----------------|----------|--------------------------------------------------------|
| `user_id`      | `string` | UUID interno (mantido para retrocompatibilidade)       |
| `access_token` | `string` | JWT HS256                                              |
| `token_type`   | `string` | Sempre `"bearer"`                                      |
| `expires_in`   | `int`    | Segundos até expiração (`JWT_EXPIRES_MINUTES * 60`)    |

Códigos de erro do callback permanecem inalterados (400 para `StravaAuthError`).

### API — Sync Strava (protegido)

| Método | Path                              | Auth                    | Response 200              |
|--------|-----------------------------------|-------------------------|---------------------------|
| POST   | `/users/{user_id}/sync/strava`    | `Bearer <access_token>` | `SyncResult` (SPEC-003)   |

| Código | Condição                                              | `detail` sugerido              |
|--------|-------------------------------------------------------|--------------------------------|
| 401    | Token ausente, malformado, inválido ou expirado       | conforme tabela acima          |
| 403    | Token válido mas `sub` ≠ `user_id` do path            | `"Forbidden"`                  |
| 404    | `user_id` inexistente (`UserNotFoundError`)           | `"User not found"` (inalterado)|
| 400    | Strava auth falhou (`StravaAuthError`)                | mensagem da exceção (inalterado)|
| 502    | Strava API indisponível (`StravaApiError`)            | `"Strava API unavailable"` (inalterado)|

Assinatura do handler:

```python
@router.post("/{user_id}/sync/strava")
def sync_strava(
    user_id: UUID,
    current_user_id: UUID = Depends(get_current_user_id),
    sync_service: StravaSyncService = Depends(get_strava_sync_service),
) -> SyncResult:
    if current_user_id != user_id:
        raise HTTPException(status_code=403, detail="Forbidden")
    ...
```

### Efeitos colaterais

Nenhum persistido. Emissão e validação de JWT são operações em memória. OAuth callback e sync mantêm os efeitos colaterais já definidos em SPEC-002 e SPEC-003.

---

## Comportamentos

### Casos normais (Happy Path)

#### CN-1: OAuth callback emite JWT válido
**Dado** que o `code` OAuth é válido e o Strava retorna tokens do atleta  
**Quando** `GET /auth/strava/callback?code=...` é chamado  
**Então** retorna `200` com `user_id`, `access_token`, `token_type == "bearer"` e `expires_in == JWT_EXPIRES_MINUTES * 60`  
**E** `decode_access_token(access_token)` retorna UUID igual a `user_id`

#### CN-2: Sync com Bearer válido e ownership correto
**Dado** que o usuário existe e possui tokens Strava válidos  
**E** `access_token` foi emitido para `sub == user_id`  
**Quando** `POST /users/{user_id}/sync/strava` é chamado com `Authorization: Bearer <access_token>`  
**Então** retorna `200` com `SyncResult` (comportamento de sync inalterado da SPEC-003)

#### CN-3: Round-trip create → decode
**Dado** um `user_id` UUID válido  
**Quando** `create_access_token(user_id)` é chamado e em seguida `decode_access_token(token)`  
**Então** retorna o mesmo `user_id`

### Casos de borda (Edge Cases)

#### CB-1: Re-OAuth do mesmo atleta emite novo JWT
**Dado** que o atleta Strava já possui `User` vinculado  
**Quando** `GET /auth/strava/callback` é chamado novamente com novo `code`  
**Então** retorna `200` com o mesmo `user_id`  
**E** `access_token` é um JWT novo (tipicamente `exp` diferente do token anterior)  
**E** `sub` do novo token permanece igual ao `user_id`

#### CB-2: Token próximo da expiração ainda é aceito
**Dado** que `JWT_EXPIRES_MINUTES = 60`  
**E** um token foi emitido há 59 minutos (ainda dentro do TTL)  
**Quando** `decode_access_token(token)` ou `get_current_user_id` com esse token é invocado  
**Então** retorna o `user_id` sem erro

### Casos de erro

#### CE-1: Sync sem header Authorization
**Dado** que o endpoint sync está protegido  
**Quando** `POST /users/{user_id}/sync/strava` é chamado sem header `Authorization`  
**Então** retorna `401` com `detail` indicando falta de autenticação

#### CE-2: Token malformado ou assinatura inválida
**Dado** um token que não é JWT válido ou foi assinado com secret diferente  
**Quando** `decode_access_token(token)` é chamado  
**Então** levanta `InvalidTokenError`  
**E** quando usado em endpoint protegido, retorna `401`

#### CE-3: Token expirado
**Dado** um token com `exp` no passado  
**Quando** `decode_access_token(token)` é chamado  
**Então** levanta `InvalidTokenError`  
**E** `POST /users/{user_id}/sync/strava` com esse token retorna `401` com `detail` descritivo (ex.: `"Invalid or expired token"`)

#### CE-4: Ownership mismatch — JWT válido, user_id do path diferente
**Dado** que `access_token` foi emitido para `sub = user_a`  
**Quando** `POST /users/{user_b}/sync/strava` é chamado com esse token (`user_a ≠ user_b`)  
**Então** retorna `403` com `detail == "Forbidden"`

#### CE-5: JWT_SECRET ausente em produção
**Dado** que `JWT_SECRET` não está definido (string vazia) fora do ambiente de teste  
**Quando** o app tenta construir `JwtTokenService`  
**Então** falha explicitamente na inicialização (ex.: `ValueError` ou equivalente documentado) — não emite tokens com secret vazio silenciosamente

---

## Critérios de Aceite

- [ ] Spec com status **Draft** no repositório
- [ ] `JwtTokenService` implementado com `create_access_token` e `decode_access_token`
- [ ] `InvalidTokenError` adicionada em `domain/exceptions.py`
- [ ] Callback retorna `user_id`, `access_token`, `token_type` e `expires_in`
- [ ] JWT contém `sub` igual ao UUID do usuário autenticado
- [ ] `get_current_user_id` extrai `sub` via `HTTPBearer`
- [ ] Sync exige Bearer e retorna `401` sem token válido
- [ ] Sync retorna `403` quando JWT `sub` ≠ `user_id` do path
- [ ] Um teste unitário por CN/CB/CE documentado
- [ ] Teste de contrato de assinatura (`create_access_token` / `decode_access_token`)
- [ ] Testes de integração OAuth e sync atualizados
- [ ] `JWT_SECRET` e `JWT_EXPIRES_MINUTES` documentados no README
- [ ] Cobertura `convertreino.application` >= 80%
- [ ] CI verde (ruff, mypy, pytest)
- [ ] Nenhuma migration Alembic
- [ ] Não contradiz SPEC-001, SPEC-002 nem SPEC-003 (estende contratos documentados)

---

## Mapeamento Spec → Testes

| Artefato                         | Localização                                                    |
|----------------------------------|----------------------------------------------------------------|
| CN/CB/CE do `JwtTokenService`    | `backend/tests/unit/application/test_jwt_token_service.py`     |
| `get_current_user_id`            | `backend/tests/unit/api/test_auth_dependencies.py`             |
| CN-1, CB-1 (callback + JWT)      | `backend/tests/integration/test_strava_oauth.py` (atualizar)   |
| CN-2, CE-1, CE-4 (sync + Bearer) | `backend/tests/integration/test_strava_activity_sync.py` (atualizar) |
| Contrato de assinatura           | `test_jwt_token_service.py` ou `test_auth_dependencies.py`     |

---

## Decisões de Design

### Decisão: JWT stateless (sem sessão em banco)
**Contexto:** Como persistir autenticação do app após OAuth Strava.  
**Opção escolhida:** JWT HS256 stateless; sem tabela `UserSession`.  
**Alternativas rejeitadas:** Sessão server-side em Redis/PostgreSQL; opaque tokens com lookup.  
**Motivo:** Escopo mínimo da POC; revogação e logout ficam para spec futura.

### Decisão: Manter `user_id` no callback além do token
**Contexto:** SPEC-002 retorna `{ "user_id": "<uuid>" }`; app mobile pode já consumir esse campo.  
**Opção escolhida:** Response estendido com `user_id` + campos OAuth2-like (`access_token`, `token_type`, `expires_in`).  
**Alternativas rejeitadas:** Remover `user_id`; retornar apenas token.  
**Motivo:** Retrocompatibilidade parcial; mobile obtém identidade e credencial na mesma resposta.

### Decisão: Path sync inalterado com checagem de ownership
**Contexto:** Como proteger o sync sem refatorar rotas existentes.  
**Opção escolhida:** Manter `POST /users/{user_id}/sync/strava`; validar `current_user_id == user_id`.  
**Alternativas rejeitadas:** Migrar para `POST /sync/strava` (user só do JWT); `GET /users/me/sync/strava`.  
**Motivo:** Diff mínimo; breaking change limitado à exigência de Bearer.

### Decisão: `/mcp` permanece sem auth nesta spec
**Contexto:** Servidor MCP exposto em `/mcp` (SPEC-007) aceita `user_id` como parâmetro.  
**Opção escolhida:** Não proteger `/mcp` na SPEC-013.  
**Alternativas rejeitadas:** Exigir Bearer no transporte HTTP/SSE do MCP.  
**Motivo:** Uso dev/stdio; SPEC-014 chamará tools in-process no orchestrator, não via HTTP público.

### Decisão: HS256 + secret compartilhado
**Contexto:** Algoritmo e distribuição de chaves para assinatura JWT.  
**Opção escolhida:** HS256 com `JWT_SECRET` em env var.  
**Alternativas rejeitadas:** RS256 com par de chaves; JWKS.  
**Motivo:** Suficiente para POC single-instance; simplicidade operacional.

### Decisão: `InvalidTokenError` no domínio
**Contexto:** Onde classificar falha de token inválido.  
**Opção escolhida:** Exceção em `domain/exceptions.py`; camada API traduz para HTTP 401.  
**Alternativas rejeitadas:** Exceção HTTP-specific em `api/`; retorno `None` silencioso.  
**Motivo:** Falha explícita é melhor que silêncio (princípio 4 do guia); Application não conhece HTTP.

---

## Notas de Migração

- **Breaking change controlado:** clientes que chamam `POST /users/{user_id}/sync/strava` passam a precisar de `Authorization: Bearer <token>`; clientes que só fazem OAuth recebem campos novos sem perder `user_id`
- A decisão de design da SPEC-002 ("Callback retorna só `user_id`") é **estendida** por esta spec — não revogada; documentar cross-reference
- Nenhuma migration Alembic
- Novas variáveis de ambiente: `JWT_SECRET` (obrigatória), `JWT_EXPIRES_MINUTES` (opcional)
- Nova dependência direta: `pyjwt[crypto]`
- Rollback: remover `jwt_token_service.py`, `InvalidTokenError`, dependência auth no sync, reverter callback para response SPEC-002, remover env vars — sem impacto em dados

---

## Roadmap pós-SPEC-013

| SPEC futura | Conteúdo                                                                                    |
|-------------|---------------------------------------------------------------------------------------------|
| SPEC-014    | API de chat (`POST /chat/messages`), `ChatOrchestrator`, abstração provider-agnostic LLM, injeção de `user_id` nas tools sem expor ao modelo |
| SPEC-015    | App mobile Expo: OAuth Strava via deep link, sessão JWT, sync inicial e tela de chat       |
| SPEC-016+   | `period_resolver` server-side (gatilho: CB-3 do nightly SPEC-021 falhar ≥ 3 noites em ambos providers) |

---

## Checklist de revisão (seção 12 do guia)

### Clareza
- [ ] O contexto explica o problema sem descrever a solução?
- [ ] O contrato tem tipos explícitos para todos os inputs e outputs?
- [ ] Cada comportamento tem "Dado / Quando / Então" completo?
- [ ] Os critérios de aceite são binários e verificáveis?

### Completude
- [ ] Há ao menos um caso normal (CN-1 a CN-3)?
- [ ] Casos de borda cobertos (re-OAuth, token próximo da expiração)?
- [ ] Casos de erro especificados (`401`, `403`, secret ausente, token inválido/expirado)?
- [ ] Escopo "Excluído" deixa claro o que ficou de fora (chat, MCP auth, refresh)?

### Consistência
- [ ] Não contradiz SPEC-001, SPEC-002 nem SPEC-003?
- [ ] Nomes de tipos alinhados ao código existente (`User`, `UUID`, `SyncResult`)?
- [ ] Application não acessa HTTP diretamente; API traduz exceções para códigos HTTP?
- [ ] Padrão de overrides de teste consistente com `dependencies.py` existente?

### Testabilidade
- [ ] Cada comportamento mapeia para teste unitário ou de integração?
- [ ] Comportamentos determinísticos (mesmo token válido → mesmo `sub`)?
- [ ] Efeitos colaterais explicitados (nenhum persistido para JWT) e testáveis?
