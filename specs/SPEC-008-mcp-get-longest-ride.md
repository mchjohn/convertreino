# SPEC-008 — MCP: tool `get_longest_ride`

| Campo          | Valor                                              |
|----------------|----------------------------------------------------|
| **Status**     | Aprovada                                           |
| **Autor**      | @convertreino                                      |
| **Revisor**    | —                                                  |
| **Criada em**  | 2026-06-18                                         |
| **Camada**     | MCP                                                |
| **Depende de** | SPEC-001, SPEC-003, SPEC-006, SPEC-007             |
| **Bloqueia**   | API de chat, filtro temporal (SPEC-009)            |
| **Épico**      | PR / Conversacional                                |

---

## Contexto

Com o PREngine já calculando o pedal mais longo de forma determinística (SPEC-006) e o servidor MCP estabelecido com `get_longest_run` (SPEC-007), o usuário pode perguntar *"qual foi meu pedal mais longo?"* via chat. O LLM precisa de uma ferramenta MCP complementar com contrato explícito para delegar esse cálculo — sem inferir distâncias nem escolher a atividade vencedora. Esta spec adiciona a tool analítica `get_longest_ride`, completando o par Run/Ride na camada MCP.

---

## Escopo

### Incluído

- Tool `get_longest_ride` delegando a `PREngine.get_longest_ride`
- Registro da tool no servidor MCP existente (stdio + HTTP/SSE em `/mcp`)
- Schema de output LLM-friendly (`LongestRideResult`) — não expor entidade `Activity` crua
- Mapper `Activity | None` → `LongestRideResult` com `average_speed_kmh`
- Testes unitários + integração do handler MCP
- Cobertura mínima MCP: 90% (guia seção 8)

### Excluído (explicitamente fora desta spec)

- Alterações no PREngine ou Domain (já coberto pela SPEC-006)
- Scaffold MCP, novos transportes ou dependências
- Endpoint REST dedicado (`GET /users/{id}/prs/longest-ride`)
- Auth JWT / injeção automática de `user_id` via sessão (spec futura de auth)
- Chat orchestrator / API de mensagens
- Testes E2E com LLM real
- `VirtualRide`, `EBikeRide` e outros subtipos Strava (permanece literal `"Ride"`)
- Cache Redis
- Application Service intermediário (`PrQueryService`)

---

## Contrato — MCP Tool

### Nome

`get_longest_ride`

### Descrição para o LLM

Retorna o pedal (`Ride`) com maior distância do usuário. Use quando o usuário perguntar sobre seu pedal mais longo, maior distância pedalando, ou recorde de ciclismo. **NÃO** use para corridas (`get_longest_run`), natação, volume semanal ou elevação.

### Perguntas que DEVEM acionar esta tool

- "Qual foi meu pedal mais longo?"
- "Qual meu recorde de pedal em km?"
- "Qual a maior distância que já pedalei?"

### Perguntas que NÃO devem acionar esta tool

- "Qual foi minha corrida mais longa?" → `get_longest_run`
- "Quanto pedalei essa semana?" → volume engine (futuro)
- "Qual minha velocidade média geral?" → engine de velocidade (futuro)

### Input schema

| Campo     | Tipo         | Obrigatório | Descrição                                                                 |
|-----------|--------------|-------------|---------------------------------------------------------------------------|
| `user_id` | `str` (UUID) | Sim         | ID interno do usuário. Na POC, passado pelo orchestrator de chat (pós-OAuth SPEC-002). O LLM **não** deve inferir este valor. |

### Output schema

```python
class LongestRideResult(BaseModel):
    activity_id: str | None
    distance_km: float | None
    date: str | None              # ISO 8601 UTC
    duration_minutes: float | None
    average_speed_kmh: float | None  # null se distance_km == 0
```

### Regras de mapeamento (`Activity` → `LongestRideResult`)

| Campo Activity         | Campo output        | Transformação                                                          |
|------------------------|---------------------|------------------------------------------------------------------------|
| `id`                   | `activity_id`       | `str(id)`                                                              |
| `distance_meters`      | `distance_km`       | `round(m / 1000, 3)`                                                   |
| `start_date`           | `date`              | `.isoformat()`                                                         |
| `elapsed_time_seconds` | `duration_minutes`  | `round(s / 60, 1)`                                                     |
| calculado              | `average_speed_kmh` | `round(distance_km / (duration_minutes / 60), 2)`; `null` se distância 0 |

Quando `PREngine.get_longest_ride` retorna `None`: retornar `LongestRideResult` com todos os campos `null` (resposta válida, sem exceção MCP).

### Efeitos colaterais

Nenhum. Operação somente leitura via `PREngine` → `ActivityRepository.get_all`.

---

## Comportamentos

### Casos normais (Happy Path)

#### CN-1: Usuário tem múltiplos pedais
**Dado** que o usuário tem 3 atividades do tipo `"Ride"` com `distance_meters` de `30000`, `120000` e `80000`  
**Quando** a tool `get_longest_ride(user_id)` é chamada  
**Então** retorna `distance_km == 120.0`, `activity_id` preenchido e demais campos calculados

#### CN-2: Usuário tem apenas um pedal
**Dado** que o usuário tem exatamente 1 atividade do tipo `"Ride"` com `distance_meters = 65000`  
**Quando** a tool `get_longest_ride(user_id)` é chamada  
**Então** retorna `distance_km == 65.0` e dados dessa atividade

### Casos de borda (Edge Cases)

#### CB-1: Usuário tem atividades mas nenhuma é pedal
**Dado** que o usuário tem atividades do tipo `"Run"` e `"Swim"`, sem nenhuma `"Ride"`  
**Quando** a tool `get_longest_ride(user_id)` é chamada  
**Então** retorna todos os campos `null`

#### CB-2: Dois pedais com distância idêntica
**Dado** que o usuário tem 2 atividades do tipo `"Ride"` com `distance_meters = 80000`, uma com `start_date = 2024-06-01T08:00:00+00:00` e outra com `start_date = 2024-09-15T07:30:00+00:00`  
**Quando** a tool `get_longest_ride(user_id)` é chamada  
**Então** retorna o pedal de `2024-09-15` (mais recente por `start_date`)

#### CB-3: Mix Ride + Run; Run tem distância maior
**Dado** que o usuário tem um pedal `"Ride"` com `distance_meters = 50000` e uma corrida `"Run"` com `distance_meters = 42195`  
**Quando** a tool `get_longest_ride(user_id)` é chamada  
**Então** retorna o pedal com `distance_km == 50.0` (filtro por tipo, não distância global)

#### CB-4: Pedal com distância zero
**Dado** que o usuário tem uma atividade do tipo `"Ride"` com `distance_meters = 0` e `elapsed_time_seconds = 600`  
**Quando** a tool `get_longest_ride(user_id)` é chamada  
**Então** retorna `distance_km == 0.0` e `average_speed_kmh is None`

### Casos de erro

#### CE-1: Usuário sem atividades
**Dado** que o usuário não tem nenhuma atividade registrada  
**Quando** a tool `get_longest_ride(user_id)` é chamada  
**Então** retorna todos os campos `null` (não lança exceção)

#### CE-2: user_id sem registros no repositório
**Dado** que `user_id` não possui nenhuma atividade no repositório (decisão SPEC-001: `get_all` → `[]`)  
**Quando** a tool `get_longest_ride(user_id)` é chamada  
**Então** retorna todos os campos `null` (não lança exceção)

#### CE-3: user_id inválido (não-UUID)
**Dado** que `user_id` não é um UUID válido  
**Quando** a tool `get_longest_ride(user_id)` é chamada  
**Então** retorna erro de validação MCP (input inválido)

---

## Critérios de Aceite

- [ ] Spec com status **Aprovada** no repositório
- [ ] Tool `get_longest_ride` registrada no servidor MCP existente (stdio + HTTP/SSE)
- [ ] Descrição da tool com fronteiras Ride vs Run (menciona `get_longest_run`)
- [ ] Descrição de `get_longest_run` continua mencionando `get_longest_ride`
- [ ] Um teste por CN/CB/CE + contrato de schema
- [ ] Cobertura `convertreino.mcp` >= 90%
- [ ] Cobertura Domain mantida >= 95%
- [ ] CI verde (ruff, mypy, pytest)
- [ ] Nenhuma migration ou env var nova

---

## Mapeamento Spec → Testes

| Artefato                                   | Localização                                                |
|--------------------------------------------|------------------------------------------------------------|
| Mapper (arredondamento, speed null)        | `backend/tests/unit/mcp/test_mappers.py`                   |
| CN/CB/CE da tool                           | `backend/tests/unit/mcp/test_get_longest_ride_tool.py`     |
| Registro da tool (nome, descrição)         | `backend/tests/unit/mcp/test_server.py`                    |
| Integração HTTP/SSE (smoke)                | `backend/tests/integration/test_mcp_get_longest_ride.py` |

Padrão AAA obrigatório (guia seção 6). Reutilizar `build_activity` de `backend/tests/builders/__init__.py` — passar `activity_type="Ride"` explicitamente.

Exemplo derivado do guia:

```python
def test_activity_to_longest_ride_result_maps_average_speed():
    # Arrange
    activity = build_activity(
        activity_type="Ride",
        distance_meters=120000,
        elapsed_time_seconds=14400,
    )

    # Act
    result = activity_to_longest_ride_result(activity)

    # Assert
    assert result.distance_km == 120.0
    assert result.average_speed_kmh == 30.0
```

---

## Decisões de Design

### Decisão: Simetria com SPEC-007, exceto métrica derivada
**Contexto:** `get_longest_ride` replica o padrão de `get_longest_run`; output precisa ser útil para o LLM em contexto de ciclismo.  
**Opção escolhida:** Mesma estrutura de campos que `LongestRunResult`, com `average_speed_kmh` em vez de `average_pace_min_per_km`.  
**Alternativas rejeitadas:** Espelhar `average_pace_min_per_km` (semântica estranha para ciclismo); incluir ambas as métricas.  
**Motivo:** Velocidade em km/h é a métrica natural para pedais; evita confusão do LLM ao responder perguntas de ciclismo.

### Decisão: Sem refactor compartilhado
**Contexto:** Mapper e handler de Ride terão lógica quase idêntica aos de Run.  
**Opção escolhida:** Funções separadas (`activity_to_longest_ride_result`, `get_longest_ride`) sem extrair helper genérico.  
**Alternativas rejeitadas:** Mapper genérico `_activity_to_longest_result(activity, metric=...)`.  
**Motivo:** Alinhado à decisão da SPEC-006 de não extrair `_get_longest_by_type`; DRY prematuro com apenas 2 tipos.

### Decisão: Tool → PREngine direto (sem Application Service)
**Contexto:** Uma tool, uma chamada de domínio — mesmo padrão da SPEC-007.  
**Opção escolhida:** Handler MCP instancia `PREngine` e delega a `get_longest_ride`.  
**Alternativas rejeitadas:** `PrQueryService` intermediário.  
**Motivo:** Over-engineering para escopo atual; Application Service entra quando houver cache/coordenação.

### Decisão: Ausência de dados → JSON com campos `null`
**Contexto:** Usuário sem pedais.  
**Opção escolhida:** `LongestRideResult` com todos os campos `null`.  
**Alternativas rejeitadas:** Exceção MCP ou `{ "error": "..." }`.  
**Motivo:** Zero é resposta válida; LLM formata mensagem amigável — consistente com SPEC-007.

### Decisão: `user_id` explícito na POC
**Contexto:** SPEC-002 retorna `user_id` no callback OAuth; JWT fora de escopo.  
**Opção escolhida:** Parâmetro obrigatório `user_id` injetado pelo orchestrator de chat.  
**Alternativas rejeitadas:** Injeção via JWT/sessão.  
**Motivo:** Consistência com SPEC-007; auth de usuário final é spec futura.

### Decisão: Velocidade calculada no mapper MCP
**Contexto:** PREngine retorna `Activity` sem velocidade derivada.  
**Opção escolhida:** `average_speed_kmh` calculado em `mappers.py`.  
**Alternativas rejeitadas:** Estender PREngine com velocidade.  
**Motivo:** Formatação para LLM é responsabilidade da camada MCP; Domain permanece agnóstico.

### Decisão: Filtro literal `"Ride"`
**Contexto:** Strava distingue `Ride`, `VirtualRide`, `EBikeRide`, etc.  
**Opção escolhida:** Delegar filtro ao PREngine (match exato `activity_type == "Ride"`).  
**Alternativas rejeitadas:** Agrupar subtipos no mapper MCP.  
**Motivo:** Consistente com SPEC-006; agrupamento de subtipos é spec futura se necessário.

---

## Notas de Migração

- Nenhuma dependência nova (`fastmcp` já adicionada na SPEC-007)
- Nenhuma migration de banco
- Nenhuma variável de ambiente nova
- Rollback: remover tool, schema, mapper e testes — sem impacto em dados

---

## Roadmap pós-SPEC-008

| Spec futura provável | Conteúdo                                                    |
|----------------------|-------------------------------------------------------------|
| SPEC-009             | Filtro temporal nos engines PR (SPEC-005/006)               |
| SPEC-010+            | Volume Engine, API de chat, auth JWT                        |

---

## Checklist de revisão (seção 12 do guia)

### Clareza
- [x] O contexto explica o problema sem descrever a solução?
- [x] O contrato tem tipos explícitos para todos os inputs e outputs?
- [x] Cada comportamento tem "Dado / Quando / Então" completo?
- [x] Os critérios de aceite são binários e verificáveis?

### Completude
- [x] Há ao menos um caso normal (CN-1, CN-2)?
- [x] Casos de borda cobertos (sem Ride, empate, mix de tipos, distância zero)?
- [x] Casos de erro especificados com comportamento esperado?
- [x] Escopo "Excluído" deixa claro o que ficou de fora?

### Consistência
- [x] Não contradiz SPEC-001, SPEC-003, SPEC-006 nem SPEC-007?
- [x] Nomes de tipos alinhados ao código existente?
- [x] MCP delega ao Domain; não reimplementa regra de negócio?

### Testabilidade
- [x] Cada comportamento mapeia para teste unitário?
- [x] Comportamentos determinísticos (mesmo input → mesmo output)?
- [x] Efeitos colaterais explicitados (nenhum) e testáveis?
