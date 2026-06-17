# SPEC-002 — OAuth Strava: vincular conta e persistir tokens

| Campo          | Valor                                              |
|----------------|----------------------------------------------------|
| **Status**     | Aprovada                                           |
| **Autor**      | @convertreino                                      |
| **Revisor**    | @convertreino                                      |
| **Criada em**  | 2026-06-17                                         |
| **Camada**     | Domain + Application + API + Infra                 |
| **Depende de** | SPEC-001                                           |
| **Bloqueia**   | SPEC-003 (sync), SPEC-004 (webhooks)               |
| **Épico**      | Infra                                              |

---

## Contexto

Antes de sincronizar atividades ou receber webhooks do Strava, o sistema precisa vincular a identidade do atleta Strava a um `User` interno e persistir credenciais OAuth reutilizáveis (access e refresh tokens).

A SPEC-001 reservou os campos Strava em `User` para esta spec.

---

## Escopo

### Incluído

- Campos Strava em `User`: `strava_athlete_id`, `access_token`, `refresh_token`, `token_expires_at`
- `UserRepository.get_by_strava_athlete_id(athlete_id)`
- `StravaOAuthService`: URL de autorização, `exchange_code`, `ensure_valid_token` (refresh proativo com margem de 5 min)
- `StravaApiClient` (httpx sync) e `FakeStravaApiClient` para testes
- Migration `002_strava_user_fields`: colunas Strava + índice único em `strava_athlete_id`
- Variáveis de ambiente: `STRAVA_CLIENT_ID`, `STRAVA_CLIENT_SECRET`, `STRAVA_REDIRECT_URI`
- Rotas `GET /auth/strava/authorize` e `GET /auth/strava/callback`

### Excluído (explicitamente fora desta spec)

- Sync de atividades → SPEC-003
- Webhooks Strava → SPEC-004
- Mapper Strava→`Activity` e extensões em `ActivityRepository`
- `UserSession` / JWT / Bearer token para API do app
- Índice em `activities.external_id`
- Redis, workers/filas, engines analíticos, MCP, chat
- Criptografia de tokens em repouso
- Subscription de webhook no painel Strava

---

## Contrato

### Entidade `User` (campos adicionais)

| Campo               | Tipo             | Obrigatório (após OAuth) | Descrição                    |
|---------------------|------------------|--------------------------|------------------------------|
| `strava_athlete_id` | `int`            | Sim                      | ID do atleta no Strava (único) |
| `access_token`      | `str`            | Sim                      | Token de acesso OAuth        |
| `refresh_token`     | `str`            | Sim                      | Token de refresh             |
| `token_expires_at`  | `datetime (UTC)` | Sim                      | Expiração do access token    |

Usuários sem vínculo Strava podem ter esses campos como `None` (compatibilidade com dados pré-OAuth).

### `UserRepository`

```python
def get_by_strava_athlete_id(athlete_id: int) -> User | None: ...
```

### `StravaOAuthService`

```python
def get_authorization_url(self) -> str: ...
def exchange_code(self, code: str) -> User: ...
def ensure_valid_token(self, user: User) -> User: ...
```

### API

| Método | Path                      | Response 200                          |
|--------|---------------------------|---------------------------------------|
| GET    | `/auth/strava/authorize`  | `{ "authorization_url": "..." }`      |
| GET    | `/auth/strava/callback?code=...` | `{ "user_id": "<uuid>" }`      |

| Código | Condição                          |
|--------|-----------------------------------|
| 400    | `code` inválido ou expirado (`StravaAuthError`) |
| 500    | Strava API indisponível (5xx)     |

Sem autenticação nas rotas (POC).

### Efeitos colaterais

- `save` persiste tokens no PostgreSQL (ou in-memory nos testes unitários)
- `exchange_code` e `ensure_valid_token` (quando refresh) atualizam tokens no repositório

---

## Comportamentos

### Casos normais (Happy Path)

#### CN-1: Atleta novo via OAuth
**Dado** que não existe `User` com o `strava_athlete_id` retornado pelo Strava  
**Quando** `exchange_code(code)` é chamado com `code` válido  
**Então** cria novo `User` com `strava_athlete_id` e tokens persistidos

#### CN-2: Re-OAuth do mesmo atleta
**Dado** que já existe `User` com o `strava_athlete_id`  
**Quando** `exchange_code(code)` é chamado novamente  
**Então** atualiza tokens do `User` existente, preservando `user.id`

#### CN-3: URL de autorização
**Quando** `GET /auth/strava/authorize` é chamado  
**Então** retorna URL Strava contendo `client_id`, `redirect_uri`, `response_type=code` e `scope`

#### CN-4: Token ainda válido
**Dado** que `token_expires_at` >= now + 5 minutos  
**Quando** `ensure_valid_token(user)` é chamado  
**Então** retorna o `user` sem chamar refresh

### Casos de borda (Edge Cases)

#### CB-1: Token expira em menos de 5 minutos
**Dado** que `token_expires_at` < now + 5 minutos  
**Quando** `ensure_valid_token(user)` é chamado  
**Então** faz refresh proativo, persiste novos tokens e retorna `User` atualizado

#### CB-2: Dois OAuth simultâneos do mesmo atleta
**Dado** duas chamadas `exchange_code` concorrentes para o mesmo atleta  
**Quando** ambas completam  
**Então** último write vence (tokens mais recentes persistidos)

### Casos de erro

#### CE-1: Code inválido ou expirado
**Dado** que o Strava rejeita o `code`  
**Quando** `exchange_code(code)` ou `GET /auth/strava/callback` é chamado  
**Então** lança `StravaAuthError`; callback retorna HTTP 400

#### CE-2: Refresh token inválido
**Dado** que o refresh token foi revogado ou é inválido  
**Quando** `ensure_valid_token(user)` tenta refresh  
**Então** lança `StravaAuthError` (usuário precisa reautorizar)

#### CE-3: Strava API indisponível
**Dado** que a API Strava retorna 5xx  
**Quando** `exchange_code` ou refresh é chamado  
**Então** lança `StravaAuthError`; nenhum token parcial é persistido

#### CE-4: `strava_athlete_id` duplicado no DB
**Dado** violação de constraint de unicidade  
**Quando** `save` é chamado  
**Então** lança `DomainIntegrityError`

---

## Critérios de Aceite

- [ ] Spec com status **Aprovada** no repositório
- [ ] Migration 002 aplicável via `alembic upgrade head`
- [ ] Primeiro OAuth cria `User` com `strava_athlete_id` e tokens
- [ ] Re-OAuth do mesmo atleta atualiza tokens sem criar novo `User`
- [ ] `ensure_valid_token` faz refresh quando token está perto de expirar
- [ ] `GET /auth/strava/authorize` e `GET /auth/strava/callback` cobertos por testes
- [ ] Um teste por CN/CB/CE + contrato de repositório + integração OAuth
- [ ] CI verde (ruff, mypy, pytest)

---

## Decisões de Design

### Decisão: Strava-first
**Contexto:** Como usuários são criados no sistema.  
**Opção escolhida:** `User` nasce do OAuth nesta fase; sem registro independente.  
**Motivo:** Escopo mínimo da POC; SPEC-00X pode adicionar auth alternativa.

### Decisão: Callback retorna só `user_id`
**Contexto:** O que o app mobile recebe após OAuth.  
**Opção escolhida:** JSON `{ "user_id": "<uuid>" }` sem sessão/JWT.  
**Motivo:** SPEC-001 excluiu auth de usuário final; suficiente para validar OAuth em dev.

### Decisão: Refresh proativo com margem de 5 minutos
**Contexto:** Quando renovar access token.  
**Opção escolhida:** Refresh se `token_expires_at` < now + 5 min.  
**Motivo:** Evita falhas em chamadas subsequentes (SPEC-003/004).

### Decisão: Tokens em texto no banco
**Contexto:** Segurança de credenciais em repouso.  
**Opção escolhida:** Armazenamento em texto plano na POC.  
**Alternativas rejeitadas:** Criptografia agora (fora de escopo).  
**Motivo:** Risco documentado; spec futura de secrets.

### Decisão: `strava_athlete_id` único
**Contexto:** Relação User ↔ atleta Strava.  
**Opção escolhida:** Constraint UNIQUE no banco; um User por atleta.  
**Motivo:** Evita duplicidade e simplifica sync futuro.

---

## Notas de Migração

- Migration `002` adiciona colunas nullable em `users` para compatibilidade com registros existentes
- Índice único parcial ou constraint UNIQUE em `strava_athlete_id` (NULL permitido para usuários sem Strava)
