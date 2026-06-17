# SPEC-003 — Sync de Atividades Strava: importação manual do histórico completo

| Campo          | Valor                                              |
|----------------|----------------------------------------------------|
| **Status**     | Aprovada                                           |
| **Autor**      | @convertreino                                      |
| **Revisor**    | @convertreino                                      |
| **Criada em**  | 2026-06-17                                         |
| **Camada**     | Domain + Application + API + Infra                 |
| **Depende de** | SPEC-001, SPEC-002                               |
| **Bloqueia**   | SPEC-004 (webhooks), engines analíticos, MCP tools |
| **Épico**      | Infra                                              |

---

## Contexto

Após vincular a conta Strava, o sistema não possui atividades reais no banco. Sem sync, nenhum insight analítico ou tool MCP pode responder perguntas sobre performance do usuário.

A SPEC-001 reservou `Activity.external_id` e a SPEC-002 entregou tokens OAuth reutilizáveis; esta spec fecha o ciclo importando o histórico completo de atividades do atleta.

---

## Escopo

### Incluído

- `StravaActivitySummary` (DTO de infraestrutura) + mapper `Strava → Activity` em `infrastructure/strava/mapper.py`
- Extensão `StravaApiClient.list_activities(access_token, *, page, per_page)` com paginação
- `FakeStravaApiClient` com lista configurável de atividades e falhas simuláveis por página
- `StravaSyncService.sync_user(user_id)` — orquestra `ensure_valid_token` → paginação → upsert
- Extensão `ActivityRepository`:
  - `get_by_external_id(user_id, external_id) -> Activity | None`
  - `upsert(activity) -> Activity` (insert ou update por par `(user_id, external_id)`)
- Exceção `UserNotFoundError` quando `user_id` não existe
- Migration `003`: índice **UNIQUE** em `(user_id, external_id)` onde `external_id IS NOT NULL`
- Endpoint `POST /users/{user_id}/sync/strava` (sem auth JWT — consistente com POC)
- Resposta com contagem: `{ "synced_count", "created_count", "updated_count", "skipped_count" }`

### Excluído (explicitamente fora desta spec)

- Sync automático pós-OAuth callback
- Webhooks / subscription Strava → SPEC-004
- Filtro por tipo de atividade (Run only) — engines filtram depois
- Janela temporal limitada (sync do histórico completo)
- Workers/filas, Redis, rate-limit backoff sofisticado
- Campos extras de atividade (elevação, pace, splits, nome)
- Auth Bearer para API do app
- Criptografia de tokens (herdado da SPEC-002)

---

## Contrato

### DTO `StravaActivitySummary` (Infra)

Representa um item do endpoint Strava `GET /athlete/activities` (summary). Vive em `infrastructure/strava/client.py` ou módulo adjacente; o domínio **não** conhece este tipo.

| Campo Strava (JSON) | Tipo Python | Obrigatório | Descrição                          |
|---------------------|-------------|-------------|------------------------------------|
| `id`                | `int`       | Sim         | ID da atividade no Strava          |
| `distance`          | `float`     | Não         | Metros; default `0.0` se ausente   |
| `elapsed_time`      | `int`       | Não         | Segundos totais                    |
| `moving_time`       | `int`       | Não         | Segundos em movimento (fallback)   |
| `start_date`        | `str`       | Sim         | ISO 8601 (ex.: `2024-01-15T10:00:00Z`) |
| `type`              | `str`       | Sim         | Tipo literal Strava (ex.: `"Run"`) |

### Mapper `map_strava_activity_to_domain`

```python
def map_strava_activity_to_domain(
    summary: StravaActivitySummary,
    *,
    user_id: UUID,
) -> Activity | None: ...
```

| Campo Strava (summary) | Campo `Activity`       | Regra                                                        |
|------------------------|------------------------|--------------------------------------------------------------|
| `id`                   | `external_id`          | `str(summary.id)`                                            |
| `distance`             | `distance_meters`      | `float`; default `0.0` se ausente                            |
| `elapsed_time`         | `elapsed_time_seconds` | `int`; preferir `elapsed_time`, fallback `moving_time`       |
| `start_date`           | `start_date`           | ISO 8601 → `datetime` UTC                                    |
| `type`                 | `activity_type`        | string literal do Strava (ex.: `"Run"`)                      |
| —                      | `user_id`              | injetado pelo service                                        |
| —                      | `id`                   | UUID novo no insert; preservado no update (via `upsert`)     |

**Atividades inválidas:** se após normalização `distance_meters < 0` ou `elapsed_time_seconds < 0`, ou se `start_date`/`type` estiverem ausentes, o mapper retorna `None` (não lança exceção). O service incrementa `skipped_count` e registra warning em log.

### `StravaApiClient` (extensão)

```python
def list_activities(
    self,
    access_token: str,
    *,
    page: int = 1,
    per_page: int = 200,
) -> list[StravaActivitySummary]: ...
```

| Parâmetro     | Tipo  | Obrigatório | Descrição                                      |
|---------------|-------|-------------|------------------------------------------------|
| `access_token`| `str` | Sim         | Token OAuth válido                             |
| `page`        | `int` | Não         | Página 1-based (padrão Strava)                 |
| `per_page`    | `int` | Não         | Máximo 200 (limite Strava)                     |

**Erros HTTP mapeados:**

| Status Strava | Exceção           | Uso no sync                          |
|---------------|-------------------|--------------------------------------|
| 401, 403      | `StravaAuthError` | Token revogado — reautorizar         |
| 5xx           | `StravaApiError`* | API indisponível                     |

\* Nova exceção `StravaApiError` em `domain/exceptions.py` para distinguir falha transitória (502 na API) de falha de auth (400). Alternativa aceitável: reutilizar `StravaAuthError` apenas para 401/403 e `StravaApiError` para 5xx.

### `ActivityRepository` (extensão)

```python
def get_by_external_id(self, user_id: UUID, external_id: str) -> Activity | None: ...

def upsert(self, activity: Activity) -> Activity: ...
```

| Método               | Input                         | Output    | Comportamento                                                                 |
|----------------------|-------------------------------|-----------|-------------------------------------------------------------------------------|
| `get_by_external_id` | `user_id`, `external_id`      | `Activity \| None` | Retorna atividade existente ou `None`                                |
| `upsert`             | `Activity` com `external_id`  | `Activity`| Se existe par `(user_id, external_id)`: atualiza campos mutáveis, preserva `id`; senão: insert com novo UUID |

Campos mutáveis no update: `distance_meters`, `elapsed_time_seconds`, `start_date`, `activity_type`. `user_id` e `external_id` são a chave lógica.

### `StravaSyncService`

```python
@dataclass(frozen=True)
class SyncResult:
    synced_count: int    # processadas com sucesso (created + updated)
    created_count: int
    updated_count: int
    skipped_count: int   # inválidas ou não mapeáveis

def sync_user(self, user_id: UUID) -> SyncResult: ...
```

| Campo            | Tipo  | Descrição                                              |
|------------------|-------|--------------------------------------------------------|
| `synced_count`   | `int` | `created_count + updated_count`                        |
| `created_count`  | `int` | Novas atividades inseridas                             |
| `updated_count`  | `int` | Atividades existentes atualizadas                      |
| `skipped_count`  | `int` | Itens Strava ignorados pelo mapper                     |

**Fluxo interno:**

1. `UserRepository.get_by_id(user_id)` — se `None` → `UserNotFoundError`
2. Se `strava_athlete_id` ou tokens ausentes → `StravaAuthError` (usuário sem vínculo Strava)
3. `StravaOAuthService.ensure_valid_token(user)` — refresh proativo se necessário (SPEC-002)
4. Loop `page = 1, 2, ...`:
   - `list_activities(access_token, page=page, per_page=PER_PAGE)`
   - Se lista vazia → encerra loop
   - Para cada item: `mapper` → se `None`, `skipped_count++`; senão `upsert` e incrementa `created_count` ou `updated_count`
   - Commit da transação da página (ver Decisões de Design)
   - Se `len(page) < PER_PAGE` → última página, encerra loop
   - Se `page > MAX_PAGES` → encerra com warning (guarda de segurança)
5. Retorna `SyncResult` agregado

**Constantes:**

| Constante  | Valor | Descrição                                      |
|------------|-------|------------------------------------------------|
| `PER_PAGE` | `200` | Máximo permitido pela API Strava               |
| `MAX_PAGES`| `500` | Guarda opcional (~100k atividades)             |

### API

| Método | Path                            | Request body | Response 200                          |
|--------|---------------------------------|--------------|---------------------------------------|
| POST   | `/users/{user_id}/sync/strava`  | (vazio)      | `SyncResult` serializado em JSON      |

| Código | Condição                                              | Corpo de erro (exemplo)                    |
|--------|-------------------------------------------------------|--------------------------------------------|
| 200    | Sync concluído (inclui 0 atividades)                  | `{ "synced_count": 0, ... }`               |
| 400    | Usuário sem vínculo Strava / tokens (`StravaAuthError`)| `{ "detail": "..." }`                      |
| 400    | Strava retorna 401/403 (`StravaAuthError`)            | `{ "detail": "Reauthorize Strava account" }` |
| 404    | `user_id` inexistente (`UserNotFoundError`)           | `{ "detail": "User not found" }`             |
| 502    | Strava retorna 5xx (`StravaApiError`)                 | `{ "detail": "Strava API unavailable" }`   |

Sem autenticação nas rotas (POC, consistente com SPEC-002).

### Efeitos colaterais

- Escrita em `activities` (insert/update via `upsert`)
- Possível refresh de token e atualização de `users` (via `ensure_valid_token`)
- Logs de warning para atividades ignoradas pelo mapper

---

## Comportamentos

### Casos normais (Happy Path)

#### CN-1: Primeira sync com atividades novas
**Dado** um `User` com Strava vinculado, 0 atividades locais, e o Strava retorna 3 atividades na página 1  
**Quando** `StravaSyncService.sync_user(user_id)` é chamado  
**Então** `created_count=3`, `updated_count=0`, `synced_count=3`, `skipped_count=0`, e todas as atividades persistidas têm `external_id` preenchido

#### CN-2: Re-sync idempotente
**Dado** que as mesmas 3 atividades já foram sincronizadas e o Strava retorna os mesmos dados  
**Quando** `sync_user(user_id)` é chamado novamente  
**Então** `created_count=0`, `updated_count=3`, `synced_count=3`, sem duplicatas no banco

#### CN-3: Histórico paginado
**Dado** um atleta com 250 atividades no Strava (página 1 com 200 itens, página 2 com 50)  
**Quando** `sync_user(user_id)` é chamado  
**Então** todas as 250 atividades são importadas; `created_count=250` na primeira execução

#### CN-4: Endpoint de sync
**Dado** um `User` com Strava vinculado e atividades disponíveis no Strava  
**Quando** `POST /users/{user_id}/sync/strava` é chamado  
**Então** retorna HTTP 200 com JSON contendo `synced_count`, `created_count`, `updated_count` e `skipped_count` corretos

### Casos de borda (Edge Cases)

#### CB-1: Strava retorna lista vazia
**Dado** um `User` com Strava vinculado e o Strava retorna `[]` na página 1  
**Quando** `sync_user(user_id)` é chamado  
**Então** `synced_count=0`, `created_count=0`, `updated_count=0`, `skipped_count=0`, sem erro

#### CB-2: Atividade com distância zero
**Dado** uma atividade Strava com `distance=0` (ex.: warmup)  
**Quando** o mapper processa o item e o service faz upsert  
**Então** persiste com `distance_meters=0` (válido, alinhado à SPEC-001 CB-2)

#### CB-3: Token perto de expirar
**Dado** que `token_expires_at` < now + 5 minutos  
**Quando** `sync_user(user_id)` é chamado  
**Então** `ensure_valid_token` faz refresh proativo antes de `list_activities` (reuso SPEC-002 CB-1)

#### CB-4: Atividade existente com dados alterados no Strava
**Dado** uma atividade local com `external_id="12345"` e o Strava retorna o mesmo `id` com `distance` atualizado  
**Quando** `sync_user(user_id)` é chamado  
**Então** `upsert` atualiza `distance_meters` e demais campos mutáveis, preservando o `id` interno (UUID)

#### CB-5: Atividade Strava inválida no mapper
**Dado** um item Strava com `distance=-1` após normalização  
**Quando** `sync_user(user_id)` processa a página  
**Então** item é ignorado, `skipped_count` incrementado, demais atividades da página são persistidas normalmente

### Casos de erro

#### CE-1: user_id inexistente
**Dado** um `user_id` que não existe no repositório  
**Quando** `sync_user(user_id)` ou `POST /users/{user_id}/sync/strava` é chamado  
**Então** lança `UserNotFoundError`; endpoint retorna HTTP 404

#### CE-2: Usuário sem vínculo Strava
**Dado** um `User` existente com `strava_athlete_id=None` ou tokens ausentes  
**Quando** `sync_user(user_id)` é chamado  
**Então** lança `StravaAuthError` com mensagem clara; endpoint retorna HTTP 400

#### CE-3: Strava retorna 401 ou 403
**Dado** que o access token foi revogado e o Strava rejeita `list_activities`  
**Quando** `sync_user(user_id)` é chamado  
**Então** lança `StravaAuthError`; endpoint retorna HTTP 400 (usuário deve reautorizar)

#### CE-4: Strava retorna 5xx
**Dado** que a API Strava retorna erro 5xx na página corrente  
**Quando** `sync_user(user_id)` é chamado  
**Então** lança `StravaApiError`; endpoint retorna HTTP 502; **nenhuma atividade da página corrente é persistida** (rollback da transação da página); páginas já commitadas permanecem

#### CE-5: Violação UNIQUE `(user_id, external_id)`
**Dado** violação de constraint de unicidade no banco  
**Quando** `upsert` ou `save` é chamado incorretamente (bypass da lógica de upsert)  
**Então** lança `DomainIntegrityError` (não deve ocorrer com upsert correto)

---

## Critérios de Aceite

- [ ] Spec com status **Aprovada** no repositório
- [ ] Migration `003` aplicável via `alembic upgrade head` (índice UNIQUE parcial em `(user_id, external_id)`)
- [ ] `upsert` cria na primeira sync e atualiza na segunda sem duplicar registros
- [ ] Paginação percorre todas as páginas até lista vazia ou `< PER_PAGE` itens
- [ ] `external_id` preenchido para toda atividade sincronizada com sucesso
- [ ] `skipped_count` reflete atividades ignoradas pelo mapper
- [ ] `POST /users/{user_id}/sync/strava` retorna 200/400/404/502 conforme contrato
- [ ] Um teste unitário por CN/CB/CE + contrato de repositório estendido + integração com PostgreSQL
- [ ] CI verde (ruff, mypy, pytest)

---

## Mapeamento Spec → Testes

| Artefato                                  | Localização                                                      |
|-------------------------------------------|------------------------------------------------------------------|
| Testes CN/CB/CE do `StravaSyncService`    | `backend/tests/unit/application/test_strava_sync_service.py`     |
| Testes do mapper                          | `backend/tests/unit/infrastructure/test_strava_activity_mapper.py` |
| Contrato `ActivityRepository` estendido   | `backend/tests/contracts/test_repository_contracts.py`           |
| Integração sync + Postgres                | `backend/tests/integration/test_strava_activity_sync.py`         |
| Integração endpoint                       | `backend/tests/integration/test_strava_activity_sync.py` (ou `test_strava_sync_api.py`) |
| `FakeStravaApiClient` estendido             | `backend/src/convertreino/infrastructure/strava/fake_client.py` |

Padrão AAA obrigatório; builders existentes em `backend/tests/builders/`.

| Comportamento | Tipo de teste   |
|---------------|-----------------|
| CN-1 a CN-4   | Unitário + integração (CN-4) |
| CB-1 a CB-5   | Unitário        |
| CE-1 a CE-5   | Unitário + integração (CE-1, CE-4) |
| Contrato repo | Contrato        |
| Migration 003 | Integração      |

---

## Decisões de Design

### Decisão: Upsert por `(user_id, external_id)`
**Contexto:** Re-syncs e reimportações devem ser seguras.  
**Opção escolhida:** `upsert` com chave lógica `(user_id, external_id)`.  
**Alternativas rejeitadas:** `save` cego (gera duplicatas).  
**Motivo:** Idempotência obrigatória para histórico completo e base para webhooks (SPEC-004).

### Decisão: Atomicidade por página
**Contexto:** Falha no meio de um histórico grande (centenas de páginas).  
**Opção escolhida:** Transação com commit após cada página processada com sucesso.  
**Alternativas rejeitadas:** Transação única para todo o histórico (perda total em falha tardia).  
**Motivo:** Reduz perda de trabalho; CE-4 documenta que páginas anteriores já commitadas permanecem.

### Decisão: Erro HTTP Strava 5xx → 502
**Contexto:** Diferenciar falha de auth de indisponibilidade transitória.  
**Opção escolhida:** `StravaApiError` + HTTP 502; não persistir página corrente.  
**Alternativas rejeitadas:** HTTP 500 genérico (menos semântico para cliente).  
**Motivo:** Cliente pode distinguir "reautorizar" (400) de "tentar depois" (502).

### Decisão: `elapsed_time` prioritário sobre `moving_time`
**Contexto:** Strava expõe dois campos de duração no summary.  
**Opção escolhida:** Usar `elapsed_time`; fallback para `moving_time` se ausente.  
**Motivo:** Alinhado ao campo `elapsed_time_seconds` da entidade `Activity`.

### Decisão: Mapper na Infra
**Contexto:** Onde converter JSON Strava para domínio.  
**Opção escolhida:** `infrastructure/strava/mapper.py`.  
**Alternativas rejeitadas:** Mapper no domínio (acopla domínio ao Strava).  
**Motivo:** Domínio não conhece formatos externos.

### Decisão: Atividades inválidas → skip com contagem
**Contexto:** Dados inconsistentes vindos do Strava.  
**Opção escolhida:** Mapper retorna `None`; service incrementa `skipped_count` e loga warning.  
**Alternativas rejeitadas:** Falhar sync inteiro por um item inválido.  
**Motivo:** Maximiza dados úteis importados; operador vê `skipped_count` na resposta.

### Decisão: `UserNotFoundError` dedicada
**Contexto:** Usuário inexistente no sync.  
**Opção escolhida:** Nova exceção `UserNotFoundError` em `domain/exceptions.py`.  
**Alternativas rejeitadas:** Retornar `None` silencioso ou `StravaAuthError` genérico.  
**Motivo:** CE-1 exige HTTP 404 distinto de 400; falha explícita.

### Decisão: Disparo apenas manual
**Contexto:** Quando executar o sync.  
**Opção escolhida:** Endpoint `POST` explícito; sem hook no callback OAuth.  
**Motivo:** Escopo mínimo da POC; SPEC-004 cobrirá atualização contínua.

### Decisão: Histórico completo sem filtro temporal
**Contexto:** Quantas atividades importar.  
**Opção escolhida:** Todas as páginas até esgotar.  
**Alternativas rejeitadas:** Janela de N dias, filtro Run-only.  
**Motivo:** Engines e MCP filtram depois; dados completos desde o início.

---

## Notas de Migração

- Coluna `external_id` já existe em `activities` (nullable, SPEC-001); migration `003` adiciona apenas índice UNIQUE composto
- Constraint parcial: `UNIQUE (user_id, external_id) WHERE external_id IS NOT NULL` — registros legados com `external_id=NULL` não conflitam
- Nenhuma alteração em `users` (campos Strava já existem via migration `002`)
- Rollback da migration `003` remove o índice sem perda de dados

---

## Checklist de revisão (seção 12 do guia)

### Clareza
- [x] O contexto explica o problema sem descrever a solução
- [x] O contrato tem tipos explícitos para todos os inputs e outputs
- [x] Cada comportamento tem "Dado / Quando / Então" completo
- [x] Os critérios de aceite são binários e verificáveis

### Completude
- [x] Há ao menos um caso normal (CN-1 a CN-4)
- [x] Casos de borda cobertos (lista vazia, distância zero, token refresh, update, skip)
- [x] Casos de erro especificados com exceção e código HTTP
- [x] Escopo "Excluído" deixa claro o que ficou de fora

### Consistência
- [x] Não contradiz SPEC-001 (validação de Activity, `external_id` nullable) nem SPEC-002 (tokens, refresh)
- [x] Nomes de tipos alinhados ao código existente (`Activity`, `StravaAuthError`, `DomainIntegrityError`)
- [x] Mapper na infra; service na application; domínio sem JSON Strava

### Testabilidade
- [x] Cada comportamento mapeia para teste unitário ou integração
- [x] Comportamentos determinísticos (mesmo input Strava → mesmo `SyncResult`)
- [x] Efeitos colaterais explicitados (banco, tokens, logs)
