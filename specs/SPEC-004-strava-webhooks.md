# SPEC-004 — Webhooks Strava: ingestão incremental em tempo real

| Campo          | Valor                                              |
|----------------|----------------------------------------------------|
| **Status**     | Aprovada                                           |
| **Autor**      | @convertreino                                      |
| **Revisor**    | @convertreino                                      |
| **Criada em**  | 2026-06-17                                         |
| **Camada**     | Application + API + Infra                          |
| **Depende de** | SPEC-001, SPEC-002, SPEC-003                       |
| **Bloqueia**   | Engines analíticos (PR, consistência, volume), MCP tools |
| **Épico**      | Infra                                              |

---

## Contexto

Após o sync manual (SPEC-003), atividades novas ou alteradas no Strava não chegam ao banco automaticamente. O usuário precisaria disparar sync manualmente para ver insights atualizados — bloqueando engines analíticos e MCP tools com dados desatualizados.

---

## Escopo

### Incluído

- DTO `StravaWebhookEvent` (payload POST do Strava)
- `StravaApiClient.get_activity(access_token, activity_id) -> StravaActivitySummary`
- `StravaWebhookProcessor.handle_event(event) -> WebhookResult`
- Extensão `ActivityRepository.delete_by_external_id(user_id, external_id) -> bool`
- Rotas API:
  - `GET /webhooks/strava` — validação de subscription (hub challenge)
  - `POST /webhooks/strava` — recebimento de eventos
- Tratamento dos 4 tipos de evento Strava:
  - `activity` + `create` → fetch + upsert
  - `activity` + `update` → fetch + upsert
  - `activity` + `delete` → delete local por `external_id`
  - `athlete` + `update` com `authorized: false` → limpar tokens Strava do `User` (manter `User` e activities locais)
- Variáveis de ambiente: `STRAVA_WEBHOOK_VERIFY_TOKEN`, `STRAVA_WEBHOOK_CALLBACK_URL` (documentação de setup)
- Comando `curl` manual para criar subscription Strava
- `FakeStravaApiClient` estendido com `get_activity` e simulação de falhas
- Exceção `StravaActivityNotFoundError` para HTTP 404 em `get_activity`

### Excluído (explicitamente fora desta spec)

- Workers/filas (processamento síncrono na request, dentro do SLA de 2s do Strava)
- Recálculo de métricas analíticas (spec futura de engines)
- Auth Bearer/JWT nas rotas de webhook
- Múltiplas subscriptions (Strava permite 1 por app)
- Sync automático pós-OAuth (permanece manual; webhooks cobrem o incremental)
- Criptografia de tokens
- Retry com backoff sofisticado para falhas Strava API
- Deletar activities locais em massa no deauth do atleta
- Endpoint admin de subscription (`ENABLE_WEBHOOK_ADMIN`) — setup via `curl` manual na POC
- Tabela `webhook_events` para idempotência (idempotência via upsert/delete)

---

## Contrato

### DTO `StravaWebhookEvent`

Representa o payload JSON do POST de webhook Strava. Vive em `infrastructure/strava/webhook.py`.

| Campo             | Tipo   | Obrigatório | Descrição                                              |
|-------------------|--------|-------------|--------------------------------------------------------|
| `object_type`     | `str`  | Sim         | `"activity"` ou `"athlete"`                            |
| `aspect_type`     | `str`  | Sim         | `"create"`, `"update"` ou `"delete"`                   |
| `object_id`       | `int`  | Sim         | ID da atividade ou atleta no Strava                    |
| `owner_id`        | `int`  | Sim         | `strava_athlete_id` do dono do recurso                 |
| `updates`         | `dict` | Não         | Campos alterados (ex.: `{"authorized": "false"}`)      |
| `event_time`      | `int`  | Sim         | Unix timestamp do evento                               |
| `subscription_id` | `int`  | Sim         | ID da subscription Strava                              |

```python
def parse_strava_webhook_event(data: dict[str, object]) -> StravaWebhookEvent: ...
```

Lança `ValueError` se campos obrigatórios estiverem ausentes ou com tipo inválido.

### `StravaApiClient` (extensão)

```python
def get_activity(self, access_token: str, activity_id: int) -> StravaActivitySummary: ...
```

| Status Strava | Exceção                      | Uso no webhook                                      |
|---------------|------------------------------|-----------------------------------------------------|
| 401, 403      | `StravaAuthError`            | Log warning; `action=ignored`; POST retorna 200     |
| 404           | `StravaActivityNotFoundError`| Delete local se existia; senão `ignored`            |
| 5xx           | `StravaApiError`             | Log error; `action=ignored`; POST retorna 200       |

`get_activity` retorna o mesmo shape `StravaActivitySummary` usado em `list_activities` (reuso do mapper SPEC-003).

### `ActivityRepository` (extensão)

```python
def delete_by_external_id(self, user_id: UUID, external_id: str) -> bool: ...
```

| Retorno | Comportamento                                      |
|---------|----------------------------------------------------|
| `True`  | Atividade removida                                 |
| `False` | Nenhuma atividade com o par `(user_id, external_id)` — idempotente |

### `StravaWebhookProcessor`

```python
@dataclass(frozen=True)
class WebhookResult:
    action: Literal["created", "updated", "deleted", "deauthorized", "ignored"]
    user_id: UUID | None

def handle_event(self, event: StravaWebhookEvent) -> WebhookResult: ...
```

**Fluxo interno:**

1. `UserRepository.get_by_strava_athlete_id(event.owner_id)` — se `None` → log warning, retorna `action=ignored`, `user_id=None`
2. Se `object_type == "activity"` e `aspect_type in ("create", "update")`:
   - `ensure_valid_token(user)` (SPEC-002)
   - `get_activity(access_token, event.object_id)`
   - `map_strava_activity_to_domain` — se `None` → log warning, `action=ignored`
   - `get_by_external_id` antes do upsert para distinguir `created` vs `updated`
   - `upsert(activity)` → `action=created` ou `updated`
3. Se `object_type == "activity"` e `aspect_type == "delete"`:
   - `delete_by_external_id(user.id, str(event.object_id))` → `action=deleted` (mesmo se `False`)
4. Se `object_type == "athlete"` e `aspect_type == "update"` e `updates.get("authorized") == "false"`:
   - Salvar `User` com `access_token=None`, `refresh_token=None`, `token_expires_at=None` (preserva `strava_athlete_id` e activities)
   - `action=deauthorized`
5. Demais combinações → `action=ignored`, log info

**Tratamento de exceções no fluxo activity create/update:**

| Exceção                      | Comportamento no processor                          |
|------------------------------|-----------------------------------------------------|
| `StravaAuthError`            | Log warning; `action=ignored`                       |
| `StravaApiError`             | Log error; `action=ignored`                       |
| `StravaActivityNotFoundError`| Se existia localmente → delete; senão `ignored`     |

### API

| Método | Path               | Comportamento                                                                 |
|--------|--------------------|-------------------------------------------------------------------------------|
| GET    | `/webhooks/strava` | Query `hub.mode`, `hub.challenge`, `hub.verify_token`                         |
| POST   | `/webhooks/strava` | Body JSON do evento → processa → `200` com `WebhookResult`                    |

**GET — validação de subscription:**

| Query param         | Descrição                          |
|---------------------|------------------------------------|
| `hub.mode`          | Deve ser `"subscribe"`             |
| `hub.challenge`     | Valor a ecoar na resposta          |
| `hub.verify_token`  | Comparado com `STRAVA_WEBHOOK_VERIFY_TOKEN` |

| Código | Condição                                      | Corpo                                      |
|--------|-----------------------------------------------|--------------------------------------------|
| 200    | Token válido                                  | `{"hub.challenge": "<valor>"}`             |
| 403    | `hub.verify_token` inválido                   | `{"detail": "Invalid verify token"}`       |

**POST — recebimento de eventos:**

| Código | Condição                                      | Corpo                                      |
|--------|-----------------------------------------------|--------------------------------------------|
| 200    | Evento processado ou ignorado com segurança   | `WebhookResult` serializado                |
| 400    | JSON malformado ou campos obrigatórios ausentes | `{"detail": "Invalid webhook payload"}`  |

Sem autenticação Bearer/JWT (POC, consistente com SPEC-002/003).

### Subscription (setup manual)

Variáveis de ambiente:

| Variável                    | Descrição                                      |
|-----------------------------|------------------------------------------------|
| `STRAVA_WEBHOOK_VERIFY_TOKEN` | Token secreto escolhido pelo operador       |
| `STRAVA_WEBHOOK_CALLBACK_URL` | URL pública `https://<host>/webhooks/strava` |

Comando para criar subscription (após deploy com URL pública):

```bash
curl -X POST https://www.strava.com/api/v3/push_subscriptions \
  -F client_id=$STRAVA_CLIENT_ID \
  -F client_secret=$STRAVA_CLIENT_SECRET \
  -F callback_url=$STRAVA_WEBHOOK_CALLBACK_URL \
  -F verify_token=$STRAVA_WEBHOOK_VERIFY_TOKEN
```

O Strava enviará GET de validação imediatamente; o endpoint deve estar acessível.

### Efeitos colaterais

- Escrita em `activities` (upsert ou delete via webhook)
- Possível refresh de token e atualização de `users` (via `ensure_valid_token`)
- Limpeza de tokens em deauth de atleta
- Logs de warning/error para eventos ignorados ou falhas Strava

---

## Comportamentos

### Casos normais (Happy Path)

#### CN-1: GET com verify_token correto retorna challenge
**Dado** que `STRAVA_WEBHOOK_VERIFY_TOKEN` está configurado como `"my-secret"`  
**Quando** `GET /webhooks/strava?hub.mode=subscribe&hub.challenge=abc123&hub.verify_token=my-secret` é chamado  
**Então** retorna HTTP 200 com `{"hub.challenge": "abc123"}`

#### CN-2: POST activity/create para atleta conhecido
**Dado** um `User` com `strava_athlete_id=88001` vinculado e o Strava retorna a atividade `5001`  
**Quando** `POST /webhooks/strava` recebe evento `object_type=activity`, `aspect_type=create`, `object_id=5001`, `owner_id=88001`  
**Então** atividade é persistida via upsert, resposta HTTP 200 com `action=created` e `user_id` do usuário

#### CN-3: POST activity/update
**Dado** atividade local com `external_id="5002"` e o Strava retorna dados atualizados para `object_id=5002`  
**Quando** evento `activity/update` é processado  
**Então** `upsert` atualiza campos mutáveis, resposta com `action=updated`

#### CN-4: POST activity/delete
**Dado** atividade local com `external_id="5003"`  
**Quando** evento `activity/delete` com `object_id=5003` é processado  
**Então** atividade removida do banco, resposta com `action=deleted`

#### CN-5: POST athlete/update com authorized=false
**Dado** um `User` com tokens Strava válidos e `strava_athlete_id=88002`  
**Quando** evento `athlete/update` com `updates={"authorized": "false"}` e `owner_id=88002`  
**Então** tokens do usuário são limpos (`access_token`, `refresh_token`, `token_expires_at` = `None`), activities locais permanecem, resposta com `action=deauthorized`

### Casos de borda (Edge Cases)

#### CB-1: Delete de atividade inexistente localmente
**Dado** nenhuma atividade com `external_id="9999"` para o usuário  
**Quando** evento `activity/delete` com `object_id=9999` é processado  
**Então** `delete_by_external_id` retorna `False`, resposta com `action=deleted` (sem erro)

#### CB-2: Atleta desconhecido
**Dado** nenhum `User` com `strava_athlete_id=77777`  
**Quando** qualquer evento com `owner_id=77777` é processado  
**Então** `action=ignored`, `user_id=None`, log warning

#### CB-3: Atividade inválida no mapper
**Dado** `get_activity` retorna summary com `distance=-1`  
**Quando** evento `activity/create` é processado  
**Então** `action=ignored`, nenhuma escrita no banco, log warning

#### CB-4: Token perto de expirar
**Dado** `token_expires_at` < now + 5 minutos  
**Quando** evento `activity/create` dispara fetch  
**Então** `ensure_valid_token` faz refresh proativo antes de `get_activity` (reuso SPEC-002)

#### CB-5: Reenvio do mesmo evento create
**Dado** atividade já persistida com `external_id="6001"`  
**Quando** o mesmo evento `activity/create` com `object_id=6001` é reprocessado  
**Então** upsert idempotente, `action=updated` na segunda vez

### Casos de erro

#### CE-1: GET com verify_token incorreto
**Dado** `STRAVA_WEBHOOK_VERIFY_TOKEN="correct"`  
**Quando** `GET /webhooks/strava?hub.verify_token=wrong&hub.mode=subscribe&hub.challenge=x`  
**Então** HTTP 403 com `{"detail": "Invalid verify token"}`

#### CE-2: POST com JSON inválido
**Dado** body não parseável como JSON ou sem campos obrigatórios  
**Quando** `POST /webhooks/strava` é chamado  
**Então** HTTP 400 com `{"detail": "Invalid webhook payload"}`

#### CE-3: get_activity retorna 401/403
**Dado** access token revogado e Strava rejeita `get_activity`  
**Quando** evento `activity/create` é processado  
**Então** log warning, `action=ignored`, POST retorna HTTP 200 (Strava não reenvia)

#### CE-4: get_activity retorna 404
**Dado** atividade local com `external_id="7001"` OU sem registro local  
**Quando** `get_activity` lança `StravaActivityNotFoundError` para `object_id=7001`  
**Então** se existia localmente → delete e `action=deleted`; se não existia → `action=ignored`

---

## Critérios de Aceite

- [ ] Spec com status **Aprovada** no repositório
- [ ] Migration não necessária (sem schema novo)
- [ ] GET challenge coberto por teste de integração
- [ ] Um teste unitário por CN/CB/CE do processor
- [ ] `FakeStravaApiClient` com `get_activity` e falhas simuláveis
- [ ] Contrato estendido de `ActivityRepository` e `StravaApiClient`
- [ ] `delete_by_external_id` testado em in-memory e integração Postgres
- [ ] CI verde (ruff, mypy, pytest)

---

## Mapeamento Spec → Testes

| Artefato                                  | Localização                                                      |
|-------------------------------------------|------------------------------------------------------------------|
| CN/CB/CE do `StravaWebhookProcessor`      | `backend/tests/unit/application/test_strava_webhook_processor.py` |
| GET challenge + POST eventos              | `backend/tests/integration/test_strava_webhooks.py`             |
| Contrato `ActivityRepository` estendido   | `backend/tests/contracts/test_repository_contracts.py`            |
| Contrato `StravaApiClient` estendido      | `backend/tests/contracts/test_strava_client_contract.py`          |
| `delete_by_external_id` Postgres          | `backend/tests/integration/test_strava_webhooks.py`               |

---

## Decisões de Design

### Decisão: Processamento síncrono na request
**Contexto:** Strava exige resposta em até 2 segundos.  
**Opção escolhida:** Processar evento na mesma request HTTP, sem fila.  
**Alternativas rejeitadas:** Worker assíncrono com fila Redis/SQS.  
**Motivo:** POC com escopo mínimo; volume de eventos por usuário é baixo.

### Decisão: Falha Strava API no POST → 200 + log
**Contexto:** Strava não reenvia eventos quando recebe HTTP 200.  
**Opção escolhida:** Em `StravaApiError` ou `StravaAuthError` durante fetch, retornar `action=ignored` e HTTP 200; logar para operador forçar sync manual.  
**Alternativas rejeitadas:** HTTP 502 para trigger de retry Strava.  
**Motivo:** Evita perda silenciosa sem visibilidade; operador pode usar `POST /users/{id}/sync/strava` como fallback.

### Decisão: get_activity 404 → delete local se existia
**Contexto:** Atividade pode ter sido removida no Strava antes do webhook de delete.  
**Opção escolhida:** Se registro local existe → `delete_by_external_id`; senão → `ignored`.  
**Alternativas rejeitadas:** Sempre ignorar 404.  
**Motivo:** Mantém consistência eventual com estado do Strava.

### Decisão: Deauth limpa só tokens
**Contexto:** Atleta revoga acesso no Strava.  
**Opção escolhida:** Zerar `access_token`, `refresh_token`, `token_expires_at`; manter `User`, `strava_athlete_id` e activities locais.  
**Alternativas rejeitadas:** Deletar activities em massa.  
**Motivo:** Privacidade incremental; dados históricos podem ser úteis até decisão explícita do usuário.

### Decisão: Subscription setup via curl manual
**Contexto:** Criar push subscription requer URL pública.  
**Opção escolhida:** Documentar comando `curl` + variáveis de ambiente.  
**Alternativas rejeitadas:** Endpoint admin `POST /admin/strava/webhooks/subscribe`.  
**Motivo:** Menor escopo na POC; operação única por ambiente.

### Decisão: Reuso do mapper e StravaActivitySummary
**Contexto:** `GET /activities/{id}` retorna shape compatível com summary de listagem.  
**Opção escolhida:** `get_activity` retorna `StravaActivitySummary`; mapper SPEC-003 sem alteração.  
**Alternativas rejeitadas:** DTO separado para detalhe de atividade.  
**Motivo:** Campos necessários já cobertos; evita duplicação.

---

## Notas de Migração

- Nenhuma migration necessária
- Novas variáveis de ambiente opcionais em dev (`STRAVA_WEBHOOK_VERIFY_TOKEN`, `STRAVA_WEBHOOK_CALLBACK_URL`)
- Rollback: remover rotas e processor sem impacto em dados existentes

---

## Checklist de revisão (seção 12 do guia)

### Clareza
- [x] O contexto explica o problema sem descrever a solução
- [x] O contrato tem tipos explícitos para todos os inputs e outputs
- [x] Cada comportamento tem "Dado / Quando / Então" completo
- [x] Os critérios de aceite são binários e verificáveis

### Completude
- [x] Há ao menos um caso normal (CN-1 a CN-5)
- [x] Casos de borda cobertos (delete idempotente, atleta desconhecido, mapper skip, token refresh, reenvio)
- [x] Casos de erro especificados com código HTTP e comportamento
- [x] Escopo "Excluído" deixa claro o que ficou de fora

### Consistência
- [x] Não contradiz SPEC-002 (tokens, refresh) nem SPEC-003 (upsert, mapper, exceções)
- [x] Nomes de tipos alinhados ao código existente
- [x] Processor na application; DTO webhook na infra; domínio sem JSON Strava

### Testabilidade
- [x] Cada comportamento mapeia para teste unitário ou integração
- [x] Comportamentos determinísticos
- [x] Efeitos colaterais explicitados e testáveis
