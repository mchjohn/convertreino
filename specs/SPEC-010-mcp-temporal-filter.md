# SPEC-010 — MCP: filtro temporal em `get_longest_run` / `get_longest_ride`

| Campo          | Valor                                              |
|----------------|----------------------------------------------------|
| **Status**     | Draft                                              |
| **Autor**      | @convertreino                                      |
| **Revisor**    | —                                                  |
| **Criada em**  | 2026-06-18                                         |
| **Camada**     | MCP                                                |
| **Depende de** | SPEC-001, SPEC-007, SPEC-008, SPEC-009             |
| **Bloqueia**   | API de chat com perguntas por período              |
| **Épico**      | PR / Conversacional                                |

---

## Contexto

Com o filtro temporal já implementado no PREngine (SPEC-009), o usuário pode perguntar não só *"qual foi minha corrida/pedal mais longo?"* (histórico completo), mas também *"em 2024?"*, *"neste mês?"* ou *"entre março e junho?"*. As MCP tools `get_longest_run` e `get_longest_ride` (SPEC-007/008) ainda aceitam apenas `user_id` — perguntas com recorte temporal retornam o histórico completo, produzindo resposta incorreta.

O ConverTreino delega cálculos analíticos a serviços determinísticos; o LLM **não** deve escolher manualmente quais atividades entram no cálculo. Quando o usuário mencionar um período, o LLM deve chamar a tool com `start_date`/`end_date` explícitos (ISO 8601 UTC), orientado pelas descrições da tool. Períodos nomeados ("este mês", "ano passado") são convertidos pelo LLM em intervalos de data — **sem** utilitário server-side de resolução de períodos nesta spec.

---

## Escopo

### Incluído

- Parâmetros opcionais `start_date: datetime | None = None` e `end_date: datetime | None = None` (keyword-only) em:
  - Tool MCP `get_longest_run` (wrapper em `server.py`)
  - Tool MCP `get_longest_ride`
  - Handlers em `tools/pr.py` — propagar ao `PREngine.get_longest_run` / `get_longest_ride`
- Atualização de `GET_LONGEST_RUN_DESCRIPTION` e `GET_LONGEST_RIDE_DESCRIPTION` com:
  - Quando usar filtro temporal
  - Exemplos de mapeamento intenção → parâmetros (2024, mês corrente, intervalo customizado)
  - Fronteiras: volume semanal/mensal agregado continua fora de escopo
- Seções **"Perguntas que DEVEM acionar (com período)"** e exemplos de conversão de datas na descrição
- Testes unitários temporais em `test_get_longest_run_tool.py` e `test_get_longest_ride_tool.py`
- Atualização de `test_server.py` — descrições mencionam filtro temporal
- Subset crítico de casos temporais espelhado para Ride (padrão SPEC-009)
- Cobertura mínima MCP: 90% (guia seção 8)
- Retrocompatibilidade: chamadas sem datas = comportamento SPEC-007/008

### Excluído (explicitamente fora desta spec)

- Alterações no PREngine ou Domain (já coberto pela SPEC-009)
- Utilitário de resolução de períodos nomeados no servidor (`period_resolver.py`)
- Parâmetro `reference_date` ou timezone do usuário
- Novas tools MCP ou mudança de output schema (`LongestRunResult` / `LongestRideResult` inalterados)
- Volume Engine, chat orchestrator, auth JWT
- Testes E2E com LLM real
- Endpoint REST dedicado
- Application Service intermediário (`PrQueryService`)

---

## Contrato — MCP Tools

As duas tools abaixo seguem contrato simétrico; diferenças de output (pace vs velocidade) permanecem conforme SPEC-007/008.

### Tool `get_longest_run`

#### Nome

`get_longest_run`

#### Descrição para o LLM

Retorna a corrida (`Run`) com maior distância do usuário, opcionalmente filtrada por intervalo de datas. Use quando o usuário perguntar sobre sua corrida mais longa, maior distância correndo, ou recorde de corrida — **com ou sem** menção a período (ano, mês, intervalo customizado). Quando o usuário mencionar um período, passe `start_date` e/ou `end_date` em ISO 8601 UTC. **NÃO** use para pedais/ciclismo (`get_longest_ride`), natação, volume semanal/mensal agregado, pace médio geral ou elevação.

**Orientação de conversão intenção → parâmetros (LLM):**

| Intenção do usuário              | `start_date`                          | `end_date`                            |
|----------------------------------|---------------------------------------|---------------------------------------|
| "em 2024"                        | `2024-01-01T00:00:00+00:00`           | `2024-12-31T23:59:59+00:00`           |
| "neste mês"                      | primeiro instante do mês corrente UTC | último instante do mês corrente UTC   |
| "entre março e junho de 2024"    | `2024-03-01T00:00:00+00:00`           | `2024-06-30T23:59:59+00:00`           |
| Sem período mencionado           | omitir (histórico completo)           | omitir (histórico completo)           |

#### Perguntas que DEVEM acionar esta tool

- "Qual foi minha corrida mais longa?"
- "Qual meu recorde de corrida em km?"
- "Qual a maior distância que já corri?"
- "Qual foi minha corrida mais longa **em 2024**?"
- "Qual meu recorde de corrida **neste mês**?"
- "Qual a maior distância que corri **entre março e junho**?"

#### Perguntas que NÃO devem acionar esta tool

- "Qual foi meu pedal mais longo?" → `get_longest_ride`
- "Quanto corri essa semana?" → volume engine (futuro)
- "Quanto corri em 2024?" (soma total) → volume engine (futuro)
- "Qual meu pace médio?" → engine de pace (futuro)

---

### Tool `get_longest_ride`

#### Nome

`get_longest_ride`

#### Descrição para o LLM

Retorna o pedal (`Ride`) com maior distância do usuário, opcionalmente filtrado por intervalo de datas. Use quando o usuário perguntar sobre seu pedal mais longo, maior distância pedalando, ou recorde de ciclismo — **com ou sem** menção a período (ano, mês, intervalo customizado). Quando o usuário mencionar um período, passe `start_date` e/ou `end_date` em ISO 8601 UTC. **NÃO** use para corridas (`get_longest_run`), natação, volume semanal/mensal agregado ou elevação.

**Orientação de conversão intenção → parâmetros (LLM):** mesma tabela de `get_longest_run` (substituir contexto de corrida por pedal).

#### Perguntas que DEVEM acionar esta tool

- "Qual foi meu pedal mais longo?"
- "Qual meu recorde de pedal em km?"
- "Qual a maior distância que já pedalei?"
- "Qual foi meu pedal mais longo **em 2024**?"
- "Qual meu recorde de ciclismo **neste mês**?"

#### Perguntas que NÃO devem acionar esta tool

- "Qual foi minha corrida mais longa?" → `get_longest_run`
- "Quanto pedalei essa semana?" → volume engine (futuro)
- "Quanto pedalei em 2024?" (soma total) → volume engine (futuro)
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
# tools/pr.py
def get_longest_run(
    user_id: UUID,
    engine: PREngine,
    *,
    start_date: datetime | None = None,
    end_date: datetime | None = None,
) -> LongestRunResult: ...

def get_longest_ride(
    user_id: UUID,
    engine: PREngine,
    *,
    start_date: datetime | None = None,
    end_date: datetime | None = None,
) -> LongestRideResult: ...

# server.py
@mcp.tool(name="get_longest_run", description=GET_LONGEST_RUN_DESCRIPTION)
def get_longest_run_tool(
    user_id: UUID,
    *,
    start_date: datetime | None = None,
    end_date: datetime | None = None,
) -> dict[str, Any]: ...

@mcp.tool(name="get_longest_ride", description=GET_LONGEST_RIDE_DESCRIPTION)
def get_longest_ride_tool(
    user_id: UUID,
    *,
    start_date: datetime | None = None,
    end_date: datetime | None = None,
) -> dict[str, Any]: ...
```

### Output schema

**Inalterado** em relação à SPEC-007/008:

```python
class LongestRunResult(BaseModel):
    activity_id: str | None
    distance_km: float | None
    date: str | None              # ISO 8601 UTC
    duration_minutes: float | None
    average_pace_min_per_km: float | None  # null se distance_km == 0

class LongestRideResult(BaseModel):
    activity_id: str | None
    distance_km: float | None
    date: str | None              # ISO 8601 UTC
    duration_minutes: float | None
    average_speed_kmh: float | None  # null se distance_km == 0
```

Quando o PREngine retorna `None` (intervalo vazio, inválido ou ausência de atividades): retornar schema com todos os campos `null` (resposta válida, sem exceção MCP).

### Regras de delegação

1. MCP repassa `start_date`/`end_date` ao PREngine **sem reimplementar** filtro temporal
2. Intervalo incoerente (`start_date > end_date`) → PREngine retorna `None` → mapper retorna campos `null`
3. `start_date`/`end_date` malformados (não parseáveis como datetime) → erro de validação MCP (FastMCP/Pydantic)
4. Chamada sem `start_date` nem `end_date` → comportamento idêntico à SPEC-007/008 (histórico completo)
5. Regras de mapeamento `Activity` → output permanecem conforme SPEC-007/008

### Efeitos colaterais

Nenhum. Operação somente leitura via `PREngine` → `ActivityRepository.get_all`.

---

## Comportamentos

Os casos temporais abaixo aplicam-se simetricamente a `get_longest_run` e `get_longest_ride`. Nos exemplos, `"Run"` e `"Ride"` são intercambiáveis conforme a tool testada. Resultados `None` do PREngine mapeiam para todos os campos `null` no output MCP.

Testes existentes de SPEC-007/008 (CN/CB/CE sem filtro temporal) **permanecem verdes** sem alteração de asserções.

### Casos normais (Happy Path)

#### CN-1: Intervalo contém múltiplas atividades; vencedora está dentro do intervalo
**Dado** que o usuário tem 3 atividades do tipo `"Run"`:  
- `start_date = 2023-01-01T08:00:00+00:00`, `distance_meters = 42000`  
- `start_date = 2024-03-01T08:00:00+00:00`, `distance_meters = 15000`  
- `start_date = 2024-08-01T08:00:00+00:00`, `distance_meters = 25000`  
**Quando** a tool `get_longest_run(user_id, start_date=2024-01-01T00:00:00+00:00, end_date=2024-12-31T23:59:59+00:00)` é chamada  
**Então** retorna `distance_km == 25.0` e `date` correspondente a `2024-08-01` (a de `42000` em 2023 fica fora do intervalo)

#### CN-2: Sem filtro temporal — comportamento inalterado (SPEC-007/008)
**Dado** que o usuário tem 3 atividades do tipo `"Run"` com `distance_meters` de `5000`, `21097` e `10000`  
**Quando** a tool `get_longest_run(user_id)` é chamada (sem `start_date` nem `end_date`)  
**Então** retorna `distance_km == 21.097`

#### CN-3: Apenas `start_date` — sem limite superior
**Dado** que o usuário tem 2 atividades do tipo `"Run"`:  
- `start_date = 2023-06-01T08:00:00+00:00`, `distance_meters = 30000`  
- `start_date = 2024-06-01T08:00:00+00:00`, `distance_meters = 10000`  
**Quando** a tool `get_longest_run(user_id, start_date=2024-01-01T00:00:00+00:00)` é chamada  
**Então** retorna `distance_km == 10.0` (atividade de `2024-06-01`)

#### CN-4: Apenas `end_date` — sem limite inferior
**Dado** que o usuário tem 2 atividades do tipo `"Ride"`:  
- `start_date = 2023-06-01T08:00:00+00:00`, `distance_meters = 80000`  
- `start_date = 2024-06-01T08:00:00+00:00`, `distance_meters = 120000`  
**Quando** a tool `get_longest_ride(user_id, end_date=2023-12-31T23:59:59+00:00)` é chamada  
**Então** retorna `distance_km == 80.0` (atividade de `2023-06-01`)

### Casos de borda (Edge Cases)

#### CB-1: Atividade exatamente na fronteira do intervalo
**Dado** que o usuário tem 1 atividade do tipo `"Run"` com `start_date = 2024-06-01T08:00:00+00:00` e `distance_meters = 10000`  
**Quando** a tool `get_longest_run(user_id, start_date=2024-06-01T08:00:00+00:00, end_date=2024-06-01T08:00:00+00:00)` é chamada  
**Então** retorna `distance_km == 10.0` (fronteiras inclusivas)

#### CB-2: Atividades no intervalo mas nenhuma do tipo correto
**Dado** que o usuário tem atividades do tipo `"Ride"` dentro do intervalo, mas nenhuma `"Run"`  
**Quando** a tool `get_longest_run(user_id, start_date=2024-01-01T00:00:00+00:00, end_date=2024-12-31T23:59:59+00:00)` é chamada  
**Então** retorna todos os campos `null`

#### CB-3: Empate de distância dentro do intervalo
**Dado** que o usuário tem 2 atividades do tipo `"Run"` com `distance_meters = 10000`, ambas dentro do intervalo, uma com `start_date = 2024-06-01T08:00:00+00:00` e outra com `start_date = 2024-09-15T07:30:00+00:00`  
**Quando** a tool `get_longest_run(user_id, start_date=2024-01-01T00:00:00+00:00, end_date=2024-12-31T23:59:59+00:00)` é chamada  
**Então** retorna a corrida de `2024-09-15` (mais recente por `start_date`)

### Casos de erro

#### CE-1: Nenhuma atividade no intervalo
**Dado** que o usuário tem atividades do tipo `"Run"`, mas todas com `start_date` anterior a `2024-01-01`  
**Quando** a tool `get_longest_run(user_id, start_date=2024-01-01T00:00:00+00:00, end_date=2024-12-31T23:59:59+00:00)` é chamada  
**Então** retorna todos os campos `null` (não lança exceção)

#### CE-2: Intervalo inválido (`start_date > end_date`)
**Dado** que o usuário tem atividades do tipo `"Run"` no histórico  
**Quando** a tool `get_longest_run(user_id, start_date=2024-12-31T00:00:00+00:00, end_date=2024-01-01T00:00:00+00:00)` é chamada  
**Então** retorna todos os campos `null` (não lança exceção)

#### CE-3: `start_date` ou `end_date` malformados
**Dado** que `start_date` não é parseável como datetime ISO 8601 (ex.: `"not-a-date"`)  
**Quando** a tool `get_longest_run(user_id, start_date="not-a-date")` é chamada  
**Então** retorna erro de validação MCP (`ToolError`)

---

## Critérios de Aceite

- [ ] Spec com status **Draft** no repositório
- [ ] Tools `get_longest_run` e `get_longest_ride` aceitam `start_date`/`end_date` opcionais sem quebrar chamadas existentes
- [ ] Handlers delegam filtro temporal ao PREngine (SPEC-009)
- [ ] Descrições atualizadas com exemplos temporais; fronteiras Run/Ride preservadas
- [ ] Um teste unitário por CN/CB/CE temporal documentado (10 casos Run; subset crítico CN-1, CN-2, CE-1 espelhado para Ride)
- [ ] Testes existentes de SPEC-007/008 permanecem verdes sem alteração de asserções
- [ ] `test_server.py` verifica que descrições mencionam filtro temporal
- [ ] Cobertura `convertreino.mcp` >= 90%
- [ ] Cobertura Domain mantida >= 95%
- [ ] CI verde (ruff, mypy, pytest)
- [ ] Nenhuma migration ou env var nova
- [ ] Output schema inalterado (SPEC-007/008)
- [ ] Não contradiz SPEC-001, SPEC-007, SPEC-008 nem SPEC-009

---

## Mapeamento Spec → Testes

| Artefato                                   | Localização                                               |
|--------------------------------------------|-----------------------------------------------------------|
| CN/CB/CE temporais (`Run`)                 | `backend/tests/unit/mcp/test_get_longest_run_tool.py`     |
| Subset crítico temporais (`Ride`)          | `backend/tests/unit/mcp/test_get_longest_ride_tool.py`    |
| Descrições temporais (registro)            | `backend/tests/unit/mcp/test_server.py`                   |
| Retrocompatibilidade (sem filtro)          | testes existentes CN/CB/CE de SPEC-007/008                |
| Integração smoke (opcional)                | `backend/tests/integration/test_mcp_get_longest_*.py`     |

Padrão AAA obrigatório (guia seção 6). Reutilizar `build_activity` de `backend/tests/builders/__init__.py`. Testes temporais devem usar `start_date` timezone-aware (consistente com `Activity.__post_init__`). Testes de Ride devem passar `activity_type="Ride"` explicitamente.

Helper de teste a estender:

```python
async def _call_get_longest_run(
    user_id,
    *,
    start_date: datetime | None = None,
    end_date: datetime | None = None,
) -> LongestRunResult:
    payload: dict[str, str] = {"user_id": str(user_id)}
    if start_date is not None:
        payload["start_date"] = start_date.isoformat()
    if end_date is not None:
        payload["end_date"] = end_date.isoformat()
    server = create_mcp_server()
    async with Client(server) as client:
        result = await client.call_tool("get_longest_run", payload)
    return LongestRunResult.model_validate(result.data)
```

Exemplo derivado do guia:

```python
@pytest.mark.anyio
async def test_get_longest_run_returns_max_distance_within_date_range():
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
            distance_meters=15000,
            start_date=datetime(2024, 3, 1, 8, 0, 0, tzinfo=UTC),
        ),
        build_activity(
            user_id=user_id,
            distance_meters=25000,
            start_date=datetime(2024, 8, 1, 8, 0, 0, tzinfo=UTC),
        ),
    ]
    _configure_engine(activities)

    # Act
    result = await _call_get_longest_run(
        user_id,
        start_date=datetime(2024, 1, 1, 0, 0, 0, tzinfo=UTC),
        end_date=datetime(2024, 12, 31, 23, 59, 59, tzinfo=UTC),
    )

    # Assert
    assert result.distance_km == 25.0
    assert result.activity_id is not None
    assert result.date is not None
```

---

## Decisões de Design

### Decisão: ISO dates + descrições LLM (sem resolver server-side)
**Contexto:** SPEC-009 deixou períodos nomeados para a camada MCP; Domain aceita apenas intervalo livre (`start_date`/`end_date`).  
**Opção escolhida:** Expor parâmetros opcionais ISO 8601 na MCP e orientar o LLM via descrições com tabela de conversão intenção → parâmetros.  
**Alternativas rejeitadas:** Utilitário `period_resolver.py` no servidor; enum de períodos nomeados na tool.  
**Motivo:** Escopo POC alinhado ao roadmap da SPEC-009; Domain permanece primitivo; evita duplicar lógica de calendário/fuso na MCP.

### Decisão: Keyword-only params
**Contexto:** Assinatura evolui de `(user_id)` para `(user_id, start_date?, end_date?)`.  
**Opção escolhida:** `*, start_date=None, end_date=None` após `user_id`.  
**Alternativas rejeitadas:** Parâmetros posicionais opcionais.  
**Motivo:** Consistente com SPEC-009; evita quebra silenciosa em evoluções futuras.

### Decisão: Output schema inalterado
**Contexto:** Filtro temporal não altera quais campos o LLM recebe.  
**Opção escolhida:** `LongestRunResult` e `LongestRideResult` permanecem idênticos à SPEC-007/008.  
**Alternativas rejeitadas:** Adicionar campos `period_start`/`period_end` no output.  
**Motivo:** Intervalo é input; output descreve a atividade vencedora, não o filtro aplicado.

### Decisão: Validação em duas camadas
**Contexto:** Erros de input temporal podem ser de formato ou de coerência semântica.  
**Opção escolhida:** Formato inválido → erro MCP (`ToolError`); intervalo incoerente (`start > end`) → PREngine retorna `None` → campos `null`.  
**Alternativas rejeitadas:** Validar `start > end` na MCP com exceção.  
**Motivo:** Alinhado à SPEC-009 ("ausência de dados = None"); MCP não duplica regra de negócio do Domain.

### Decisão: Simetria Run/Ride
**Contexto:** Ambas as tools ganham os mesmos parâmetros temporais.  
**Opção escolhida:** Mesmos parâmetros e orientações temporais; métricas derivadas (pace vs speed) inalteradas.  
**Alternativas rejeitadas:** Filtro temporal apenas em `get_longest_run`.  
**Motivo:** SPEC-009 implementou filtro em ambos; perguntas temporais existem para corrida e pedal.

### Decisão: Sem helper genérico MCP
**Contexto:** Handlers de Run e Ride terão assinaturas quase idênticas.  
**Opção escolhida:** Funções separadas (`get_longest_run`, `get_longest_ride`) sem extrair helper genérico.  
**Alternativas rejeitadas:** Handler único `_get_longest(user_id, activity_type, ...)`.  
**Motivo:** Consistente com SPEC-008; DRY prematuro com apenas 2 tools.

### Decisão: Delegação direta ao PREngine
**Contexto:** MCP não deve reimplementar filtro temporal.  
**Opção escolhida:** Handlers repassam `start_date`/`end_date` ao PREngine sem lógica adicional.  
**Alternativas rejeitadas:** Filtrar atividades na camada MCP antes de chamar o engine.  
**Motivo:** Regra de negócio pertence ao Domain (SPEC-009); MCP é adaptador LLM-friendly.

---

## Notas de Migração

- Nenhuma dependência nova (`fastmcp` já adicionada na SPEC-007)
- Nenhuma migration de banco
- Nenhuma variável de ambiente nova
- Retrocompatível: chamadas existentes sem `start_date`/`end_date` mantêm comportamento SPEC-007/008
- Rollback: reverter assinaturas e descrições em `tools/pr.py` e `server.py`; remover testes temporais — sem impacto em dados

---

## Roadmap pós-SPEC-010

| Spec futura provável | Conteúdo                                                    |
|----------------------|-------------------------------------------------------------|
| SPEC-011+            | Volume Engine, resolver determinístico de períodos (se necessário), API de chat, auth JWT |

---

## Checklist de revisão (seção 12 do guia)

### Clareza
- [ ] O contexto explica o problema sem descrever a solução?
- [ ] O contrato tem tipos explícitos para todos os inputs e outputs?
- [ ] Cada comportamento tem "Dado / Quando / Então" completo?
- [ ] Os critérios de aceite são binários e verificáveis?

### Completude
- [ ] Há ao menos um caso normal (CN-1 a CN-4)?
- [ ] Casos de borda cobertos (fronteira inclusiva, tipo errado, empate)?
- [ ] Casos de erro especificados com comportamento esperado (`null`, `ToolError`)?
- [ ] Escopo "Excluído" deixa claro o que ficou de fora?

### Consistência
- [ ] Não contradiz SPEC-001, SPEC-007, SPEC-008 nem SPEC-009?
- [ ] Nomes de tipos alinhados ao código existente?
- [ ] MCP delega ao Domain; não reimplementa regra de negócio?

### Testabilidade
- [ ] Cada comportamento mapeia para teste unitário com `InMemoryActivityRepository`?
- [ ] Comportamentos determinísticos (mesmo input → mesmo output)?
- [ ] Efeitos colaterais explicitados (nenhum) e testáveis?
