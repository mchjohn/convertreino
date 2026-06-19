# SPEC-012 — MCP: tools `get_run_volume` / `get_ride_volume`

| Campo          | Valor                                              |
|----------------|----------------------------------------------------|
| **Status**     | Draft                                              |
| **Autor**      | @convertreino                                      |
| **Revisor**    | —                                                  |
| **Criada em**  | 2026-06-18                                         |
| **Camada**     | MCP                                                |
| **Depende de** | SPEC-001, SPEC-003, SPEC-007, SPEC-011             |
| **Bloqueia**   | API de chat com perguntas de volume                |
| **Épico**      | Volume                                             |

---

## Contexto

Com o VolumeEngine já calculando distância acumulada de forma determinística (SPEC-011), o usuário pode perguntar *"quanto corri essa semana?"*, *"quantos km em 2024?"* ou *"qual meu volume total de pedal?"* via chat. Sem MCP tools dedicadas, o LLM poderia somar distâncias manualmente, escolher atividades erradas ou confundir **volume agregado** (soma) com **recorde** (maior distância individual — `get_longest_run` / `get_longest_ride`, SPEC-007/008).

O ConverTreino delega cálculos analíticos a serviços determinísticos; o LLM **não** deve inferir quais atividades entram na soma nem executar a agregação. Quando o usuário mencionar um período, o LLM deve chamar a tool com `start_date`/`end_date` explícitos (ISO 8601 UTC), orientado pelas descrições da tool — mesmo padrão da SPEC-010. Períodos nomeados ("esta semana", "ano passado") são convertidos pelo LLM em intervalos de data, **sem** utilitário server-side de resolução de períodos.

As descrições de `get_longest_run` / `get_longest_ride` (SPEC-010) ainda referenciam volume como responsabilidade futura; esta spec fecha esse gap e atualiza as fronteiras de intenção entre tools PR e tools de volume.

---

## Escopo

### Incluído

- Novas tools MCP `get_run_volume` e `get_ride_volume` (contrato simétrico Run/Ride)
- Handlers em `tools/volume.py` delegando a `VolumeEngine.get_run_volume` / `get_ride_volume`
- Registro das tools no servidor MCP existente (`server.py` — stdio + HTTP/SSE em `/mcp`)
- Schemas Pydantic `RunVolumeResult` e `RideVolumeResult` em `mcp/schemas.py`
- Mapper `VolumeResult` (domain) → schema MCP em `mcp/mappers.py` com conversão para km
- Parâmetros opcionais keyword-only `start_date` / `end_date` (ISO 8601 UTC), propagados ao VolumeEngine
- Descrições LLM (`GET_RUN_VOLUME_DESCRIPTION`, `GET_RIDE_VOLUME_DESCRIPTION`) com:
  - Fronteira **soma vs recorde** (volume ≠ longest)
  - Fronteira **Run vs Ride**
  - Tabela intenção → parâmetros (2024, semana corrente, mês corrente, intervalo customizado)
  - Seções **"Perguntas que DEVEM acionar"** e **"Perguntas que NÃO devem acionar"**
- **Atualização** de `GET_LONGEST_RUN_DESCRIPTION` e `GET_LONGEST_RIDE_DESCRIPTION` em `tools/pr.py`: substituir `"volume engine (futuro)"` por `get_run_volume` / `get_ride_volume`
- Testes unitários em `test_get_run_volume_tool.py` e `test_get_ride_volume_tool.py`
- Testes de mapper em `test_mappers.py`
- Atualização de `test_server.py` — registro e descrições das novas tools
- Cobertura mínima MCP: 90% (guia seção 8)

### Excluído (explicitamente fora desta spec)

- Alterações no `VolumeEngine` ou Domain (já coberto pela SPEC-011)
- Tools separadas por período nomeado (`get_weekly_volume`, `get_monthly_volume`, etc.) — LLM converte para ISO 8601
- Utilitário de resolução de períodos nomeados no servidor (`period_resolver.py`)
- Parâmetro `reference_date` ou timezone do usuário
- Volume combinado Run+Ride ("quanto treinei no total?")
- Outros tipos de atividade (`Swim`, `VirtualRide`, `EBikeRide`, etc.)
- Pace, tempo ou elevação agregados
- Endpoint REST, auth JWT, chat orchestrator
- Testes E2E com LLM real
- Application Service intermediário (`VolumeQueryService`)

---

## Contrato — MCP Tools

As duas tools abaixo seguem contrato simétrico; ambas retornam a mesma estrutura de output (`total_distance_km`, `activities_count`).

### Tool `get_run_volume`

#### Nome

`get_run_volume`

#### Descrição para o LLM

Retorna o volume total de corridas (`Run`) do usuário — soma de distâncias e contagem de atividades — opcionalmente filtrado por intervalo de datas. Use quando o usuário perguntar **quanto correu**, volume de corrida, distância acumulada correndo, quantos km em um período, ou quantas corridas fez — **com ou sem** menção a período (semana, mês, ano, intervalo customizado). Quando o usuário mencionar um período, passe `start_date` e/ou `end_date` em ISO 8601 UTC. **NÃO** use para pedais/ciclismo (`get_ride_volume`), recorde de corrida individual (`get_longest_run`), natação, pace médio ou elevação.

**Orientação de conversão intenção → parâmetros (LLM):**

| Intenção do usuário              | `start_date`                          | `end_date`                            |
|----------------------------------|---------------------------------------|---------------------------------------|
| "essa semana"                    | primeiro instante da semana corrente UTC (segunda 00:00) | último instante da semana corrente UTC (domingo 23:59:59) |
| "em 2024"                        | `2024-01-01T00:00:00+00:00`           | `2024-12-31T23:59:59+00:00`           |
| "neste mês"                      | primeiro instante do mês corrente UTC | último instante do mês corrente UTC   |
| "entre março e junho de 2024"    | `2024-03-01T00:00:00+00:00`           | `2024-06-30T23:59:59+00:00`           |
| Sem período mencionado           | omitir (histórico completo)           | omitir (histórico completo)           |

#### Perguntas que DEVEM acionar esta tool

- "Quanto corri essa semana?"
- "Quantos km corri em 2024?"
- "Qual meu volume total de corrida?"
- "Quantas corridas fiz neste mês?"
- "Qual a distância acumulada correndo **entre março e junho**?"
- "Quanto corri **no ano passado**?" (LLM converte para intervalo ISO 8601)

#### Perguntas que NÃO devem acionar esta tool

- "Qual foi minha corrida mais longa?" → `get_longest_run` (recorde, não soma)
- "Qual a maior distância que já corri?" → `get_longest_run`
- "Quanto pedalei essa semana?" → `get_ride_volume`
- "Quanto treinei no total?" (Run + Ride) → fora de escopo
- "Qual meu pace médio?" → engine de pace (futuro)

---

### Tool `get_ride_volume`

#### Nome

`get_ride_volume`

#### Descrição para o LLM

Retorna o volume total de pedais (`Ride`) do usuário — soma de distâncias e contagem de atividades — opcionalmente filtrado por intervalo de datas. Use quando o usuário perguntar **quanto pedalou**, volume de ciclismo, distância acumulada pedalando, quantos km em um período, ou quantos pedais fez — **com ou sem** menção a período (semana, mês, ano, intervalo customizado). Quando o usuário mencionar um período, passe `start_date` e/ou `end_date` em ISO 8601 UTC. **NÃO** use para corridas (`get_run_volume`), recorde de pedal individual (`get_longest_ride`), natação ou elevação.

**Orientação de conversão intenção → parâmetros (LLM):** mesma tabela de `get_run_volume` (substituir contexto de corrida por pedal).

#### Perguntas que DEVEM acionar esta tool

- "Quanto pedalei essa semana?"
- "Quantos km pedalei em 2024?"
- "Qual meu volume total de pedal?"
- "Quantos pedais fiz neste mês?"
- "Qual a distância acumulada pedalando **entre março e junho**?"

#### Perguntas que NÃO devem acionar esta tool

- "Qual foi meu pedal mais longo?" → `get_longest_ride` (recorde, não soma)
- "Qual a maior distância que já pedalei?" → `get_longest_ride`
- "Quanto corri essa semana?" → `get_run_volume`
- "Quanto treinei no total?" (Run + Ride) → fora de escopo
- "Qual minha velocidade média geral?" → engine de velocidade (futuro)

---

### Input schema (ambas as tools)

| Campo        | Tipo                | Obrigatório | Descrição                                                                 |
|--------------|---------------------|-------------|---------------------------------------------------------------------------|
| `user_id`    | `str` (UUID)        | Sim         | ID interno do usuário. Na POC, passado pelo orchestrator de chat (pós-OAuth SPEC-002). O LLM **não** deve inferir este valor. |
| `start_date` | `datetime \| None`  | Não         | Limite inferior inclusivo (ISO 8601, preferencialmente timezone-aware UTC). `None` = sem limite inferior |
| `end_date`   | `datetime \| None`  | Não         | Limite superior inclusivo. `None` = sem limite superior                   |

FastMCP infere o JSON schema a partir das anotações de tipo; strings ISO 8601 são parseadas automaticamente para `datetime`.

### Assinaturas

```python
# tools/volume.py
def get_run_volume(
    user_id: UUID,
    engine: VolumeEngine,
    *,
    start_date: datetime | None = None,
    end_date: datetime | None = None,
) -> RunVolumeResult: ...

def get_ride_volume(
    user_id: UUID,
    engine: VolumeEngine,
    *,
    start_date: datetime | None = None,
    end_date: datetime | None = None,
) -> RideVolumeResult: ...

# server.py
@mcp.tool(name="get_run_volume", description=GET_RUN_VOLUME_DESCRIPTION)
def get_run_volume_tool(
    user_id: UUID,
    *,
    start_date: datetime | None = None,
    end_date: datetime | None = None,
) -> dict[str, Any]: ...

@mcp.tool(name="get_ride_volume", description=GET_RIDE_VOLUME_DESCRIPTION)
def get_ride_volume_tool(
    user_id: UUID,
    *,
    start_date: datetime | None = None,
    end_date: datetime | None = None,
) -> dict[str, Any]: ...
```

### Output schema

```python
class RunVolumeResult(BaseModel):
    total_distance_km: float
    activities_count: int

class RideVolumeResult(BaseModel):
    total_distance_km: float
    activities_count: int
```

**Diferença semântica vs tools PR:** volume **nunca** retorna campos `null`. Ausência de dados, intervalo vazio ou inválido produz `{ total_distance_km: 0.0, activities_count: 0 }` (resposta válida, sem exceção MCP).

| Situação                         | PREngine (SPEC-007/008) | Volume MCP (SPEC-012)        |
|----------------------------------|-------------------------|------------------------------|
| Nenhuma atividade no recorte     | campos `null`           | `{0.0, 0}`                   |
| Intervalo inválido               | campos `null`           | `{0.0, 0}`                   |
| Usuário sem atividades           | campos `null`           | `{0.0, 0}`                   |

### Regras de mapeamento (`VolumeResult` domain → MCP)

| Campo Domain              | Campo MCP             | Transformação              |
|---------------------------|-----------------------|----------------------------|
| `total_distance_meters`   | `total_distance_km`   | `round(m / 1000, 3)`       |
| `activities_count`        | `activities_count`    | identidade (`int`)         |

Mapper sugerido:

```python
def volume_result_to_run_volume_result(result: VolumeResult) -> RunVolumeResult:
    return RunVolumeResult(
        total_distance_km=round(result.total_distance_meters / 1000, 3),
        activities_count=result.activities_count,
    )

def volume_result_to_ride_volume_result(result: VolumeResult) -> RideVolumeResult:
    return RideVolumeResult(
        total_distance_km=round(result.total_distance_meters / 1000, 3),
        activities_count=result.activities_count,
    )
```

### Regras de delegação

1. MCP repassa `start_date`/`end_date` ao `VolumeEngine` **sem reimplementar** filtro temporal ou agregação
2. Intervalo incoerente (`start_date > end_date`) → VolumeEngine retorna `VolumeResult(0, 0)` → mapper retorna `{0.0, 0}`
3. `start_date`/`end_date` malformados (não parseáveis como datetime) → erro de validação MCP (`ToolError`)
4. Chamada sem `start_date` nem `end_date` → histórico completo do tipo (SPEC-011 CN-2)
5. Arredondamento para km ocorre **apenas** no mapper MCP; Domain soma metros brutos (SPEC-011)

### Efeitos colaterais

Nenhum. Operação somente leitura via `VolumeEngine` → `ActivityRepository.get_all`.

---

## Comportamentos

Os casos abaixo aplicam-se simetricamente a `get_run_volume` e `get_ride_volume`. Nos exemplos, `"Run"` e `"Ride"` são intercambiáveis conforme a tool testada. Valores de distância no output MCP estão em **km** (3 casas decimais).

### Casos normais (Happy Path)

#### CN-1: Intervalo contém múltiplas atividades — soma correta
**Dado** que o usuário tem 3 atividades do tipo `"Run"`:  
- `start_date = 2023-01-01T08:00:00+00:00`, `distance_meters = 42000`  
- `start_date = 2024-03-01T08:00:00+00:00`, `distance_meters = 5000`  
- `start_date = 2024-06-01T08:00:00+00:00`, `distance_meters = 10000`  
**Quando** a tool `get_run_volume(user_id, start_date=2024-01-01T00:00:00+00:00, end_date=2024-12-31T23:59:59+00:00)` é chamada  
**Então** retorna `total_distance_km == 15.0` e `activities_count == 2` (a de `42000` em 2023 fica fora do intervalo)

#### CN-2: Sem filtro temporal — histórico completo
**Dado** que o usuário tem 3 atividades do tipo `"Run"` com `distance_meters` de `5000`, `21097` e `10000`  
**Quando** a tool `get_run_volume(user_id)` é chamada (sem `start_date` nem `end_date`)  
**Então** retorna `total_distance_km == 36.097` e `activities_count == 3`

#### CN-3: Apenas `start_date` — sem limite superior
**Dado** que o usuário tem 2 atividades do tipo `"Run"`:  
- `start_date = 2023-06-01T08:00:00+00:00`, `distance_meters = 30000`  
- `start_date = 2024-06-01T08:00:00+00:00`, `distance_meters = 10000`  
**Quando** a tool `get_run_volume(user_id, start_date=2024-01-01T00:00:00+00:00)` é chamada  
**Então** retorna `total_distance_km == 10.0` e `activities_count == 1`

#### CN-4: Apenas `end_date` — sem limite inferior
**Dado** que o usuário tem 2 atividades do tipo `"Ride"`:  
- `start_date = 2023-06-01T08:00:00+00:00`, `distance_meters = 80000`  
- `start_date = 2024-06-01T08:00:00+00:00`, `distance_meters = 120000`  
**Quando** a tool `get_ride_volume(user_id, end_date=2023-12-31T23:59:59+00:00)` é chamada  
**Então** retorna `total_distance_km == 80.0` e `activities_count == 1`

### Casos de borda (Edge Cases)

#### CB-1: Atividade exatamente na fronteira do intervalo
**Dado** que o usuário tem 1 atividade do tipo `"Run"` com `start_date = 2024-06-01T08:00:00+00:00` e `distance_meters = 10000`  
**Quando** a tool `get_run_volume(user_id, start_date=2024-06-01T08:00:00+00:00, end_date=2024-06-01T08:00:00+00:00)` é chamada  
**Então** retorna `total_distance_km == 10.0` e `activities_count == 1` (fronteiras inclusivas)

#### CB-2: Atividades no intervalo mas nenhuma do tipo correto
**Dado** que o usuário tem atividades do tipo `"Ride"` dentro do intervalo, mas nenhuma `"Run"`  
**Quando** a tool `get_run_volume(user_id, start_date=2024-01-01T00:00:00+00:00, end_date=2024-12-31T23:59:59+00:00)` é chamada  
**Então** retorna `total_distance_km == 0.0` e `activities_count == 0`

#### CB-3: Mix Run + Ride no intervalo; filtro por tipo isola corretamente
**Dado** que o usuário tem um pedal `"Ride"` com `distance_meters = 85000` e uma corrida `"Run"` com `distance_meters = 10000`, ambos dentro do intervalo  
**Quando** a tool `get_run_volume(user_id, start_date=2024-01-01T00:00:00+00:00, end_date=2024-12-31T23:59:59+00:00)` é chamada  
**Então** retorna `total_distance_km == 10.0` e `activities_count == 1` (filtro por tipo, não soma global)

#### CB-4: Atividade com `distance_meters = 0`
**Dado** que o usuário tem 2 atividades do tipo `"Run"` dentro do intervalo: uma com `distance_meters = 5000` e outra com `distance_meters = 0`  
**Quando** a tool `get_run_volume(user_id, start_date=2024-01-01T00:00:00+00:00, end_date=2024-12-31T23:59:59+00:00)` é chamada  
**Então** retorna `total_distance_km == 5.0` e `activities_count == 2` (atividade com distância zero conta no `activities_count`)

### Casos de erro

#### CE-1: Nenhuma atividade no intervalo
**Dado** que o usuário tem atividades do tipo `"Run"`, mas todas com `start_date` anterior a `2024-01-01`  
**Quando** a tool `get_run_volume(user_id, start_date=2024-01-01T00:00:00+00:00, end_date=2024-12-31T23:59:59+00:00)` é chamada  
**Então** retorna `total_distance_km == 0.0` e `activities_count == 0` (não lança exceção)

#### CE-2: Intervalo inválido (`start_date > end_date`)
**Dado** que o usuário tem atividades do tipo `"Run"` no histórico  
**Quando** a tool `get_run_volume(user_id, start_date=2024-12-31T00:00:00+00:00, end_date=2024-01-01T00:00:00+00:00)` é chamada  
**Então** retorna `total_distance_km == 0.0` e `activities_count == 0` (não lança exceção)

#### CE-3: Usuário sem atividades
**Dado** que o usuário não tem nenhuma atividade registrada (`get_all` retorna `[]`)  
**Quando** a tool `get_ride_volume(user_id, start_date=2024-01-01T00:00:00+00:00)` é chamada  
**Então** retorna `total_distance_km == 0.0` e `activities_count == 0` (não lança exceção)

#### CE-4: `start_date` ou `end_date` malformados
**Dado** que `start_date` não é parseável como datetime ISO 8601 (ex.: `"not-a-date"`)  
**Quando** a tool `get_run_volume(user_id, start_date="not-a-date")` é chamada  
**Então** retorna erro de validação MCP (`ToolError`)

---

## Critérios de Aceite

- [ ] Spec com status **Draft** no repositório
- [ ] Tools `get_run_volume` e `get_ride_volume` registradas em `server.py` e delegam ao `VolumeEngine` (SPEC-011)
- [ ] Handlers em `tools/volume.py` sem lógica duplicada de filtro ou agregação
- [ ] Schemas `RunVolumeResult` / `RideVolumeResult` e mappers em `schemas.py` / `mappers.py`
- [ ] Output sempre numérico (`0.0` / `0` quando vazio — nunca `null`)
- [ ] Conversão para km com `round(m / 1000, 3)` apenas no mapper MCP
- [ ] Descrições LLM com fronteiras volume vs recorde e Run vs Ride
- [ ] Descrições PR (`GET_LONGEST_*_DESCRIPTION`) atualizadas para referenciar `get_run_volume` / `get_ride_volume`
- [ ] Um teste unitário por CN/CB/CE documentado (12 casos Run; subset crítico CN-1, CN-2, CE-1 espelhado para Ride)
- [ ] Testes de mapper para conversão domain → MCP
- [ ] `test_server.py` verifica registro e descrições das novas tools
- [ ] Cobertura `convertreino.mcp` >= 90%
- [ ] Cobertura Domain mantida >= 95%
- [ ] CI verde (ruff, mypy, pytest)
- [ ] Nenhuma migration ou env var nova
- [ ] Não contradiz SPEC-001, SPEC-007, SPEC-010 nem SPEC-011

---

## Mapeamento Spec → Testes

| Artefato                                   | Localização                                               |
|--------------------------------------------|-----------------------------------------------------------|
| CN/CB/CE (`Run`)                           | `backend/tests/unit/mcp/test_get_run_volume_tool.py`      |
| Subset crítico (`Ride`)                    | `backend/tests/unit/mcp/test_get_ride_volume_tool.py`    |
| Mapper domain → MCP                        | `backend/tests/unit/mcp/test_mappers.py`                  |
| Registro + descrições                      | `backend/tests/unit/mcp/test_server.py`                   |
| Atualização fronteiras PR                  | `test_server.py` e/ou testes existentes de `get_longest_*` |

Padrão AAA obrigatório (guia seção 6). Reutilizar `build_activity` de `backend/tests/builders/__init__.py`. Testes temporais devem usar `start_date` timezone-aware (consistente com `Activity.__post_init__`). Testes de Ride devem passar `activity_type="Ride"` explicitamente.

Helper de teste:

```python
async def _call_get_run_volume(
    user_id,
    *,
    start_date: datetime | None = None,
    end_date: datetime | None = None,
) -> RunVolumeResult:
    payload: dict[str, str] = {"user_id": str(user_id)}
    if start_date is not None:
        payload["start_date"] = start_date.isoformat()
    if end_date is not None:
        payload["end_date"] = end_date.isoformat()
    server = create_mcp_server()
    async with Client(server) as client:
        result = await client.call_tool("get_run_volume", payload)
    return RunVolumeResult.model_validate(result.data)
```

Exemplo derivado da SPEC-011:

```python
@pytest.mark.anyio
async def test_get_run_volume_sums_distances_within_date_range():
    # Arrange — CN-1
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
    _configure_engine(activities)

    # Act
    result = await _call_get_run_volume(
        user_id,
        start_date=datetime(2024, 1, 1, 0, 0, 0, tzinfo=UTC),
        end_date=datetime(2024, 12, 31, 23, 59, 59, tzinfo=UTC),
    )

    # Assert
    assert result.total_distance_km == 15.0
    assert result.activities_count == 2
```

---

## Decisões de Design

### Decisão: Duas tools tipadas (`get_run_volume` / `get_ride_volume`)
**Contexto:** Volume agregado existe para Run e Ride com lógica idêntica mas fronteiras de intenção distintas.  
**Opção escolhida:** Duas tools MCP nomeadas por tipo, espelhando SPEC-011 e o par PR (`get_longest_run` / `get_longest_ride`).  
**Alternativas rejeitadas:** Tool genérica `get_volume(activity_type)`.  
**Motivo:** Descrições LLM precisas por tipo; consistente com arquitetura MCP existente.

### Decisão: Intervalo livre via ISO 8601 (sem `get_weekly_volume`)
**Contexto:** Usuários perguntam por semana, mês, ano ou intervalo customizado.  
**Opção escolhida:** Parâmetros opcionais `start_date`/`end_date` + tabela de conversão na descrição LLM.  
**Alternativas rejeitadas:** Tools separadas por período (`get_weekly_volume`, `get_monthly_volume`); `period_resolver.py` server-side.  
**Motivo:** Alinhado à SPEC-011 e SPEC-010; Domain permanece primitivo; evita proliferar tools MCP.

### Decisão: Zero é resposta válida, não `null`
**Contexto:** Semana sem treinos, usuário novo ou intervalo sem atividades do tipo.  
**Opção escolhida:** Retornar `{ total_distance_km: 0.0, activities_count: 0 }`.  
**Alternativas rejeitadas:** Campos `null` (padrão PREngine) ou exceção.  
**Motivo:** Zero km é resposta válida para agregação (guia seção 11); distingue volume de recorde.

### Decisão: `total_distance_km` com 3 casas decimais
**Contexto:** Domain soma metros brutos; LLM apresenta km ao usuário.  
**Opção escolhida:** `round(m / 1000, 3)` no mapper MCP.  
**Alternativas rejeitadas:** Arredondar no Domain; expor metros ao LLM.  
**Motivo:** Consistente com `distance_km` em `mcp/mappers.py` (SPEC-007/008); arredondamento na camada de apresentação.

### Decisão: `tools/volume.py` separado de `tools/pr.py`
**Contexto:** Novas tools de volume convivem com tools PR existentes.  
**Opção escolhida:** Módulo dedicado `tools/volume.py` para handlers e descrições de volume.  
**Alternativas rejeitadas:** Adicionar handlers de volume em `tools/pr.py`.  
**Motivo:** Separação por épico (Volume vs PR); evita módulo PR crescer além do escopo.

### Decisão: Atualizar descrições PR na mesma spec
**Contexto:** SPEC-010 referencia volume como "futuro"; com SPEC-012 implementada, fronteiras desatualizadas confundem o LLM.  
**Opção escolhida:** Atualizar `GET_LONGEST_RUN_DESCRIPTION` e `GET_LONGEST_RIDE_DESCRIPTION` para apontar a `get_run_volume` / `get_ride_volume`.  
**Alternativas rejeitadas:** Deixar referências obsoletas; spec separada só para descrições.  
**Motivo:** Roteamento correto exige fronteiras consistentes entre todas as tools registradas.

### Decisão: Keyword-only params
**Contexto:** Assinatura inclui `user_id` + parâmetros temporais opcionais.  
**Opção escolhida:** `*, start_date=None, end_date=None` após `user_id`.  
**Alternativas rejeitadas:** Parâmetros posicionais opcionais.  
**Motivo:** Consistente com SPEC-010; evita quebra silenciosa em evoluções futuras.

### Decisão: Delegação direta ao VolumeEngine
**Contexto:** MCP não deve reimplementar filtro temporal ou agregação.  
**Opção escolhida:** Handlers repassam parâmetros ao VolumeEngine; mapper converte output.  
**Alternativas rejeitadas:** Filtrar ou somar atividades na camada MCP.  
**Motivo:** Regra de negócio pertence ao Domain (SPEC-011); MCP é adaptador LLM-friendly.

### Decisão: Validação em duas camadas
**Contexto:** Erros de input temporal podem ser de formato ou de coerência semântica.  
**Opção escolhida:** Formato inválido → erro MCP (`ToolError`); intervalo incoerente (`start > end`) → VolumeEngine retorna `(0, 0)` → output `{0.0, 0}`.  
**Alternativas rejeitadas:** Validar `start > end` na MCP com exceção.  
**Motivo:** Alinhado à SPEC-011; MCP não duplica regra de negócio do Domain.

### Decisão: Schemas simétricos `RunVolumeResult` / `RideVolumeResult`
**Contexto:** Output idêntico para Run e Ride; nomes distintos facilitam evolução futura.  
**Opção escolhida:** Dois modelos Pydantic com mesma estrutura, espelhando `LongestRunResult` / `LongestRideResult`.  
**Alternativas rejeitadas:** Schema único `VolumeResult` na camada MCP (colide com domain); campos nullable.  
**Motivo:** Consistência com par PR; evita import ambiguity com `VolumeResult` do domain.

---

## Notas de Migração

- Nenhuma dependência nova (`fastmcp` já adicionada na SPEC-007)
- Nenhuma migration de banco
- Nenhuma variável de ambiente nova
- Aditivo: novas tools não alteram contrato das tools PR existentes
- Rollback: remover `tools/volume.py`, schemas, mappers, registros em `server.py`, testes associados e reverter descrições PR — sem impacto em dados

---

## Roadmap pós-SPEC-012

| Spec futura provável | Conteúdo                                                    |
|----------------------|-------------------------------------------------------------|
| SPEC-013+            | API de chat, auth JWT, `period_resolver` (se necessário)  |

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
- [ ] Casos de erro especificados com comportamento esperado (`{0.0, 0}`, `ToolError`)?
- [ ] Escopo "Excluído" deixa claro o que ficou de fora?

### Consistência
- [ ] Não contradiz SPEC-001, SPEC-007, SPEC-010 nem SPEC-011?
- [ ] Nomes de tipos alinhados ao código existente?
- [ ] MCP delega ao Domain; não reimplementa regra de negócio?
- [ ] Fronteiras volume vs recorde explícitas nas descrições LLM?

### Testabilidade
- [ ] Cada comportamento mapeia para teste unitário com `InMemoryActivityRepository`?
- [ ] Comportamentos determinísticos (mesmo input → mesmo output)?
- [ ] Efeitos colaterais explicitados (nenhum) e testáveis?
