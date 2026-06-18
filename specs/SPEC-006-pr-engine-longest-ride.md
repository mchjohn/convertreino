# SPEC-006 — PR Engine: pedal com maior distância

| Campo          | Valor                                              |
|----------------|----------------------------------------------------|
| **Status**     | Aprovada                                           |
| **Autor**      | @convertreino                                      |
| **Revisor**    | —                                                  |
| **Criada em**  | 2026-06-17                                         |
| **Camada**     | Domain                                             |
| **Depende de** | SPEC-001, SPEC-003, SPEC-005                       |
| **Bloqueia**   | MCP tools de PR para Ride                          |
| **Épico**      | PR                                                 |

---

## Contexto

Com atividades Strava já persistidas no banco (SPEC-003), o usuário pode perguntar *"qual foi meu pedal mais longo?"* e espera uma resposta precisa e reproduzível. O ConverTreino delega cálculos analíticos a serviços determinísticos — o LLM não deve inferir distâncias nem escolher a atividade vencedora. A SPEC-005 definiu a regra para corridas (`Run`); esta spec estende o PREngine com a regra equivalente para pedais (`Ride`): identificar o pedal com maior `distance_meters` de um usuário.

O PREngine **depende apenas de atividades já persistidas** — não requer Strava nem webhooks em runtime.

---

## Escopo

### Incluído

- Método `get_longest_ride(user_id: UUID) -> Activity | None` na classe `PREngine` existente (`domain/services/pr_engine.py`)
- Filtro por `activity_type == "Ride"` (literal Strava, case-sensitive — consistente com SPEC-003 e SPEC-005)
- Desempate por `start_date` mais recente quando `distance_meters` é idêntico
- Testes unitários com `InMemoryActivityRepository` + `build_activity` existente
- Cobertura mínima Domain: 95% (guia seção 8)

### Excluído (explicitamente fora desta spec)

- Outros tipos (`Run`, `Swim`, `VirtualRide`, `EBikeRide`, etc.) → specs futuras por tipo ou agrupamento
- Filtro por período (semana/mês/ano) → spec futura
- PRs por pace, tempo ou distância alvo
- Endpoint REST e MCP tool `get_longest_ride` → specs de camada API/MCP (SPEC-008)
- Extensão de `ActivityRepository` (query por tipo no banco) — POC usa `get_all` + filtro em memória
- Refatoração compartilhada (`_get_longest_by_type`) — evitar scope creep; refatorar só se 3+ tipos forem adicionados
- Cache, workers, recálculo pós-webhook
- Auth JWT

---

## Contrato

### Assinatura

```python
class PREngine:
    def __init__(self, activity_repo: ActivityRepository) -> None: ...

    def get_longest_ride(self, user_id: UUID) -> Activity | None: ...
```

**Decisão de nomenclatura:** usar `get_longest_ride` (não `get_longest_activity`) porque o filtro por tipo é requisito de negócio e alinha com fronteiras de MCP futuras (`get_longest_run` vs `get_longest_ride`).

### Inputs

| Parâmetro  | Tipo   | Obrigatório | Descrição              |
|------------|--------|-------------|------------------------|
| `user_id`  | `UUID` | Sim         | ID interno do usuário  |

### Outputs

| Campo      | Tipo              | Descrição                                                        |
|------------|-------------------|------------------------------------------------------------------|
| `activity` | `Activity \| None`| Entidade `Activity` completa do pedal vencedor, ou `None`        |

### Regra de seleção

1. Buscar todas as atividades do usuário via `ActivityRepository.get_all(user_id)`
2. Considerar apenas atividades com `activity_type == "Ride"` (match exato, case-sensitive)
3. Entre os pedais filtrados, escolher o de maior `distance_meters`
4. Em empate de `distance_meters`, escolher a atividade com `start_date` mais recente (determinístico)
5. Se a lista estiver vazia após o filtro → retornar `None` (sem exceção)

### Efeitos colaterais

Nenhum. Operação somente leitura via `ActivityRepository.get_all`.

---

## Comportamentos

### Casos normais (Happy Path)

#### CN-1: Usuário tem múltiplos pedais
**Dado** que o usuário tem 3 atividades do tipo `"Ride"` com `distance_meters` de `30000`, `120000` e `80000`  
**Quando** `get_longest_ride(user_id)` é chamado  
**Então** retorna a atividade com `distance_meters == 120000`

#### CN-2: Usuário tem apenas um pedal
**Dado** que o usuário tem exatamente 1 atividade do tipo `"Ride"` com `distance_meters = 65000`  
**Quando** `get_longest_ride(user_id)` é chamado  
**Então** retorna essa atividade (com `distance_meters == 65000`)

### Casos de borda (Edge Cases)

#### CB-1: Usuário tem atividades mas nenhuma é pedal
**Dado** que o usuário tem atividades do tipo `"Run"` e `"Swim"`, sem nenhuma `"Ride"`  
**Quando** `get_longest_ride(user_id)` é chamado  
**Então** retorna `None`

#### CB-2: Dois pedais com distância idêntica
**Dado** que o usuário tem 2 atividades do tipo `"Ride"` com `distance_meters = 80000`, uma com `start_date = 2024-06-01T08:00:00+00:00` e outra com `start_date = 2024-09-15T07:30:00+00:00`  
**Quando** `get_longest_ride(user_id)` é chamado  
**Então** retorna o pedal de `2024-09-15` (mais recente por `start_date`)

#### CB-3: Mix Ride + Run; Run tem distância maior
**Dado** que o usuário tem um pedal `"Ride"` com `distance_meters = 50000` e uma corrida `"Run"` com `distance_meters = 42195`  
**Quando** `get_longest_ride(user_id)` é chamado  
**Então** retorna o pedal com `distance_meters == 50000` (filtro por tipo, não distância global)

### Casos de erro

#### CE-1: Usuário sem atividades
**Dado** que o usuário não tem nenhuma atividade registrada (`get_all` retorna `[]`)  
**Quando** `get_longest_ride(user_id)` é chamado  
**Então** retorna `None` (não lança exceção)

#### CE-2: user_id sem registros no repositório
**Dado** que `user_id` não possui nenhuma atividade no repositório (decisão SPEC-001: `get_all` → `[]`)  
**Quando** `get_longest_ride(user_id)` é chamado  
**Então** retorna `None` (não lança exceção)

---

## Critérios de Aceite

- [x] Spec com status **Aprovada** no repositório
- [x] `get_longest_ride` em `PREngine` sem dependência de infra (apenas `ActivityRepository`)
- [x] Um teste unitário por CN/CB/CE (7 testes de comportamento)
- [x] Cobertura Domain >= 95% para `pr_engine.py`
- [x] Nenhuma migration necessária
- [x] CI verde (ruff, mypy, pytest)
- [x] Comportamento determinístico em empates (`start_date` mais recente vence)
- [x] Filtra apenas `"Ride"` (literal Strava, case-sensitive)
- [x] Retorna `None` sem exceção quando não há pedais
- [x] Não contradiz SPEC-001, SPEC-003 nem SPEC-005

---

## Mapeamento Spec → Testes

| Artefato                                   | Localização                                          |
|--------------------------------------------|------------------------------------------------------|
| CN/CB/CE do `get_longest_ride`             | `backend/tests/unit/domain/test_pr_engine.py`        |
| Contrato (tipo de retorno)                 | Mesmo arquivo (`test_pr_engine.py`)                  |

Padrão AAA obrigatório (guia seção 6). Reutilizar `build_activity` de `backend/tests/builders/__init__.py` — sem novos builders. Testes de CB-2 devem usar `start_date` timezone-aware (consistente com `Activity.__post_init__`, que normaliza para UTC). Testes de Ride devem passar `activity_type="Ride"` explicitamente quando o default de `build_activity` for `"Run"`.

Exemplo derivado do guia:

```python
def test_get_longest_ride_returns_activity_with_max_distance():
    # Arrange
    user_id = uuid4()
    activities = [
        build_activity(user_id=user_id, activity_type="Ride", distance_meters=30000),
        build_activity(user_id=user_id, activity_type="Ride", distance_meters=120000),
        build_activity(user_id=user_id, activity_type="Ride", distance_meters=80000),
    ]
    engine = PREngine(InMemoryActivityRepository(activities))

    # Act
    result = engine.get_longest_ride(user_id)

    # Assert
    assert result is not None
    assert result.distance_meters == 120000
```

---

## Decisões de Design

### Decisão: Simetria com SPEC-005 (`get_all` + filtro em memória)
**Contexto:** SPEC-005 estabeleceu `get_longest_run` com `get_all` + filtro Python por tipo.  
**Opção escolhida:** Mesma estratégia para `get_longest_ride`.  
**Alternativas rejeitadas:** Query SQL por tipo no repositório; helper compartilhado `_get_longest_by_type`.  
**Motivo:** POC; volume baixo por usuário; diff mínimo; refatorar helper só se SPEC-007+ adicionar 3º tipo.

### Decisão: Comparação literal `"Ride"`
**Contexto:** `activity_type` vem do mapper Strava (SPEC-003) como string literal do Strava. Strava distingue `Ride`, `VirtualRide`, `EBikeRide`, etc.  
**Opção escolhida:** Match exato `activity_type == "Ride"`.  
**Alternativas rejeitadas:** Agrupar `VirtualRide` e `EBikeRide` com `Ride`; normalização case-insensitive.  
**Motivo:** Consistência com SPEC-005 e dados importados; agrupamento de subtipos pode ser spec futura se necessário.

### Decisão: `None` vs. exceção para ausência de dados
**Contexto:** Usuário novo ou sem pedais no histórico.  
**Opção escolhida:** Retornar `None`.  
**Alternativas rejeitadas:** `ActivityNotFoundError` ou exceção genérica.  
**Motivo:** Alinhado ao guia, à SPEC-005 e à decisão SPEC-001 (`get_all` vazio retorna `[]`, não exceção).

### Decisão: Desempate por `start_date`
**Contexto:** Dois pedais com mesma distância máxima.  
**Opção escolhida:** Atividade com `start_date` mais recente vence.  
**Alternativas rejeitadas:** Primeira encontrada, menor `id`, ou escolha arbitrária.  
**Motivo:** Simetria com SPEC-005; PR "atual" é semanticamente a última conquista naquela distância; comportamento determinístico e testável.

### Decisão: Sem refactor compartilhado nesta spec
**Contexto:** `get_longest_run` e `get_longest_ride` terão lógica quase idêntica.  
**Opção escolhida:** Duplicar o padrão de 5 linhas em `get_longest_ride` sem extrair helper.  
**Alternativas rejeitadas:** `_get_longest_by_type(user_id, activity_type)` genérico.  
**Motivo:** Evitar scope creep; DRY prematuro com apenas 2 métodos; refatorar quando houver 3+ tipos ou filtro temporal cross-cutting.

---

## Notas de Migração

- Nenhuma migration
- Nenhuma variável de ambiente nova
- Rollback: remover `get_longest_ride` de `pr_engine.py` e testes associados sem impacto em dados

---

## Roadmap pós-SPEC-006

| Spec futura provável | Conteúdo                                                    |
|----------------------|-------------------------------------------------------------|
| SPEC-007             | MCP server scaffold + tool `get_longest_run`                |
| SPEC-008             | MCP tool `get_longest_ride` (padrão estabelecido na 007)    |
| SPEC-009             | Filtro temporal nos engines PR (SPEC-005/006)               |
| SPEC-010+            | Volume Engine (`get_weekly_volume`), outros engines         |

---

## Checklist de revisão (seção 12 do guia)

### Clareza
- [x] O contexto explica o problema sem descrever a solução?
- [x] O contrato tem tipos explícitos para todos os inputs e outputs?
- [x] Cada comportamento tem "Dado / Quando / Então" completo?
- [x] Os critérios de aceite são binários e verificáveis?

### Completude
- [x] Há ao menos um caso normal (CN-1, CN-2)?
- [x] Casos de borda cobertos (sem Ride, empate, mix de tipos)?
- [x] Casos de erro especificados com comportamento esperado (`None`, sem exceção)?
- [x] Escopo "Excluído" deixa claro o que ficou de fora?

### Consistência
- [x] Não contradiz SPEC-001 (`get_all` → `[]`), SPEC-003 (`activity_type` literal Strava) nem SPEC-005?
- [x] Nomes de tipos alinhados ao código existente (`Activity`, `ActivityRepository`, `PREngine`)?
- [x] Domain não acessa banco diretamente; application layer não entra nesta spec?

### Testabilidade
- [x] Cada comportamento mapeia para teste unitário com `InMemoryActivityRepository`?
- [x] Comportamentos determinísticos (mesmo input → mesmo output)?
- [x] Efeitos colaterais explicitados (nenhum) e testáveis?
