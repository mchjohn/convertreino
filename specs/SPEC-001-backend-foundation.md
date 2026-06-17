# SPEC-001 — Fundação do Backend: entidades, repositórios e persistência

| Campo          | Valor                                              |
|----------------|----------------------------------------------------|
| **Status**     | Aprovada                                           |
| **Autor**      | @convertreino                                      |
| **Revisor**    | @convertreino                                      |
| **Criada em**  | 2026-06-17                                         |
| **Camada**     | Domain + Infra (API entra apenas com `GET /health`) |
| **Depende de** | Nenhuma                                            |
| **Épico**      | Infra                                              |
| **Bloqueia**   | Toda spec posterior (Strava, engines, MCP, API de chat) |

---

## Contexto

Antes de sincronizar dados do Strava ou calcular insights, o sistema precisa de um modelo de domínio compartilhado, contratos de persistência testáveis e uma base de projeto que permita SDD+TDD nas specs seguintes.

---

## Escopo

### Incluído

- Layout do projeto `backend/` com separação `domain/` vs `infrastructure/`
- Entidades de domínio `User` e `Activity` (campos mínimos derivados dos exemplos do guia)
- Interfaces `UserRepository` e `ActivityRepository`
- Implementações SQLAlchemy sync + Alembic (migrations iniciais)
- Repositórios in-memory para testes unitários
- Builders de teste (`build_user`, `build_activity`)
- Configuração pytest + cobertura mínima para camada Domain (>= 95%)
- CI básico (lint, typecheck, testes)
- Endpoint `GET /health` retornando `{ "status": "ok" }`
- `docker-compose.yml` com PostgreSQL para desenvolvimento e testes de integração

### Excluído (explicitamente fora desta spec)

- OAuth / tokens Strava
- Webhooks Strava
- Cálculos analíticos (pace, volume, PR, tendência)
- Cache (Redis)
- MCP tools e integração LLM
- Autenticação JWT/sessão de usuário final
- Workers/filas
- Frontend/mobile

---

## Contrato

### Entidade `User`

| Campo        | Tipo             | Obrigatório | Descrição              |
|--------------|------------------|-------------|------------------------|
| `id`         | UUID             | Sim         | Identificador interno  |
| `created_at` | datetime (UTC)   | Sim         | Timestamp de criação   |

> Campos Strava (`strava_athlete_id`, tokens) ficam para SPEC-002.

### Entidade `Activity`

| Campo                  | Tipo             | Obrigatório | Descrição                                      |
|------------------------|------------------|-------------|------------------------------------------------|
| `id`                   | UUID             | Sim         | ID interno                                     |
| `user_id`              | UUID             | Sim         | FK lógica para User                            |
| `distance_meters`      | float            | Sim         | Distância >= 0                                   |
| `elapsed_time_seconds` | int              | Sim         | Duração >= 0                                     |
| `start_date`           | datetime (UTC)   | Sim         | Início da atividade                            |
| `activity_type`        | str              | Sim         | Ex.: `"Run"`, `"Ride"`, `"Swim"`               |
| `external_id`          | str \| None      | Não         | Reservado para ID Strava (nullable nesta spec) |

### `UserRepository`

```python
def get_by_id(user_id: UUID) -> User | None: ...
def save(user: User) -> User: ...
```

### `ActivityRepository`

```python
def get_all(user_id: UUID) -> list[Activity]: ...
def save(activity: Activity) -> Activity: ...
```

### API (mínima)

- `GET /health` → `200` `{ "status": "ok" }`
- Sem autenticação

### Efeitos colaterais

- `save` persiste no PostgreSQL (implementação SQL) ou em memória (testes unitários).

---

## Comportamentos

### Casos normais (Happy Path)

#### CN-1: Persistir novo usuário
**Dado** usuário inexistente  
**Quando** `UserRepository.save(user)` é chamado  
**Então** persiste e retorna o mesmo `User` com `id` preservado

#### CN-2: Listar activities de um usuário
**Dado** usuário existente com 2 activities  
**Quando** `ActivityRepository.get_all(user_id)`  
**Então** retorna lista com 2 itens

#### CN-3: Health check
**Dado** app iniciada  
**Quando** `GET /health`  
**Então** retorna 200 com `{ "status": "ok" }`

### Casos de borda (Edge Cases)

#### CB-1: Usuário sem activities
**Dado** usuário sem activities  
**Quando** `get_all(user_id)`  
**Então** retorna `[]` (não `None`)

#### CB-2: Activity com distância zero
**Dado** `Activity` com `distance_meters = 0`  
**Quando** `save`  
**Então** aceita (atividade válida, ex. warmup)

#### CB-3: Activity sem external_id
**Dado** `external_id = None`  
**Quando** `save`  
**Então** persiste normalmente

### Casos de erro

#### CE-1: Distância negativa
**Dado** `distance_meters < 0`  
**Quando** construir/salvar `Activity`  
**Então** rejeita com `DomainValidationError`

#### CE-2: Tempo negativo
**Dado** `elapsed_time_seconds < 0`  
**Quando** construir/salvar `Activity`  
**Então** rejeita com `DomainValidationError`

#### CE-3: user_id inexistente ao salvar Activity (SQL)
**Dado** `user_id` inexistente ao salvar `Activity` na implementação SQLAlchemy  
**Quando** `ActivityRepository.save(activity)`  
**Então** falha com `DomainIntegrityError` (violação de FK mapeada)

#### CE-4: Usuário desconhecido em get_by_id
**Dado** `user_id` desconhecido  
**Quando** `UserRepository.get_by_id`  
**Então** retorna `None` (sem exceção)

---

## Critérios de Aceite

- [x] Spec com status **Aprovada** em `specs/SPEC-001-backend-foundation.md`
- [x] Entidades `User` e `Activity` com validação de campos negativos
- [x] Interfaces de repositório implementadas em **in-memory** e **SQLAlchemy**
- [x] Migration Alembic cria tabelas `users` e `activities`
- [x] Um teste unitário por CN/CB/CE usando repositório in-memory
- [x] Um teste de integração com PostgreSQL cobrindo CN-2 + CE-3
- [x] Teste de contrato verificando assinaturas e tipos de retorno
- [x] `GET /health` coberto por teste de integração
- [x] Cobertura Domain >= 95%
- [x] CI executa pytest + ruff + mypy

---

## Decisões de Design

### Decisão: Validação negativa na entidade
**Contexto:** CE-1 e CE-2 exigem rejeição explícita de valores inválidos.  
**Opção escolhida:** Validação na entidade de domínio (`DomainValidationError`).  
**Alternativas rejeitadas:** `ValueError` puro (menos semântico para camada de domínio).  
**Motivo:** Alinhado ao princípio "falha explícita" do guia.

### Decisão: ORM sync
**Contexto:** POC precisa de simplicidade antes de otimizar concorrência.  
**Opção escolhida:** SQLAlchemy 2.x **sync**.  
**Alternativas rejeitadas:** async (complexidade desnecessária na v1).  
**Motivo:** Menor superfície de bugs e setup mais simples para integração pytest.

### Decisão: Estrutura de pastas
**Opção escolhida:** `backend/src/convertreino/{domain,infrastructure,api}`  
**Motivo:** Separação clara para specs futuras por camada.

### Decisão: Gerenciador de dependências
**Opção escolhida:** `uv` + `pyproject.toml`  
**Motivo:** Moderno e rápido para POC.

### Decisão: Docker Compose para PostgreSQL
**Opção escolhida:** `backend/docker-compose.yml` com serviço `postgres` na porta 5432.  
**Motivo:** Ambiente reproduzível para dev e testes de integração locais/CI.

### Decisão: Exceção de integridade
**Opção escolhida:** `DomainIntegrityError` para violações de FK na camada SQL.  
**Motivo:** CE-3 exige erro documentado sem vazar detalhes do ORM para o domínio.

### Decisão: get_all vazio
**Opção escolhida:** Retorna `[]`.  
**Motivo:** Consistente com exemplos do guia (PREngine).
