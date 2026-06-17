# SPEC-005 — PR Engine: corrida com maior distância

| Campo          | Valor                                              |
|----------------|----------------------------------------------------|
| **Status**     | Aprovada                                             |
| **Autor**      | @convertreino                                      |
| **Revisor**    | —                                                  |
| **Criada em**  | 2026-06-17                                         |
| **Camada**     | Domain                                             |
| **Depende de** | SPEC-001, SPEC-003                                 |
| **Bloqueia**   | MCP tools de PR, outras capacidades do PREngine    |
| **Épico**      | PR                                                 |

---

## Contexto

Com atividades Strava já persistidas no banco (SPEC-003), o usuário pode perguntar *"qual foi minha corrida mais longa?"* e espera uma resposta precisa e reproduzível. O ConverTreino delega cálculos analíticos a serviços determinísticos — o LLM não deve inferir distâncias nem escolher a atividade vencedora. Esta spec define o primeiro Domain Service do projeto: a regra de negócio para identificar a corrida (`Run`) com maior `distance_meters` de um usuário.

A SPEC-004 desbloqueia ingestão incremental de atividades, mas o PREngine **depende apenas de atividades já persistidas** — não requer Strava nem webhooks em runtime.

---

## Escopo

### Incluído

- Classe `PREngine` em `domain/services/pr_engine.py` (primeiro Domain Service do projeto)
- Método `get_longest_run(user_id: UUID) -> Activity | None`
- Filtro por `activity_type == "Run"` (literal Strava, consistente com SPEC-003)
- Desempate por `start_date` mais recente quando `distance_meters` é idêntico
- Testes unitários com `InMemoryActivityRepository` + `build_activity` existente
- Cobertura mínima Domain: 95% (guia seção 8)

### Excluído (explicitamente fora desta spec)

- Outros tipos (`Ride`, `Swim`) → spec futura por tipo (`get_longest_ride`, etc.)
- Filtro por período (semana/mês/ano) → spec futura
- PRs por pace, tempo ou distância alvo (5K, 10K, etc.)
- Endpoint REST e MCP tool `get_longest_run` → specs de camada API/MCP
- Extensão de `ActivityRepository` (query por tipo no banco) — POC usa `get_all` + filtro em memória
- Cache, workers, recálculo pós-webhook
- Auth JWT

---

## Contrato

### Assinatura

```python
class PREngine:
    def __init__(self, activity_repo: ActivityRepository) -> None: ...

    def get_longest_run(self, user_id: UUID) -> Activity | None: ...
```

**Decisão de nomenclatura:** usar `get_longest_run` (não `get_longest_activity`) porque o filtro por tipo é requisito de negócio e alinha com fronteiras de MCP futuras (`get_longest_run` vs `get_longest_ride`).

### Inputs

| Parâmetro  | Tipo   | Obrigatório | Descrição              |
|------------|--------|-------------|------------------------|
| `user_id`  | `UUID` | Sim         | ID interno do usuário  |

### Outputs

| Campo      | Tipo              | Descrição                                                        |
|------------|-------------------|------------------------------------------------------------------|
| `activity` | `Activity \| None`| Entidade `Activity` completa da corrida vencedora, ou `None`     |

### Regra de seleção

1. Buscar todas as atividades do usuário via `ActivityRepository.get_all(user_id)`
2. Considerar apenas atividades com `activity_type == "Run"` (match exato, case-sensitive)
3. Entre as corridas filtradas, escolher a de maior `distance_meters`
4. Em empate de `distance_meters`, escolher a atividade com `start_date` mais recente (determinístico)
5. Se a lista estiver vazia após o filtro → retornar `None` (sem exceção)

### Efeitos colaterais

Nenhum. Operação somente leitura via `ActivityRepository.get_all`.

---

## Comportamentos

### Casos normais (Happy Path)

#### CN-1: Usuário tem múltiplas corridas
**Dado** que o usuário tem 3 atividades do tipo `"Run"` com `distance_meters` de `5000`, `21097` e `10000`  
**Quando** `get_longest_run(user_id)` é chamado  
**Então** retorna a atividade com `distance_meters == 21097`

#### CN-2: Usuário tem apenas uma corrida
**Dado** que o usuário tem exatamente 1 atividade do tipo `"Run"` com `distance_meters = 8420`  
**Quando** `get_longest_run(user_id)` é chamado  
**Então** retorna essa atividade (com `distance_meters == 8420`)

### Casos de borda (Edge Cases)

#### CB-1: Usuário tem atividades mas nenhuma é corrida
**Dado** que o usuário tem atividades do tipo `"Ride"` e `"Swim"`, sem nenhuma `"Run"`  
**Quando** `get_longest_run(user_id)` é chamado  
**Então** retorna `None`

#### CB-2: Duas corridas com distância idêntica
**Dado** que o usuário tem 2 atividades do tipo `"Run"` com `distance_meters = 10000`, uma com `start_date = 2024-06-01T08:00:00+00:00` e outra com `start_date = 2024-09-15T07:30:00+00:00`  
**Quando** `get_longest_run(user_id)` é chamado  
**Então** retorna a corrida de `2024-09-15` (mais recente por `start_date`)

#### CB-3: Mix Run + Ride; Ride tem distância maior
**Dado** que o usuário tem uma corrida `"Run"` com `distance_meters = 10000` e um pedal `"Ride"` com `distance_meters = 85000`  
**Quando** `get_longest_run(user_id)` é chamado  
**Então** retorna a corrida com `distance_meters == 10000` (filtro por tipo, não distância global)

### Casos de erro

#### CE-1: Usuário sem atividades
**Dado** que o usuário não tem nenhuma atividade registrada (`get_all` retorna `[]`)  
**Quando** `get_longest_run(user_id)` é chamado  
**Então** retorna `None` (não lança exceção)

#### CE-2: user_id sem registros no repositório
**Dado** que `user_id` não possui nenhuma atividade no repositório (decisão SPEC-001: `get_all` → `[]`)  
**Quando** `get_longest_run(user_id)` é chamado  
**Então** retorna `None` (não lança exceção)

---

## Critérios de Aceite

- [ ] Spec com status **Aprovada** no repositório
- [ ] `PREngine` em `domain/services/` sem dependência de infra (apenas `ActivityRepository`)
- [ ] Um teste unitário por CN/CB/CE (7 testes de comportamento)
- [ ] Cobertura Domain >= 95% para `pr_engine.py`
- [ ] Nenhuma migration necessária
- [ ] CI verde (ruff, mypy, pytest)
- [ ] Comportamento determinístico em empates (`start_date` mais recente vence)

---

## Mapeamento Spec → Testes

| Artefato                                   | Localização                                          |
|--------------------------------------------|------------------------------------------------------|
| CN/CB/CE do `PREngine`                     | `backend/tests/unit/domain/test_pr_engine.py`        |
| Contrato (instanciação + tipo de retorno)  | Mesmo arquivo (`test_pr_engine.py`)                  |

Padrão AAA obrigatório (guia seção 6). Reutilizar `build_activity` de `backend/tests/builders/__init__.py` — sem novos builders. Testes de CB-2 devem usar `start_date` timezone-aware (consistente com `Activity.__post_init__`, que normaliza para UTC).

Exemplo derivado do guia:

```python
def test_get_longest_run_returns_activity_with_max_distance():
    # Arrange
    user_id = uuid4()
    activities = [
        build_activity(user_id=user_id, distance_meters=5000),
        build_activity(user_id=user_id, distance_meters=21097),
        build_activity(user_id=user_id, distance_meters=10000),
    ]
    engine = PREngine(InMemoryActivityRepository(activities))

    # Act
    result = engine.get_longest_run(user_id)

    # Assert
    assert result is not None
    assert result.distance_meters == 21097
```

---

## Decisões de Design

### Decisão: `get_all` + filtro em memória vs. query SQL por tipo
**Contexto:** Volume de atividades por usuário na POC é baixo; engines precisam filtrar por tipo.  
**Opção escolhida:** `get_all(user_id)` + filtro Python por `activity_type == "Run"`.  
**Alternativas rejeitadas:** `list_by_type(user_id, "Run")` no repositório.  
**Motivo:** POC; evita migration/query nova; SPEC-003 já entrega todas as atividades via sync.

### Decisão: `None` vs. exceção para ausência de dados
**Contexto:** Usuário novo ou sem corridas no histórico.  
**Opção escolhida:** Retornar `None`.  
**Alternativas rejeitadas:** `ActivityNotFoundError` ou exceção genérica.  
**Motivo:** Alinhado ao guia e à decisão SPEC-001 (`get_all` vazio retorna `[]`, não exceção).

### Decisão: Desempate por `start_date`
**Contexto:** Duas corridas com mesma distância máxima.  
**Opção escolhida:** Atividade com `start_date` mais recente vence.  
**Alternativas rejeitadas:** Primeira encontrada, menor `id`, ou escolha arbitrária.  
**Motivo:** PR "atual" é semanticamente a última conquista naquela distância; comportamento determinístico e testável.

### Decisão: Comparação literal `"Run"`
**Contexto:** `activity_type` vem do mapper Strava (SPEC-003) como string literal do Strava.  
**Opção escolhida:** Match exato `activity_type == "Run"`.  
**Alternativas rejeitadas:** Normalização case-insensitive ou enum interno nesta spec.  
**Motivo:** Consistência com dados importados; normalização pode ser spec futura se necessário.

---

## Notas de Migração

- Nenhuma migration
- Nenhuma variável de ambiente nova
- Rollback: remover `domain/services/pr_engine.py` e testes sem impacto em dados

---

## Roadmap pós-SPEC-005

| Spec futura provável | Conteúdo                                           |
|----------------------|----------------------------------------------------|
| SPEC-006+            | `get_longest_ride`, PR por pace, filtro temporal   |
| SPEC-0XX             | MCP tool `get_longest_run` com schema LLM          |
| SPEC-0XX             | Outros engines (Volume, Consistência, Tendência)   |

---

## Checklist de revisão (seção 12 do guia)

### Clareza
- [ ] O contexto explica o problema sem descrever a solução?
- [ ] O contrato tem tipos explícitos para todos os inputs e outputs?
- [ ] Cada comportamento tem "Dado / Quando / Então" completo?
- [ ] Os critérios de aceite são binários e verificáveis?

### Completude
- [ ] Há ao menos um caso normal (CN-1, CN-2)?
- [ ] Casos de borda cobertos (sem Run, empate, mix de tipos)?
- [ ] Casos de erro especificados com comportamento esperado (`None`, sem exceção)?
- [ ] Escopo "Excluído" deixa claro o que ficou de fora?

### Consistência
- [ ] Não contradiz SPEC-001 (`get_all` → `[]`) nem SPEC-003 (`activity_type` literal Strava)?
- [ ] Nomes de tipos alinhados ao código existente (`Activity`, `ActivityRepository`)?
- [ ] Domain não acessa banco diretamente; application layer não entra nesta spec?

### Testabilidade
- [ ] Cada comportamento mapeia para teste unitário com `InMemoryActivityRepository`?
- [ ] Comportamentos determinísticos (mesmo input → mesmo output)?
- [ ] Efeitos colaterais explicitados (nenhum) e testáveis?
