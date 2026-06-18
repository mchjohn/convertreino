# SPEC-009 — PR Engine: filtro temporal

| Campo          | Valor                                              |
|----------------|----------------------------------------------------|
| **Status**     | Draft                                              |
| **Autor**      | @convertreino                                      |
| **Revisor**    | —                                                  |
| **Criada em**  | 2026-06-18                                         |
| **Camada**     | Domain                                             |
| **Depende de** | SPEC-001, SPEC-003, SPEC-005, SPEC-006             |
| **Bloqueia**   | MCP temporal (SPEC-010), API de chat com perguntas por período |
| **Épico**      | PR                                                 |

---

## Contexto

Com `get_longest_run` e `get_longest_ride` já definidos (SPEC-005/006), o usuário pode perguntar não só *"qual foi minha corrida/pedal mais longo?"* (histórico completo), mas também *"em 2024?"*, *"neste mês?"* ou *"entre março e junho?"*. Sem filtro temporal, o PREngine sempre considera todo o histórico — resposta incorreta para essas intenções. O ConverTreino delega cálculos analíticos a serviços determinísticos; o LLM não deve inferir o recorte temporal nem escolher quais atividades entram no cálculo.

O PREngine **depende apenas de atividades já persistidas** — não requer Strava nem webhooks em runtime.

---

## Escopo

### Incluído

- Parâmetros opcionais `start_date: datetime | None = None` e `end_date: datetime | None = None` (keyword-only) em:
  - `PREngine.get_longest_run(user_id, *, start_date=None, end_date=None)`
  - `PREngine.get_longest_ride(user_id, *, start_date=None, end_date=None)`
- Filtro temporal **após** filtro por tipo (`"Run"` / `"Ride"`), **antes** da seleção por `max(distance_meters, start_date)`
- Refatoração para helper privado `_get_longest_by_type(user_id, activity_type, start_date?, end_date?)` — gatilho previsto na SPEC-006 (*"refatorar quando houver filtro temporal cross-cutting"*)
- Normalização de `start_date`/`end_date` naive → UTC antes da comparação (consistente com `Activity.__post_init__`)
- Testes unitários com `InMemoryActivityRepository` + `build_activity` existente
- Cobertura mínima Domain: 95% (guia seção 8)

### Excluído (explicitamente fora desta spec)

- Atualização das MCP tools (`get_longest_run` / `get_longest_ride`) → SPEC-010
- Períodos nomeados (semana/mês/ano, "essa semana", "ano passado") → resolvidos na SPEC-010 (MCP) ou Volume Engine
- Query SQL por intervalo no repositório — POC usa `get_all` + filtro em memória
- Novos métodos separados (`get_longest_run_in_period`) — estender assinatura existente preserva compatibilidade
- Outros tipos de atividade (`Swim`, `VirtualRide`, `EBikeRide`, etc.)
- Endpoint REST, auth JWT, cache, workers
- PRs por pace, tempo ou distância alvo

---

## Contrato

### Assinatura

```python
class PREngine:
    def __init__(self, activity_repo: ActivityRepository) -> None: ...

    def get_longest_run(
        self,
        user_id: UUID,
        *,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
    ) -> Activity | None: ...

    def get_longest_ride(
        self,
        user_id: UUID,
        *,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
    ) -> Activity | None: ...

    def _get_longest_by_type(
        self,
        user_id: UUID,
        activity_type: str,
        *,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
    ) -> Activity | None: ...
```

**Decisão de nomenclatura:** manter `get_longest_run` / `get_longest_ride` (não criar métodos novos) porque o filtro temporal é opcional e retrocompatível — chamadas existentes `get_longest_run(user_id)` permanecem válidas.

### Inputs

| Parâmetro     | Tipo                | Obrigatório | Descrição                                                                 |
|---------------|---------------------|-------------|---------------------------------------------------------------------------|
| `user_id`     | `UUID`              | Sim         | ID interno do usuário                                                     |
| `start_date`  | `datetime \| None`  | Não         | Limite inferior inclusivo; `None` = sem limite inferior                   |
| `end_date`    | `datetime \| None`  | Não         | Limite superior inclusivo; `None` = sem limite superior                   |

Ambos `start_date` e `end_date` comparam contra `activity.start_date` (momento de início da atividade Strava). Valores naive são normalizados para UTC antes da comparação.

### Outputs

| Campo      | Tipo              | Descrição                                                        |
|------------|-------------------|------------------------------------------------------------------|
| `activity` | `Activity \| None`| Entidade `Activity` completa da atividade vencedora, ou `None`   |

### Regra de seleção

1. Se `start_date` e `end_date` informados e `start_date > end_date` → retornar `None` (sem exceção)
2. Normalizar `start_date`/`end_date` naive para UTC (se informados)
3. Buscar todas as atividades do usuário via `ActivityRepository.get_all(user_id)`
4. Considerar apenas atividades com `activity_type` correspondente (`"Run"` ou `"Ride"`, match exato, case-sensitive)
5. Se `start_date` informado: manter atividades com `activity.start_date >= start_date` (**inclusivo**)
6. Se `end_date` informado: manter atividades com `activity.start_date <= end_date` (**inclusivo**)
7. Entre as atividades filtradas, escolher a de maior `distance_meters`
8. Em empate de `distance_meters`, escolher a atividade com `start_date` mais recente (determinístico)
9. Se a lista estiver vazia após os filtros → retornar `None` (sem exceção)

**Retrocompatibilidade:** quando `start_date` e `end_date` são ambos `None`, o comportamento é idêntico à SPEC-005/006.

### Efeitos colaterais

Nenhum. Operação somente leitura via `ActivityRepository.get_all`.

---

## Comportamentos

Os casos abaixo aplicam-se simetricamente a `get_longest_run` e `get_longest_ride`. Nos exemplos, `"Run"` e `"Ride"` são intercambiáveis conforme o método testado.

### Casos normais (Happy Path)

#### CN-1: Intervalo contém múltiplas atividades; vencedora está dentro do intervalo
**Dado** que o usuário tem 3 atividades do tipo `"Run"`:  
- `start_date = 2023-01-01T08:00:00+00:00`, `distance_meters = 42000`  
- `start_date = 2024-03-01T08:00:00+00:00`, `distance_meters = 15000`  
- `start_date = 2024-08-01T08:00:00+00:00`, `distance_meters = 25000`  
**Quando** `get_longest_run(user_id, start_date=2024-01-01T00:00:00+00:00, end_date=2024-12-31T23:59:59+00:00)` é chamado  
**Então** retorna a atividade de `2024-08-01` com `distance_meters == 25000` (a de `42000` em 2023 fica fora do intervalo)

#### CN-2: Sem filtro temporal — comportamento inalterado (SPEC-005/006)
**Dado** que o usuário tem 3 atividades do tipo `"Run"` com `distance_meters` de `5000`, `21097` e `10000`  
**Quando** `get_longest_run(user_id)` é chamado (sem `start_date` nem `end_date`)  
**Então** retorna a atividade com `distance_meters == 21097`

#### CN-3: Apenas `start_date` — sem limite superior
**Dado** que o usuário tem 2 atividades do tipo `"Run"`:  
- `start_date = 2023-06-01T08:00:00+00:00`, `distance_meters = 30000`  
- `start_date = 2024-06-01T08:00:00+00:00`, `distance_meters = 10000`  
**Quando** `get_longest_run(user_id, start_date=2024-01-01T00:00:00+00:00)` é chamado  
**Então** retorna a atividade de `2024-06-01` com `distance_meters == 10000`

#### CN-4: Apenas `end_date` — sem limite inferior
**Dado** que o usuário tem 2 atividades do tipo `"Ride"`:  
- `start_date = 2023-06-01T08:00:00+00:00`, `distance_meters = 80000`  
- `start_date = 2024-06-01T08:00:00+00:00`, `distance_meters = 120000`  
**Quando** `get_longest_ride(user_id, end_date=2023-12-31T23:59:59+00:00)` é chamado  
**Então** retorna a atividade de `2023-06-01` com `distance_meters == 80000`

### Casos de borda (Edge Cases)

#### CB-1: Atividade exatamente na fronteira do intervalo
**Dado** que o usuário tem 1 atividade do tipo `"Run"` com `start_date = 2024-06-01T08:00:00+00:00` e `distance_meters = 10000`  
**Quando** `get_longest_run(user_id, start_date=2024-06-01T08:00:00+00:00, end_date=2024-06-01T08:00:00+00:00)` é chamado  
**Então** retorna essa atividade (fronteiras inclusivas)

#### CB-2: Atividades no intervalo mas nenhuma do tipo correto
**Dado** que o usuário tem atividades do tipo `"Ride"` dentro do intervalo, mas nenhuma `"Run"`  
**Quando** `get_longest_run(user_id, start_date=2024-01-01T00:00:00+00:00, end_date=2024-12-31T23:59:59+00:00)` é chamado  
**Então** retorna `None`

#### CB-3: Empate de distância dentro do intervalo
**Dado** que o usuário tem 2 atividades do tipo `"Run"` com `distance_meters = 10000`, ambas dentro do intervalo, uma com `start_date = 2024-06-01T08:00:00+00:00` e outra com `start_date = 2024-09-15T07:30:00+00:00`  
**Quando** `get_longest_run(user_id, start_date=2024-01-01T00:00:00+00:00, end_date=2024-12-31T23:59:59+00:00)` é chamado  
**Então** retorna a corrida de `2024-09-15` (mais recente por `start_date`)

#### CB-4: Mix Run + Ride no intervalo; filtro por tipo isola corretamente
**Dado** que o usuário tem um pedal `"Ride"` com `distance_meters = 85000` e uma corrida `"Run"` com `distance_meters = 10000`, ambos dentro do intervalo  
**Quando** `get_longest_run(user_id, start_date=2024-01-01T00:00:00+00:00, end_date=2024-12-31T23:59:59+00:00)` é chamado  
**Então** retorna a corrida com `distance_meters == 10000` (filtro por tipo, não distância global)

### Casos de erro

#### CE-1: Nenhuma atividade no intervalo
**Dado** que o usuário tem atividades do tipo `"Run"`, mas todas com `start_date` anterior a `2024-01-01`  
**Quando** `get_longest_run(user_id, start_date=2024-01-01T00:00:00+00:00, end_date=2024-12-31T23:59:59+00:00)` é chamado  
**Então** retorna `None` (não lança exceção)

#### CE-2: Intervalo inválido (`start_date > end_date`)
**Dado** que o usuário tem atividades do tipo `"Run"` no histórico  
**Quando** `get_longest_run(user_id, start_date=2024-12-31T00:00:00+00:00, end_date=2024-01-01T00:00:00+00:00)` é chamado  
**Então** retorna `None` (não lança exceção)

#### CE-3: Usuário sem atividades
**Dado** que o usuário não tem nenhuma atividade registrada (`get_all` retorna `[]`)  
**Quando** `get_longest_ride(user_id, start_date=2024-01-01T00:00:00+00:00)` é chamado  
**Então** retorna `None` (não lança exceção)

---

## Critérios de Aceite

- [ ] Spec com status **Draft** no repositório
- [ ] Assinaturas estendidas sem quebrar chamadas existentes (`get_longest_run(user_id)`)
- [ ] Helper `_get_longest_by_type` com filtro temporal compartilhado entre Run e Ride
- [ ] Um teste unitário por CN/CB/CE documentado (11 testes de comportamento; subset crítico espelhado ou parametrizado para Ride)
- [ ] Testes existentes de SPEC-005/006 permanecem verdes sem alteração de asserções
- [ ] Cobertura Domain >= 95% para `pr_engine.py`
- [ ] Nenhuma migration necessária
- [ ] CI verde (ruff, mypy, pytest)
- [ ] Comportamento determinístico em empates (`start_date` mais recente vence)
- [ ] Fronteiras de intervalo inclusivas (`>= start_date`, `<= end_date`)
- [ ] Retorna `None` sem exceção para intervalo vazio, inválido ou ausência de atividades
- [ ] Não contradiz SPEC-001, SPEC-003, SPEC-005 nem SPEC-006

---

## Mapeamento Spec → Testes

| Artefato                                   | Localização                                          |
|--------------------------------------------|------------------------------------------------------|
| CN/CB/CE do filtro temporal (`Run`)        | `backend/tests/unit/domain/test_pr_engine.py`        |
| Subset crítico espelhado (`Ride`)          | Mesmo arquivo (`test_pr_engine.py`)                  |
| Contrato (retrocompatibilidade)            | Mesmo arquivo — testes SPEC-005/006 existentes       |

Padrão AAA obrigatório (guia seção 6). Reutilizar `build_activity` de `backend/tests/builders/__init__.py` — sem novos builders. Testes temporais devem usar `start_date` timezone-aware (consistente com `Activity.__post_init__`). Testes de Ride devem passar `activity_type="Ride"` explicitamente.

Exemplo derivado do guia:

```python
def test_get_longest_run_returns_max_distance_within_date_range():
    # Arrange
    user_id = uuid4()
    activities = [
        build_activity(
            user_id=user_id,
            distance_meters=42000,
            start_date=datetime(2023, 1, 1, 8, 0, 0, tzinfo=UTC),
        ),
        build_activity(
            user_id=user_id,
            distance_meters=15000,
            start_date=datetime(2024, 3, 1, 8, 0, 0, tzinfo=UTC),
        ),
        build_activity(
            user_id=user_id,
            distance_meters=25000,
            start_date=datetime(2024, 8, 1, 8, 0, 0, tzinfo=UTC),
        ),
    ]
    engine = PREngine(InMemoryActivityRepository(activities))

    # Act
    result = engine.get_longest_run(
        user_id,
        start_date=datetime(2024, 1, 1, 0, 0, 0, tzinfo=UTC),
        end_date=datetime(2024, 12, 31, 23, 59, 59, tzinfo=UTC),
    )

    # Assert
    assert result is not None
    assert result.distance_meters == 25000
    assert result.start_date == datetime(2024, 8, 1, 8, 0, 0, tzinfo=UTC)
```

---

## Decisões de Design

### Decisão: Intervalo livre (`start_date` / `end_date`) no Domain
**Contexto:** Usuários perguntam por histórico completo, ano calendário, mês ou intervalo customizado.  
**Opção escolhida:** Parâmetros opcionais `start_date` e `end_date` no PREngine.  
**Alternativas rejeitadas:** Períodos nomeados (semana/mês/ano) no Domain; métodos separados por período.  
**Motivo:** Primitivo reutilizável; semana/mês/ano exigem calendário/fuso e serão resolvidos na SPEC-010 (MCP/Application).

### Decisão: Fronteiras inclusivas
**Contexto:** Atividade iniciada exatamente em `start_date` ou `end_date` deve contar?  
**Opção escolhida:** `activity.start_date >= start_date` e `activity.start_date <= end_date`.  
**Alternativas rejeitadas:** Intervalo semi-aberto `[start, end)`.  
**Motivo:** Intuitivo para perguntas como "em junho de 2024"; atividade no primeiro/último dia do mês entra no recorte.

### Decisão: Keyword-only params
**Contexto:** Assinatura evolui de `(user_id)` para `(user_id, start_date?, end_date?)`.  
**Opção escolhida:** `*, start_date=None, end_date=None` após `user_id`.  
**Alternativas rejeitadas:** Parâmetros posicionais opcionais.  
**Motivo:** Evita quebra silenciosa se novos parâmetros posicionais forem adicionados no futuro.

### Decisão: Helper `_get_longest_by_type`
**Contexto:** SPEC-006 adiou refactor até filtro temporal cross-cutting; SPEC-005/006 duplicam lógica idêntica.  
**Opção escolhida:** Extrair `_get_longest_by_type(user_id, activity_type, *, start_date?, end_date?)`; `get_longest_run` e `get_longest_ride` delegam ao helper.  
**Alternativas rejeitadas:** Duplicar filtro temporal em ambos os métodos.  
**Motivo:** Filtro temporal é cross-cutting; DRY justificado com 2 tipos + lógica temporal compartilhada.

### Decisão: `None` para intervalo inválido
**Contexto:** `start_date > end_date` é input incoerente.  
**Opção escolhida:** Retornar `None` (sem exceção).  
**Alternativas rejeitadas:** `ValueError` ou `DomainValidationError`.  
**Motivo:** Alinhado ao padrão "ausência de dados = None" das specs 005/006; na POC, MCP tratará validação de input na SPEC-010.

### Decisão: Normalização naive → UTC
**Contexto:** `Activity.__post_init__` normaliza `start_date` naive para UTC; parâmetros do engine devem ser consistentes.  
**Opção escolhida:** Normalizar `start_date`/`end_date` naive para UTC antes de comparar com `activity.start_date`.  
**Alternativas rejeitadas:** Exigir timezone-aware nos parâmetros (rejeitar naive).  
**Motivo:** Consistência com entidade `Activity`; testes usam UTC explícito como boa prática.

### Decisão: `get_all` + filtro em memória (mantido)
**Contexto:** Volume baixo por usuário na POC; filtro temporal adiciona mais um passo em memória.  
**Opção escolhida:** Manter `get_all(user_id)` + filtros Python (tipo + intervalo).  
**Alternativas rejeitadas:** Query SQL por intervalo no repositório.  
**Motivo:** Consistência com SPEC-005/006; evitar migration/query nova.

---

## Notas de Migração

- Nenhuma migration
- Nenhuma variável de ambiente nova
- Retrocompatível: chamadas existentes sem `start_date`/`end_date` mantêm comportamento SPEC-005/006
- Rollback: reverter assinaturas e helper em `pr_engine.py` e remover testes temporais — sem impacto em dados

---

## Roadmap pós-SPEC-009

| Spec futura provável | Conteúdo                                                    |
|----------------------|-------------------------------------------------------------|
| SPEC-010             | MCP: `start_date`/`end_date` opcionais + descrições LLM para "em 2024", "este mês", etc. |
| SPEC-011+            | Volume Engine, API de chat, auth JWT                        |

---

## Checklist de revisão (seção 12 do guia)

### Clareza
- [ ] O contexto explica o problema sem descrever a solução?
- [ ] O contrato tem tipos explícitos para todos os inputs e outputs?
- [ ] Cada comportamento tem "Dado / Quando / Então" completo?
- [ ] Os critérios de aceite são binários e verificáveis?

### Completude
- [ ] Há ao menos um caso normal (CN-1 a CN-4)?
- [ ] Casos de borda cobertos (fronteira inclusiva, tipo errado, empate, mix de tipos)?
- [ ] Casos de erro especificados com comportamento esperado (`None`, sem exceção)?
- [ ] Escopo "Excluído" deixa claro o que ficou de fora?

### Consistência
- [ ] Não contradiz SPEC-001 (`get_all` → `[]`), SPEC-003 (`activity_type` literal Strava), SPEC-005 nem SPEC-006?
- [ ] Nomes de tipos alinhados ao código existente (`Activity`, `ActivityRepository`, `PREngine`)?
- [ ] Domain não acessa banco diretamente; MCP não entra nesta spec?

### Testabilidade
- [ ] Cada comportamento mapeia para teste unitário com `InMemoryActivityRepository`?
- [ ] Comportamentos determinísticos (mesmo input → mesmo output)?
- [ ] Efeitos colaterais explicitados (nenhum) e testáveis?
