# SPEC-011 — Volume Engine: distância acumulada por tipo

| Campo          | Valor                                              |
|----------------|----------------------------------------------------|
| **Status**     | Draft                                              |
| **Autor**      | @convertreino                                      |
| **Revisor**    | —                                                  |
| **Criada em**  | 2026-06-18                                         |
| **Camada**     | Domain                                             |
| **Depende de** | SPEC-001, SPEC-003                                 |
| **Bloqueia**   | SPEC-012 (MCP tools de volume), API de chat com perguntas de volume |
| **Épico**      | Volume                                             |

---

## Contexto

Com atividades Strava já persistidas no banco (SPEC-003), o usuário pode perguntar *"quanto corri essa semana?"*, *"quantos km em 2024?"* ou *"qual meu volume total de pedal?"* — respostas que exigem **soma** de distâncias, não seleção de um recorde (PREngine, SPEC-005/006). Sem um serviço determinístico, o LLM poderia somar distâncias manualmente e errar silenciosamente.

O ConverTreino delega cálculos analíticos a serviços determinísticos; o LLM **não** deve inferir quais atividades entram no cálculo nem executar a agregação. A SPEC-010 já referencia perguntas de volume agregado como responsabilidade futura do Volume Engine — esta spec define a regra de negócio no Domain.

O VolumeEngine **depende apenas de atividades já persistidas** — não requer Strava nem webhooks em runtime.

---

## Escopo

### Incluído

- Nova classe `VolumeEngine` em `domain/services/volume_engine.py`
- Value object `VolumeResult` (dataclass frozen, no mesmo arquivo) com:
  - `total_distance_meters: float`
  - `activities_count: int`
- Métodos com parâmetros opcionais keyword-only (simétricos ao filtro temporal da SPEC-009):
  - `VolumeEngine.get_run_volume(user_id, *, start_date=None, end_date=None) -> VolumeResult`
  - `VolumeEngine.get_ride_volume(user_id, *, start_date=None, end_date=None) -> VolumeResult`
- Helper privado `_get_volume_by_type(user_id, activity_type, start_date?, end_date?)`
- Filtro temporal **idêntico** ao PREngine: fronteiras inclusivas, normalização naive→UTC, comparação contra `activity.start_date`
- Testes unitários com `InMemoryActivityRepository` + `build_activity` existente
- Export em `domain/services/__init__.py`
- Cobertura mínima Domain: 95% (guia seção 8)

### Excluído (explicitamente fora desta spec)

- MCP tools (`get_run_volume`, `get_ride_volume`, `get_weekly_volume`, etc.) → SPEC-012
- Utilitário server-side de períodos nomeados (`period_resolver.py`) — LLM converte "esta semana" em ISO 8601 na camada MCP (padrão SPEC-010)
- Volume combinado Run+Ride ("quanto treinei no total?")
- Outros tipos de atividade (`Swim`, `VirtualRide`, `EBikeRide`, etc.)
- Pace, tempo ou elevação agregados
- Query SQL por intervalo no repositório — POC usa `get_all` + filtro em memória
- Endpoint REST, auth JWT, cache, workers
- Refatoração do PREngine para extrair filtro temporal compartilhado entre engines
- Application Service intermediário (`VolumeQueryService`)

---

## Contrato

### Assinatura

```python
@dataclass(frozen=True, slots=True)
class VolumeResult:
    total_distance_meters: float
    activities_count: int

class VolumeEngine:
    def __init__(self, activity_repo: ActivityRepository) -> None: ...

    def get_run_volume(
        self,
        user_id: UUID,
        *,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
    ) -> VolumeResult: ...

    def get_ride_volume(
        self,
        user_id: UUID,
        *,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
    ) -> VolumeResult: ...

    def _get_volume_by_type(
        self,
        user_id: UUID,
        activity_type: str,
        *,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
    ) -> VolumeResult: ...
```

**Decisão de nomenclatura:** usar `get_run_volume` / `get_ride_volume` (não `get_volume` genérico) porque o filtro por tipo é requisito de negócio e alinha com fronteiras de MCP futuras, consistente com `get_longest_run` / `get_longest_ride`.

### Inputs

| Parâmetro     | Tipo                | Obrigatório | Descrição                                                                 |
|---------------|---------------------|-------------|---------------------------------------------------------------------------|
| `user_id`     | `UUID`              | Sim         | ID interno do usuário                                                     |
| `start_date`  | `datetime \| None`  | Não         | Limite inferior inclusivo; `None` = sem limite inferior                   |
| `end_date`    | `datetime \| None`  | Não         | Limite superior inclusivo; `None` = sem limite superior                   |

Ambos `start_date` e `end_date` comparam contra `activity.start_date` (momento de início da atividade Strava). Valores naive são normalizados para UTC antes da comparação.

### Outputs

| Campo                    | Tipo     | Descrição                                                                 |
|--------------------------|----------|---------------------------------------------------------------------------|
| `total_distance_meters`  | `float`  | Soma de `distance_meters` das atividades filtradas                        |
| `activities_count`       | `int`    | Quantidade de atividades incluídas na soma (inclui `distance_meters == 0`)|

**Diferença semântica vs PREngine:** o VolumeEngine **nunca** retorna `None`. Ausência de dados ou recorte vazio produz `VolumeResult(total_distance_meters=0, activities_count=0)`.

| Situação                         | PREngine   | VolumeEngine              |
|----------------------------------|------------|---------------------------|
| Nenhuma atividade no recorte     | `None`     | `VolumeResult(0, 0)`      |
| Intervalo inválido               | `None`     | `VolumeResult(0, 0)`      |
| Usuário sem atividades           | `None`     | `VolumeResult(0, 0)`      |

Motivo: zero km é resposta válida para volume (guia seção 11, exemplo `get_weekly_volume` CE-1).

### Regra de agregação

1. Se `start_date` e `end_date` informados e `start_date > end_date` → retornar `VolumeResult(0, 0)` (sem exceção)
2. Normalizar `start_date`/`end_date` naive para UTC (se informados)
3. Buscar todas as atividades do usuário via `ActivityRepository.get_all(user_id)`
4. Considerar apenas atividades com `activity_type` correspondente (`"Run"` ou `"Ride"`, match exato, case-sensitive)
5. Se `start_date` informado: manter atividades com `activity.start_date >= start_date` (**inclusivo**)
6. Se `end_date` informado: manter atividades com `activity.start_date <= end_date` (**inclusivo**)
7. `total_distance_meters = sum(a.distance_meters for a in filtered)`
8. `activities_count = len(filtered)`
9. Se a lista estiver vazia após os filtros → retornar `VolumeResult(0, 0)` (sem exceção)

**Sem filtro temporal:** quando `start_date` e `end_date` são ambos `None`, soma o histórico completo do tipo.

### Precisão numérica

- Domain soma metros brutos (`float`) — **sem arredondamento**
- Conversão para km e arredondamento ficam na camada MCP (SPEC-012), como pace e velocidade já ficam em `mcp/mappers.py`

### Efeitos colaterais

Nenhum. Operação somente leitura via `ActivityRepository.get_all`.

---

## Comportamentos

Os casos abaixo aplicam-se simetricamente a `get_run_volume` e `get_ride_volume`. Nos exemplos, `"Run"` e `"Ride"` são intercambiáveis conforme o método testado.

### Casos normais (Happy Path)

#### CN-1: Intervalo contém múltiplas atividades — soma correta
**Dado** que o usuário tem 3 atividades do tipo `"Run"`:  
- `start_date = 2023-01-01T08:00:00+00:00`, `distance_meters = 42000`  
- `start_date = 2024-03-01T08:00:00+00:00`, `distance_meters = 5000`  
- `start_date = 2024-06-01T08:00:00+00:00`, `distance_meters = 10000`  
**Quando** `get_run_volume(user_id, start_date=2024-01-01T00:00:00+00:00, end_date=2024-12-31T23:59:59+00:00)` é chamado  
**Então** retorna `VolumeResult(total_distance_meters=15000, activities_count=2)` (a de `42000` em 2023 fica fora do intervalo)

#### CN-2: Sem filtro temporal — histórico completo
**Dado** que o usuário tem 3 atividades do tipo `"Run"` com `distance_meters` de `5000`, `21097` e `10000`  
**Quando** `get_run_volume(user_id)` é chamado (sem `start_date` nem `end_date`)  
**Então** retorna `VolumeResult(total_distance_meters=36097, activities_count=3)`

#### CN-3: Apenas `start_date` — sem limite superior
**Dado** que o usuário tem 2 atividades do tipo `"Run"`:  
- `start_date = 2023-06-01T08:00:00+00:00`, `distance_meters = 30000`  
- `start_date = 2024-06-01T08:00:00+00:00`, `distance_meters = 10000`  
**Quando** `get_run_volume(user_id, start_date=2024-01-01T00:00:00+00:00)` é chamado  
**Então** retorna `VolumeResult(total_distance_meters=10000, activities_count=1)`

#### CN-4: Apenas `end_date` — sem limite inferior
**Dado** que o usuário tem 2 atividades do tipo `"Ride"`:  
- `start_date = 2023-06-01T08:00:00+00:00`, `distance_meters = 80000`  
- `start_date = 2024-06-01T08:00:00+00:00`, `distance_meters = 120000`  
**Quando** `get_ride_volume(user_id, end_date=2023-12-31T23:59:59+00:00)` é chamado  
**Então** retorna `VolumeResult(total_distance_meters=80000, activities_count=1)`

### Casos de borda (Edge Cases)

#### CB-1: Atividade exatamente na fronteira do intervalo
**Dado** que o usuário tem 1 atividade do tipo `"Run"` com `start_date = 2024-06-01T08:00:00+00:00` e `distance_meters = 10000`  
**Quando** `get_run_volume(user_id, start_date=2024-06-01T08:00:00+00:00, end_date=2024-06-01T08:00:00+00:00)` é chamado  
**Então** retorna `VolumeResult(total_distance_meters=10000, activities_count=1)` (fronteiras inclusivas)

#### CB-2: Atividades no intervalo mas nenhuma do tipo correto
**Dado** que o usuário tem atividades do tipo `"Ride"` dentro do intervalo, mas nenhuma `"Run"`  
**Quando** `get_run_volume(user_id, start_date=2024-01-01T00:00:00+00:00, end_date=2024-12-31T23:59:59+00:00)` é chamado  
**Então** retorna `VolumeResult(total_distance_meters=0, activities_count=0)`

#### CB-3: Mix Run + Ride no intervalo; filtro por tipo isola corretamente
**Dado** que o usuário tem um pedal `"Ride"` com `distance_meters = 85000` e uma corrida `"Run"` com `distance_meters = 10000`, ambos dentro do intervalo  
**Quando** `get_run_volume(user_id, start_date=2024-01-01T00:00:00+00:00, end_date=2024-12-31T23:59:59+00:00)` é chamado  
**Então** retorna `VolumeResult(total_distance_meters=10000, activities_count=1)` (filtro por tipo, não soma global)

#### CB-4: Atividade com `distance_meters = 0`
**Dado** que o usuário tem 2 atividades do tipo `"Run"` dentro do intervalo: uma com `distance_meters = 5000` e outra com `distance_meters = 0`  
**Quando** `get_run_volume(user_id, start_date=2024-01-01T00:00:00+00:00, end_date=2024-12-31T23:59:59+00:00)` é chamado  
**Então** retorna `VolumeResult(total_distance_meters=5000, activities_count=2)` (atividade com distância zero conta no `activities_count`)

### Casos de erro

#### CE-1: Nenhuma atividade no intervalo
**Dado** que o usuário tem atividades do tipo `"Run"`, mas todas com `start_date` anterior a `2024-01-01`  
**Quando** `get_run_volume(user_id, start_date=2024-01-01T00:00:00+00:00, end_date=2024-12-31T23:59:59+00:00)` é chamado  
**Então** retorna `VolumeResult(total_distance_meters=0, activities_count=0)` (não lança exceção)

#### CE-2: Intervalo inválido (`start_date > end_date`)
**Dado** que o usuário tem atividades do tipo `"Run"` no histórico  
**Quando** `get_run_volume(user_id, start_date=2024-12-31T00:00:00+00:00, end_date=2024-01-01T00:00:00+00:00)` é chamado  
**Então** retorna `VolumeResult(total_distance_meters=0, activities_count=0)` (não lança exceção)

#### CE-3: Usuário sem atividades
**Dado** que o usuário não tem nenhuma atividade registrada (`get_all` retorna `[]`)  
**Quando** `get_ride_volume(user_id, start_date=2024-01-01T00:00:00+00:00)` é chamado  
**Então** retorna `VolumeResult(total_distance_meters=0, activities_count=0)` (não lança exceção)

---

## Critérios de Aceite

- [ ] Spec com status **Draft** no repositório
- [ ] `VolumeEngine` + `VolumeResult` em `domain/services/` sem dependência de infra (apenas `ActivityRepository`)
- [ ] Helper `_get_volume_by_type` com filtro temporal compartilhado entre Run e Ride
- [ ] Um teste unitário por CN/CB/CE documentado (11 testes de comportamento; subset crítico espelhado ou parametrizado para Ride)
- [ ] Cobertura Domain >= 95% para `volume_engine.py`
- [ ] Nenhuma migration necessária
- [ ] CI verde (ruff, mypy, pytest)
- [ ] Retorna `VolumeResult(0, 0)` sem exceção para intervalo vazio, inválido ou ausência de atividades
- [ ] Fronteiras de intervalo inclusivas (`>= start_date`, `<= end_date`)
- [ ] Soma em metros brutos sem arredondamento no Domain
- [ ] Não contradiz SPEC-001, SPEC-003, SPEC-005/006/009

---

## Mapeamento Spec → Testes

| Artefato                                   | Localização                                          |
|--------------------------------------------|------------------------------------------------------|
| CN/CB/CE do VolumeEngine (`Run`)           | `backend/tests/unit/domain/test_volume_engine.py`    |
| Subset crítico espelhado (`Ride`)          | Mesmo arquivo (`test_volume_engine.py`)              |
| Contrato (instanciação + tipo de retorno)  | Mesmo arquivo (`test_volume_engine.py`)              |

Padrão AAA obrigatório (guia seção 6). Reutilizar `build_activity` de `backend/tests/builders/__init__.py` — sem novos builders. Testes temporais devem usar `start_date` timezone-aware (consistente com `Activity.__post_init__`). Testes de Ride devem passar `activity_type="Ride"` explicitamente.

Exemplo derivado do guia:

```python
def test_get_run_volume_sums_distances_within_date_range():
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
            distance_meters=5000,
            start_date=datetime(2024, 3, 1, 8, 0, 0, tzinfo=UTC),
        ),
        build_activity(
            user_id=user_id,
            distance_meters=10000,
            start_date=datetime(2024, 6, 1, 8, 0, 0, tzinfo=UTC),
        ),
    ]
    engine = VolumeEngine(InMemoryActivityRepository(activities))

    # Act
    result = engine.get_run_volume(
        user_id,
        start_date=datetime(2024, 1, 1, 0, 0, 0, tzinfo=UTC),
        end_date=datetime(2024, 12, 31, 23, 59, 59, tzinfo=UTC),
    )

    # Assert
    assert result.total_distance_meters == 15000
    assert result.activities_count == 2
```

---

## Decisões de Design

### Decisão: Intervalo livre (`start_date` / `end_date`) no Domain
**Contexto:** Usuários perguntam por semana, mês, ano ou intervalo customizado ("quanto corri em 2024?", "essa semana").  
**Opção escolhida:** Parâmetros opcionais `start_date` e `end_date` no VolumeEngine.  
**Alternativas rejeitadas:** Métodos separados (`get_weekly_volume`, `get_monthly_volume`) no Domain.  
**Motivo:** Alinhado à SPEC-009; primitivo reutilizável; semana/mês/ano exigem calendário/fuso e serão resolvidos na SPEC-012 (MCP).

### Decisão: `VolumeResult(0, 0)` vs `None`
**Contexto:** Usuário novo, semana sem treinos ou intervalo sem atividades do tipo.  
**Opção escolhida:** Retornar `VolumeResult(total_distance_meters=0, activities_count=0)`.  
**Alternativas rejeitadas:** `None` (padrão PREngine) ou exceção.  
**Motivo:** Zero km é resposta válida para agregação (guia seção 11); distingue semanticamente "não há recorde" (PR) de "volume zero" (soma).

### Decisão: Fronteiras inclusivas
**Contexto:** Atividade iniciada exatamente em `start_date` ou `end_date` deve contar?  
**Opção escolhida:** `activity.start_date >= start_date` e `activity.start_date <= end_date`.  
**Alternativas rejeitadas:** Intervalo semi-aberto `[start, end)`.  
**Motivo:** Consistente com SPEC-009; intuitivo para "em junho de 2024".

### Decisão: Keyword-only params
**Contexto:** Assinatura inclui `user_id` + parâmetros temporais opcionais.  
**Opção escolhida:** `*, start_date=None, end_date=None` após `user_id`.  
**Alternativas rejeitadas:** Parâmetros posicionais opcionais.  
**Motivo:** Consistente com SPEC-009; evita quebra silenciosa se novos parâmetros forem adicionados.

### Decisão: Helper `_get_volume_by_type`
**Contexto:** `get_run_volume` e `get_ride_volume` terão lógica idêntica de filtro e agregação.  
**Opção escolhida:** Extrair `_get_volume_by_type(user_id, activity_type, *, start_date?, end_date?)`; métodos públicos delegam ao helper.  
**Alternativas rejeitadas:** Duplicar lógica em ambos os métodos.  
**Motivo:** Dois métodos públicos + filtro temporal justificam DRY desde o início (padrão `_get_longest_by_type` da SPEC-009).

### Decisão: `VolumeResult(0, 0)` para intervalo inválido
**Contexto:** `start_date > end_date` é input incoerente.  
**Opção escolhida:** Retornar `VolumeResult(0, 0)` (sem exceção).  
**Alternativas rejeitadas:** `ValueError`, `DomainValidationError` ou `None`.  
**Motivo:** Conjunto filtrado é vazio; soma de conjunto vazio é zero; alinhado ao padrão de agregação desta spec.

### Decisão: Normalização naive → UTC
**Contexto:** `Activity.__post_init__` normaliza `start_date` naive para UTC; parâmetros do engine devem ser consistentes.  
**Opção escolhida:** Duplicar `_normalize_datetime` (~6 linhas) em `volume_engine.py`.  
**Alternativas rejeitadas:** Importar de `pr_engine.py`; extrair módulo compartilhado nesta spec.  
**Motivo:** Evita acoplamento entre engines; refactor cross-cutting fica fora de escopo.

### Decisão: `get_all` + filtro em memória
**Contexto:** Volume baixo por usuário na POC; filtro temporal adiciona passo em memória.  
**Opção escolhida:** Manter `get_all(user_id)` + filtros Python (tipo + intervalo).  
**Alternativas rejeitadas:** Query SQL por intervalo no repositório.  
**Motivo:** Consistente com SPEC-005/006/009; evitar migration/query nova.

### Decisão: Comparação literal `"Run"` / `"Ride"`
**Contexto:** `activity_type` vem do mapper Strava (SPEC-003) como string literal.  
**Opção escolhida:** Match exato `activity_type == "Run"` ou `"Ride"`.  
**Alternativas rejeitadas:** Normalização case-insensitive ou agrupamento de subtipos (`VirtualRide`, etc.).  
**Motivo:** Consistente com PREngine; agrupamento pode ser spec futura se necessário.

### Decisão: `VolumeResult` no mesmo arquivo do engine
**Contexto:** Value object com dois campos; não é entidade com identidade.  
**Opção escolhida:** Dataclass frozen em `volume_engine.py`.  
**Alternativas rejeitadas:** Nova pasta `domain/value_objects/`.  
**Motivo:** POC; diff mínimo; extrair quando houver reuso em outras camadas.

---

## Notas de Migração

- Nenhuma migration
- Nenhuma variável de ambiente nova
- Nenhuma dependência nova
- Rollback: remover `volume_engine.py`, export em `__init__.py` e testes associados — sem impacto em dados

---

## Roadmap pós-SPEC-011

| Spec futura provável | Conteúdo                                                    |
|----------------------|-------------------------------------------------------------|
| SPEC-012             | MCP: `get_run_volume` / `get_ride_volume` + descrições LLM + conversão km |
| SPEC-013+            | API de chat, `period_resolver` (se necessário), auth JWT  |

---

## Checklist de revisão (seção 12 do guia)

### Clareza
- [ ] O contexto explica o problema sem descrever a solução?
- [ ] O contrato tem tipos explícitos para todos os inputs e outputs?
- [ ] Cada comportamento tem "Dado / Quando / Então" completo?
- [ ] Os critérios de aceite são binários e verificáveis?

### Completude
- [ ] Há ao menos um caso normal (CN-1 a CN-4)?
- [ ] Casos de borda cobertos (fronteira inclusiva, tipo errado, mix de tipos, distância zero)?
- [ ] Casos de erro especificados com comportamento esperado (`VolumeResult(0, 0)`, sem exceção)?
- [ ] Escopo "Excluído" deixa claro o que ficou de fora?

### Consistência
- [ ] Não contradiz SPEC-001 (`get_all` → `[]`), SPEC-003 (`activity_type` literal Strava), SPEC-005/006/009?
- [ ] Nomes de tipos alinhados ao código existente (`Activity`, `ActivityRepository`, `VolumeResult`)?
- [ ] Domain não acessa banco diretamente; MCP não entra nesta spec?
- [ ] Filtro temporal idêntico ao PREngine (SPEC-009)?

### Testabilidade
- [ ] Cada comportamento mapeia para teste unitário com `InMemoryActivityRepository`?
- [ ] Comportamentos determinísticos (mesmo input → mesmo output)?
- [ ] Efeitos colaterais explicitados (nenhum) e testáveis?
