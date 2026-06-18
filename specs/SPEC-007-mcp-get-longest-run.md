# SPEC-007 — MCP: scaffold + tool `get_longest_run`

| Campo          | Valor                                              |
|----------------|----------------------------------------------------|
| **Status**     | Aprovada                                           |
| **Autor**      | @convertreino                                      |
| **Revisor**    | —                                                  |
| **Criada em**  | 2026-06-18                                         |
| **Camada**     | MCP                                                |
| **Depende de** | SPEC-001, SPEC-003, SPEC-005                       |
| **Bloqueia**   | SPEC-008 (`get_longest_ride`), API de chat          |
| **Épico**      | PR / Conversacional                                |

---

## Contexto

Com o PREngine já calculando a corrida mais longa de forma determinística (SPEC-005), o usuário pode perguntar *"qual foi minha corrida mais longa?"* via chat. O LLM precisa de uma ferramenta MCP com contrato explícito para delegar esse cálculo — sem inferir distâncias nem escolher a atividade vencedora. Esta spec introduz o scaffold do servidor MCP do ConverTreino e a primeira tool analítica: `get_longest_run`.

---

## Escopo

### Incluído

- Pacote `convertreino/mcp/` com servidor FastMCP
- Dois transportes:
  - **stdio** — entrypoint CLI (`python -m convertreino.mcp`) para dev local (Cursor/Claude Desktop)
  - **HTTP/SSE** — montado no FastAPI existente em `/mcp`
- Tool `get_longest_run` delegando a `PREngine.get_longest_run`
- Schema de output LLM-friendly (`LongestRunResult`) — não expor entidade `Activity` crua
- Mapper `Activity | None` → `LongestRunResult`
- Testes unitários + integração do handler MCP
- Cobertura mínima MCP: 90% (guia seção 8)

### Excluído (explicitamente fora desta spec)

- Tool `get_longest_ride` → SPEC-008
- Endpoint REST dedicado (`GET /users/{id}/prs/longest-run`)
- Auth JWT / injeção automática de `user_id` via sessão (spec futura de auth)
- Chat orchestrator / API de mensagens
- Testes E2E com LLM real
- Cache Redis
- Application Service intermediário (`PrQueryService`)

---

## Contrato — MCP Tool

### Nome

`get_longest_run`

### Descrição para o LLM

Retorna a corrida (`Run`) com maior distância do usuário. Use quando o usuário perguntar sobre sua corrida mais longa, maior distância correndo, ou recorde de corrida. **NÃO** use para pedais/ciclismo (`get_longest_ride`), natação, pace médio geral, volume semanal ou elevação.

### Perguntas que DEVEM acionar esta tool

- "Qual foi minha corrida mais longa?"
- "Qual meu recorde de corrida em km?"
- "Qual a maior distância que já corri?"

### Perguntas que NÃO devem acionar esta tool

- "Qual foi meu pedal mais longo?" → `get_longest_ride` (SPEC-008)
- "Quanto corri essa semana?" → volume engine (futuro)
- "Qual meu pace médio?" → engine de pace (futuro)

### Input schema

| Campo     | Tipo         | Obrigatório | Descrição                                                                 |
|-----------|--------------|-------------|---------------------------------------------------------------------------|
| `user_id` | `str` (UUID) | Sim         | ID interno do usuário. Na POC, passado pelo orchestrator de chat (pós-OAuth SPEC-002). O LLM **não** deve inferir este valor. |

### Output schema

```python
class LongestRunResult(BaseModel):
    activity_id: str | None
    distance_km: float | None
    date: str | None              # ISO 8601 UTC
    duration_minutes: float | None
    average_pace_min_per_km: float | None  # null se distance_km == 0
```

### Regras de mapeamento (`Activity` → `LongestRunResult`)

| Campo Activity         | Campo output              | Transformação                                                          |
|------------------------|---------------------------|------------------------------------------------------------------------|
| `id`                   | `activity_id`             | `str(id)`                                                              |
| `distance_meters`      | `distance_km`             | `round(m / 1000, 3)`                                                     |
| `start_date`           | `date`                    | `.isoformat()`                                                         |
| `elapsed_time_seconds` | `duration_minutes`        | `round(s / 60, 1)`                                                       |
| calculado              | `average_pace_min_per_km` | `(elapsed_s / 60) / (distance_m / 1000)`, 2 casas; `null` se distância 0 |

Quando `PREngine.get_longest_run` retorna `None`: retornar `LongestRunResult` com todos os campos `null` (resposta válida, sem exceção MCP).

### Efeitos colaterais

Nenhum. Operação somente leitura via `PREngine` → `ActivityRepository.get_all`.

---

## Comportamentos

### Casos normais (Happy Path)

#### CN-1: Usuário tem múltiplas corridas
**Dado** que o usuário tem 3 atividades do tipo `"Run"` com `distance_meters` de `5000`, `21097` e `10000`  
**Quando** a tool `get_longest_run(user_id)` é chamada  
**Então** retorna `distance_km == 21.097`, `activity_id` preenchido e demais campos calculados

#### CN-2: Usuário tem apenas uma corrida
**Dado** que o usuário tem exatamente 1 atividade do tipo `"Run"` com `distance_meters = 8420`  
**Quando** a tool `get_longest_run(user_id)` é chamada  
**Então** retorna `distance_km == 8.42` e dados dessa atividade

### Casos de borda (Edge Cases)

#### CB-1: Usuário tem atividades mas nenhuma é corrida
**Dado** que o usuário tem atividades do tipo `"Ride"` e `"Swim"`, sem nenhuma `"Run"`  
**Quando** a tool `get_longest_run(user_id)` é chamada  
**Então** retorna todos os campos `null`

#### CB-2: Duas corridas com distância idêntica
**Dado** que o usuário tem 2 atividades do tipo `"Run"` com `distance_meters = 10000`, uma com `start_date = 2024-06-01T08:00:00+00:00` e outra com `start_date = 2024-09-15T07:30:00+00:00`  
**Quando** a tool `get_longest_run(user_id)` é chamada  
**Então** retorna a corrida de `2024-09-15` (mais recente por `start_date`)

#### CB-3: Mix Run + Ride; Ride tem distância maior
**Dado** que o usuário tem uma corrida `"Run"` com `distance_meters = 10000` e um pedal `"Ride"` com `distance_meters = 85000`  
**Quando** a tool `get_longest_run(user_id)` é chamada  
**Então** retorna a corrida com `distance_km == 10.0` (filtro por tipo, não distância global)

### Casos de erro

#### CE-1: Usuário sem atividades
**Dado** que o usuário não tem nenhuma atividade registrada  
**Quando** a tool `get_longest_run(user_id)` é chamada  
**Então** retorna todos os campos `null` (não lança exceção)

#### CE-2: user_id sem registros no repositório
**Dado** que `user_id` não possui nenhuma atividade no repositório (decisão SPEC-001: `get_all` → `[]`)  
**Quando** a tool `get_longest_run(user_id)` é chamada  
**Então** retorna todos os campos `null` (não lança exceção)

#### CE-3: user_id inválido (não-UUID)
**Dado** que `user_id` não é um UUID válido  
**Quando** a tool `get_longest_run(user_id)` é chamada  
**Então** retorna erro de validação MCP (input inválido)

---

## Critérios de Aceite

- [x] Spec com status **Aprovada** no repositório
- [x] Servidor MCP sobe via `uv run python -m convertreino.mcp` (stdio)
- [x] Endpoint `/mcp` responde no FastAPI (HTTP/SSE)
- [x] Tool `get_longest_run` registrada com descrição e fronteiras Run vs Ride
- [x] Um teste por CN/CB/CE + contrato de schema
- [x] Cobertura `convertreino.mcp` >= 90%
- [x] Cobertura Domain mantida >= 95%
- [x] CI verde (ruff, mypy, pytest)
- [x] Nenhuma migration ou env var nova

---

## Mapeamento Spec → Testes

| Artefato                                   | Localização                                               |
|--------------------------------------------|-----------------------------------------------------------|
| Mapper (arredondamento, pace null)         | `backend/tests/unit/mcp/test_mappers.py`                  |
| CN/CB/CE da tool                           | `backend/tests/unit/mcp/test_get_longest_run_tool.py`     |
| Registro da tool (nome, descrição)         | `backend/tests/unit/mcp/test_server.py`                   |
| Integração HTTP/SSE (smoke)                | `backend/tests/integration/test_mcp_get_longest_run.py`   |

Padrão AAA obrigatório (guia seção 6). Reutilizar `build_activity` de `backend/tests/builders/__init__.py`.

---

## Decisões de Design

### Decisão: Framework MCP — FastMCP
**Contexto:** Primeiro servidor MCP do projeto; precisa de tools explícitas, não espelhar rotas REST.  
**Opção escolhida:** FastMCP com decorators `@mcp.tool()`.  
**Alternativas rejeitadas:** `fastapi-mcp` (auto-expor rotas REST — não há rota REST de PR).  
**Motivo:** Controle do contrato LLM; padrão estabelecido para SPEC-008.

### Decisão: Transporte duplo (stdio + HTTP/SSE)
**Contexto:** Dev local usa Cursor/Claude Desktop (stdio); app mobile precisa de backend HTTP.  
**Opção escolhida:** stdio via `__main__.py` + mount HTTP/SSE em `/mcp` no FastAPI.  
**Alternativas rejeitadas:** Apenas um transporte.  
**Motivo:** Flexibilidade POC sem dois deploys.

### Decisão: Tool → PREngine direto (sem Application Service)
**Contexto:** Uma tool, uma chamada de domínio.  
**Opção escolhida:** Handler MCP instancia `PREngine` e delega.  
**Alternativas rejeitadas:** `PrQueryService` intermediário.  
**Motivo:** Over-engineering para escopo atual; Application Service entra quando houver cache/coordenação.

### Decisão: Ausência de dados → JSON com campos `null`
**Contexto:** Usuário sem corridas.  
**Opção escolhida:** `LongestRunResult` com todos os campos `null`.  
**Alternativas rejeitadas:** Exceção MCP ou `{ "error": "..." }`.  
**Motivo:** Zero é resposta válida; LLM formata mensagem amigável.

### Decisão: `user_id` explícito na POC
**Contexto:** SPEC-002 retorna `user_id` no callback OAuth; JWT fora de escopo.  
**Opção escolhida:** Parâmetro obrigatório `user_id` injetado pelo orchestrator de chat.  
**Alternativas rejeitadas:** Injeção via JWT/sessão.  
**Motivo:** Consistência com POC; auth de usuário final é spec futura.

### Decisão: Pace calculado no mapper MCP
**Contexto:** PREngine retorna `Activity` sem pace derivado.  
**Opção escolhida:** `average_pace_min_per_km` calculado em `mappers.py`.  
**Alternativas rejeitadas:** Estender PREngine com pace.  
**Motivo:** Formatação para LLM é responsabilidade da camada MCP; Domain permanece agnóstico.

---

## Notas de Migração

- Dependência nova: `fastmcp` em `pyproject.toml`
- Nenhuma migration de banco
- Nenhuma variável de ambiente nova
- Rollback: remover pacote `convertreino/mcp/` e mount em `main.py`

---

## Roadmap pós-SPEC-007

| Spec futura provável | Conteúdo                                                    |
|----------------------|-------------------------------------------------------------|
| SPEC-008             | MCP tool `get_longest_ride` (replica padrão da 007)         |
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
- [x] Casos de borda cobertos (sem Run, empate, mix de tipos)?
- [x] Casos de erro especificados com comportamento esperado?
- [x] Escopo "Excluído" deixa claro o que ficou de fora?

### Consistência
- [x] Não contradiz SPEC-001, SPEC-003 nem SPEC-005?
- [x] Nomes de tipos alinhados ao código existente?
- [x] MCP delega ao Domain; não reimplementa regra de negócio?

### Testabilidade
- [x] Cada comportamento mapeia para teste unitário?
- [x] Comportamentos determinísticos (mesmo input → mesmo output)?
- [x] Efeitos colaterais explicitados (nenhum) e testáveis?
