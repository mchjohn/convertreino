# SPEC-014 — API de Chat: orchestrator, LLM e injeção de `user_id`

| Campo          | Valor                                              |
|----------------|----------------------------------------------------|
| **Status**     | Draft                                              |
| **Autor**      | @convertreino                                      |
| **Revisor**    | —                                                  |
| **Criada em**  | 2026-06-19                                         |
| **Camada**     | Application + API + Infra (config)                 |
| **Depende de** | SPEC-001, SPEC-003, SPEC-007–012, SPEC-013         |
| **Bloqueia**   | Testes E2E com LLM real (futuro), mobile chat UI   |
| **Épico**      | Conversacional                                     |

---

## Contexto

As specs MCP (SPEC-007 a SPEC-012) expõem quatro ferramentas analíticas (`get_longest_run`, `get_longest_ride`, `get_run_volume`, `get_ride_volume`) com descrições detalhadas para tool use do LLM. A SPEC-013 introduziu JWT Bearer para autenticar o app mobile, mas ainda não existe endpoint conversacional que una autenticação, orquestração LLM e execução determinística das tools.

O usuário precisa perguntar em linguagem natural — *"qual foi minha corrida mais longa?"*, *"quanto corri essa semana?"* — e receber respostas precisas. O ConverTreino delega cálculos a engines determinísticos; o LLM atua apenas no entendimento de intenção, seleção de ferramentas e formatação da resposta. Para isso, o sistema precisa de um orchestrator que chame o LLM, execute tools in-process com o `user_id` do JWT (sem expor esse valor ao modelo) e devolva a resposta final ao app.

---

## Escopo

### Incluído

- Endpoint `POST /chat/messages` autenticado via Bearer JWT (SPEC-013)
- `ChatOrchestrator` em `application/chat_orchestrator.py`:
  - Loop tool-use: LLM → tool call → resultado → LLM (máx. `CHAT_MAX_TOOL_ITERATIONS`, default `5`)
  - System prompt fixo em português do Brasil
- Abstração LLM provider-agnostic em `application/llm/`:
  - Protocolo `LLMClient` com `complete(messages, tools) -> LLMCompletion`
  - Tipos: `ChatMessage`, `ToolDefinition`, `ToolCall`, `LLMCompletion`
  - Implementação `OpenAILLMClient` via SDK oficial `openai`
  - `FakeLLMClient` para testes unitários e integração (sem chamada de rede)
- `ChatToolRegistry` em `application/chat_tools.py`:
  - Registra as 4 tools com schemas **sem** `user_id`
  - Executa in-process chamando funções de `mcp/tools/` com `user_id` injetado do JWT
  - Reutiliza descrições existentes (`GET_LONGEST_RUN_DESCRIPTION`, etc.)
  - Instancia `PREngine` / `VolumeEngine` com `ActivityRepository` da sessão DB
- Schemas API Pydantic em `api/schemas/chat.py`
- Rota `api/routes/chat.py` + registro em `api/main.py`
- Configuração em `infrastructure/config.py`:
  - `OPENAI_API_KEY` (obrigatória em runtime de produção)
  - `OPENAI_MODEL` (default: `gpt-4o-mini`)
  - `CHAT_MAX_TOOL_ITERATIONS` (default: `5`)
- Dependência FastAPI `get_chat_orchestrator()` em `api/dependencies.py` + override `set_chat_orchestrator_override`
- Exceções de domínio: `LLMProviderError`, `ChatProcessingError`
- Histórico multi-turn via `messages[]` no request body (cliente mantém histórico; servidor stateless)
- Testes unitários e de integração (TDD a partir dos comportamentos abaixo)
- Cobertura mínima Application: **80%** (guia seção 8)
- Cobertura mínima API Endpoints: **80%** (guia seção 8)
- Atualização de `backend/README.md` com env vars e exemplo curl

### Excluído (explicitamente fora desta spec)

- Streaming / SSE (resposta síncrona JSON apenas)
- Persistência de conversas (tabelas, histórico server-side)
- `period_resolver.py` server-side — LLM converte períodos via descrições das tools (padrão SPEC-010/012) → SPEC-016+
- Testes E2E com OpenAI real (CI usa `FakeLLMClient`)
- Auth em `/mcp` HTTP
- Alteração das MCP tools públicas em `/mcp` (continuam com `user_id` no schema para dev/stdio)
- Novos engines analíticos (pace, consistência, tendência)
- Rate limiting, retry com backoff, circuit breaker do provider
- Refresh token / logout (SPEC-013)
- Proteção de endpoints além de `/chat/messages`

---

## Contrato

### Tipos compartilhados (Application)

```python
# application/llm/types.py
from dataclasses import dataclass
from typing import Literal
from uuid import UUID

ChatRole = Literal["system", "user", "assistant", "tool"]

@dataclass(frozen=True, slots=True)
class ChatMessage:
    role: ChatRole
    content: str
    tool_call_id: str | None = None  # obrigatório quando role == "tool"

@dataclass(frozen=True, slots=True)
class ToolDefinition:
    name: str
    description: str
    parameters: dict  # JSON Schema (OpenAI function parameters)

@dataclass(frozen=True, slots=True)
class ToolCall:
    id: str
    name: str
    arguments: dict[str, object]

@dataclass(frozen=True, slots=True)
class LLMCompletion:
    message: ChatMessage | None          # resposta final quando sem tool calls
    tool_calls: tuple[ToolCall, ...]     # vazio quando resposta final
```

### `LLMClient` (protocolo)

```python
# application/llm/client.py
class LLMClient(Protocol):
    def complete(
        self,
        messages: list[ChatMessage],
        tools: list[ToolDefinition],
    ) -> LLMCompletion: ...
```

| Método     | Input                              | Output          | Erro                |
|------------|------------------------------------|-----------------|---------------------|
| `complete` | `messages`, `tools`                | `LLMCompletion` | `LLMProviderError`  |

`OpenAILLMClient` mapeia para OpenAI Chat Completions API com `tools` e `tool_choice: "auto"`.

`FakeLLMClient` aceita sequência pré-programada de `LLMCompletion` para testes determinísticos.

### `ChatToolRegistry`

```python
# application/chat_tools.py
class ChatToolRegistry:
    def __init__(self, activity_repo: ActivityRepository) -> None: ...

    def get_tool_definitions(self) -> list[ToolDefinition]: ...

    def execute(
        self,
        user_id: UUID,
        tool_name: str,
        arguments: dict[str, object],
    ) -> dict[str, object]: ...
```

| Método                 | Input                                    | Output              | Erro                      |
|------------------------|------------------------------------------|---------------------|---------------------------|
| `get_tool_definitions` | —                                        | `list[ToolDefinition]` sem `user_id` nos schemas | — |
| `execute`              | `user_id`, `tool_name`, `arguments`      | `dict` (JSON-serializável) | `ValueError` se tool desconhecida |

Tools registradas e parâmetros visíveis ao LLM:

| Tool               | Parâmetros no schema LLM                          |
|--------------------|---------------------------------------------------|
| `get_longest_run`  | `start_date?: string (ISO 8601)`, `end_date?: string (ISO 8601)` |
| `get_longest_ride` | `start_date?: string (ISO 8601)`, `end_date?: string (ISO 8601)` |
| `get_run_volume`   | `start_date?: string (ISO 8601)`, `end_date?: string (ISO 8601)` |
| `get_ride_volume`  | `start_date?: string (ISO 8601)`, `end_date?: string (ISO 8601)` |

`user_id` **não** aparece em nenhum schema enviado ao LLM. Descrições das tools reutilizam constantes de `mcp/tools/pr.py` e `mcp/tools/volume.py`.

### `ChatOrchestrator`

```python
# application/chat_orchestrator.py
@dataclass(frozen=True, slots=True)
class ChatResponse:
    message: ChatMessage
    tool_calls_made: tuple[str, ...]

class ChatOrchestrator:
    def __init__(
        self,
        llm_client: LLMClient,
        tool_registry: ChatToolRegistry,
        *,
        max_tool_iterations: int = 5,
        system_prompt: str = DEFAULT_SYSTEM_PROMPT,
    ) -> None: ...

    def handle(self, user_id: UUID, messages: list[ChatMessage]) -> ChatResponse: ...
```

| Método   | Input                         | Output         | Erro                    |
|----------|-------------------------------|----------------|-------------------------|
| `handle` | `user_id`, `messages` (sem system) | `ChatResponse` | `LLMProviderError`, `ChatProcessingError` |

**Fluxo interno de `handle`:**

1. Prefixar `messages` com system prompt (`role: "system"`)
2. Chamar `llm_client.complete(messages, tool_registry.get_tool_definitions())`
3. Se `LLMCompletion.tool_calls` não vazio:
   - Para cada `ToolCall`, executar `tool_registry.execute(user_id, name, arguments)`
   - Anexar mensagens `role: "tool"` com resultado JSON
   - Incrementar contador de iterações; repetir passo 2
4. Se `LLMCompletion.message` com `role: "assistant"` → retornar `ChatResponse`
5. Se iterações > `max_tool_iterations` sem resposta final → `ChatProcessingError`
6. Acumular nomes de tools executadas em `tool_calls_made` (ordem de execução)

### System prompt (`DEFAULT_SYSTEM_PROMPT`)

Conteúdo mínimo obrigatório:

- Você é o ConverTreino, assistente de performance esportiva para atletas com dados do Strava
- Responda sempre em português do Brasil
- Use as ferramentas disponíveis para obter dados analíticos; **nunca invente números**
- Se a ferramenta retornar dados vazios ou nulos, informe claramente que não há dados
- Diferencie recorde individual (`get_longest_run` / `get_longest_ride`) de volume agregado (`get_run_volume` / `get_ride_volume`)
- Diferencie corrida (`Run`) de pedal (`Ride`)
- Converta períodos mencionados pelo usuário em `start_date`/`end_date` ISO 8601 UTC ao chamar tools

### Configuração

| Variável                  | Obrigatória | Default (testes)   | Descrição                              |
|---------------------------|-------------|--------------------|----------------------------------------|
| `OPENAI_API_KEY`          | Sim*        | `"test-openai-key"`| Chave da API OpenAI                    |
| `OPENAI_MODEL`            | Não         | `gpt-4o-mini`      | Modelo para Chat Completions           |
| `CHAT_MAX_TOOL_ITERATIONS`| Não         | `5`                | Máximo de rodadas LLM↔tools por request |

\* Em runtime de produção, `OPENAI_API_KEY` vazio deve impedir construção do `OpenAILLMClient` (falha explícita).

### API — `POST /chat/messages`

| Método | Path              | Auth                    | Response 200    |
|--------|-------------------|-------------------------|-----------------|
| POST   | `/chat/messages`  | `Bearer <access_token>` | `ChatResponse`  |

**Request body:**

```json
{
  "messages": [
    { "role": "user", "content": "Qual foi minha corrida mais longa?" }
  ]
}
```

| Campo              | Tipo                    | Obrigatório | Regras                                              |
|--------------------|-------------------------|-------------|-----------------------------------------------------|
| `messages`         | `ChatMessageRequest[]`  | Sim         | Mín. 1 item; última mensagem deve ser `role: "user"` |
| `messages[].role`  | `"user" \| "assistant"` | Sim         | `system` e `tool` **não** aceitos no body           |
| `messages[].content` | `string`              | Sim         | Não vazio após `strip()`                            |

**Response 200:**

```json
{
  "message": {
    "role": "assistant",
    "content": "Sua corrida mais longa foi de 21,1 km em ..."
  },
  "tool_calls_made": ["get_longest_run"]
}
```

| Campo             | Tipo            | Descrição                                                |
|-------------------|-----------------|----------------------------------------------------------|
| `message.role`    | `"assistant"`   | Sempre `"assistant"` na resposta                         |
| `message.content` | `string`        | Resposta final em linguagem natural                      |
| `tool_calls_made` | `string[]`      | Nomes das tools invocadas na ordem de execução; `[]` se nenhuma |

| Código | Condição                                              | `detail` sugerido              |
|--------|-------------------------------------------------------|--------------------------------|
| 401    | Token ausente, malformado, inválido ou expirado       | conforme SPEC-013              |
| 422    | `messages` vazio, última msg ≠ `user`, `content` vazio, `role` inválido | validação Pydantic |
| 502    | OpenAI indisponível, timeout ou erro de API           | `"LLM provider unavailable"`   |
| 500    | Excedeu `CHAT_MAX_TOOL_ITERATIONS` sem resposta final | `"Chat processing failed"`     |

Assinatura do handler:

```python
# api/routes/chat.py
@router.post("/messages")
def send_chat_message(
    body: ChatRequest,
    current_user_id: UUID = Depends(get_current_user_id),
    orchestrator: ChatOrchestrator = Depends(get_chat_orchestrator),
) -> ChatResponseSchema: ...
```

`user_id` vem **exclusivamente** do JWT (`current_user_id`); não há `user_id` no path nem no body.

### Efeitos colaterais

Nenhum persistido. Leitura somente via `ActivityRepository` nas tools. Chamada HTTP externa à OpenAI (custo e latência de rede).

---

## Comportamentos

### Casos normais (Happy Path)

#### CN-1: Pergunta de PR aciona `get_longest_run`
**Dado** que o usuário autenticado tem atividades `Run` no banco  
**E** o `FakeLLMClient` retorna tool call `get_longest_run` na primeira rodada e resposta final na segunda  
**Quando** `POST /chat/messages` é chamado com `messages: [{ "role": "user", "content": "Qual foi minha corrida mais longa?" }]` e Bearer válido  
**Então** retorna `200` com `message.role == "assistant"` e conteúdo não vazio  
**E** `tool_calls_made == ["get_longest_run"]`  
**E** a tool foi executada com `user_id` do JWT (não do body)

#### CN-2: Pergunta de volume com período aciona `get_run_volume`
**Dado** que o usuário autenticado tem atividades `Run`  
**E** o LLM retorna tool call `get_run_volume` com `start_date` e `end_date` em ISO 8601  
**Quando** `ChatOrchestrator.handle` processa a mensagem do usuário  
**Então** retorna resposta final com `tool_calls_made` contendo `"get_run_volume"`  
**E** `ChatToolRegistry.execute` repassa as datas ao `VolumeEngine`

#### CN-3: Saudação sem necessidade de tool
**Dado** que o `FakeLLMClient` retorna resposta direta sem tool calls  
**Quando** `POST /chat/messages` é chamado com `messages: [{ "role": "user", "content": "Olá!" }]`  
**Então** retorna `200` com `message.content` não vazio  
**E** `tool_calls_made == []`

#### CN-4: Multi-turn preserva contexto
**Dado** um histórico `messages` com alternância `user` / `assistant` e última mensagem `user`  
**Quando** `ChatOrchestrator.handle` é invocado  
**Então** o `LLMClient.complete` recebe system prompt + histórico completo na ordem enviada pelo cliente

### Casos de borda (Edge Cases)

#### CB-1: Usuário sem atividades
**Dado** que o usuário autenticado não tem atividades do tipo solicitado  
**E** o LLM aciona `get_longest_run`  
**Quando** a tool retorna campos `null` (comportamento SPEC-007)  
**Então** o orchestrator repassa o resultado ao LLM sem exceção  
**E** a resposta final informa ausência de dados (texto gerado pelo LLM)

#### CB-2: LLM solicita tool desconhecida
**Dado** que o `FakeLLMClient` retorna tool call com `name` não registrado  
**Quando** `ChatOrchestrator.handle` tenta executar a tool  
**Então** levanta `ChatProcessingError`  
**E** o endpoint retorna `500` com `detail == "Chat processing failed"`

#### CB-3: Múltiplas tool calls numa única rodada
**Dado** que o LLM retorna duas tool calls (`get_longest_run` e `get_run_volume`) na mesma completion  
**Quando** `ChatOrchestrator.handle` processa a rodada  
**Então** ambas são executadas com o mesmo `user_id` do JWT  
**E** `tool_calls_made` contém ambos os nomes na ordem de execução

#### CB-4: Tool call com argumentos extras ignorados
**Dado** que o LLM envia argumento `user_id` espúrio (não deveria ocorrer — campo ausente do schema)  
**Quando** `ChatToolRegistry.execute` processa os argumentos  
**Então** ignora chaves desconhecidas e usa apenas `start_date` / `end_date`  
**E** `user_id` efetivo permanece o injetado pelo orchestrator

### Casos de erro

#### CE-1: Request sem header Authorization
**Dado** que o endpoint exige autenticação  
**Quando** `POST /chat/messages` é chamado sem header `Authorization`  
**Então** retorna `401` com `detail` indicando falta de autenticação

#### CE-2: Request com `messages` inválido
**Dado** um body com `messages: []` ou última mensagem com `role: "assistant"`  
**Quando** `POST /chat/messages` é chamado  
**Então** retorna `422` (validação Pydantic)

#### CE-3: OpenAI retorna erro
**Dado** que `OpenAILLMClient` recebe erro da API (timeout, 5xx, auth failure)  
**Quando** `ChatOrchestrator.handle` chama `llm_client.complete`  
**Então** levanta `LLMProviderError`  
**E** o endpoint retorna `502` com `detail == "LLM provider unavailable"`

#### CE-4: Loop de tools excede limite
**Dado** que `CHAT_MAX_TOOL_ITERATIONS = 5`  
**E** o LLM retorna tool calls em todas as 5 rodadas sem resposta final  
**Quando** `ChatOrchestrator.handle` processa o request  
**Então** levanta `ChatProcessingError`  
**E** o endpoint retorna `500` com `detail == "Chat processing failed"`

#### CE-5: `OPENAI_API_KEY` ausente em produção
**Dado** que `OPENAI_API_KEY` não está definido (string vazia) fora do ambiente de teste  
**Quando** o app tenta construir `OpenAILLMClient`  
**Então** falha explicitamente na inicialização — não chama OpenAI com chave vazia silenciosamente

---

## Critérios de Aceite

- [ ] Spec com status **Draft** no repositório
- [ ] `POST /chat/messages` funcional com Bearer JWT (SPEC-013)
- [ ] `user_id` nunca aparece no schema de tools enviado ao LLM
- [ ] `ChatToolRegistry` executa as 4 tools in-process com `user_id` do JWT
- [ ] `ChatOrchestrator` implementa loop tool-use com limite configurável
- [ ] `LLMClient` protocolo + `OpenAILLMClient` + `FakeLLMClient`
- [ ] Multi-turn via `messages[]` repassado ao LLM
- [ ] `tool_calls_made` presente na response
- [ ] Um teste unitário por CN/CB/CE documentado
- [ ] Teste de contrato de assinatura (`handle`, `complete`, `execute`)
- [ ] Teste de integração do endpoint com `FakeLLMClient` (sem rede)
- [ ] `OPENAI_API_KEY`, `OPENAI_MODEL`, `CHAT_MAX_TOOL_ITERATIONS` documentados no README
- [ ] Cobertura `convertreino.application` >= 80%
- [ ] Cobertura endpoints de chat >= 80%
- [ ] CI verde (ruff, mypy, pytest)
- [ ] Nenhuma migration Alembic
- [ ] Nova dependência direta: `openai>=1.0.0`
- [ ] Não contradiz SPEC-001, SPEC-003, SPEC-007–013

---

## Mapeamento Spec → Testes

| Artefato                              | Localização                                                         |
|---------------------------------------|---------------------------------------------------------------------|
| CN/CB/CE do `ChatOrchestrator`        | `backend/tests/unit/application/test_chat_orchestrator.py`          |
| `FakeLLMClient` + sequência tool-use  | `backend/tests/unit/application/test_chat_orchestrator.py`          |
| `ChatToolRegistry` + injeção `user_id`| `backend/tests/unit/application/test_chat_tools.py`                 |
| Schemas LLM sem `user_id`             | `backend/tests/unit/application/test_chat_tools.py`                 |
| `OpenAILLMClient` (mapeamento)        | `backend/tests/unit/application/llm/test_openai_client.py`          |
| CN-1, CN-3, CE-1, CE-2 (endpoint)     | `backend/tests/integration/test_chat_messages.py`                   |
| Contrato de assinatura                | `test_chat_orchestrator.py` ou `test_chat_tools.py`               |

Padrão de override: `set_chat_orchestrator_override` em `dependencies.py`, espelhando `set_jwt_service_override`. Testes de integração usam `FakeLLMClient` com completions pré-programadas — sem chamada real à OpenAI.

---

## Decisões de Design

### Decisão: `POST /chat/messages` sem `user_id` no path
**Contexto:** Como identificar o usuário no endpoint de chat.  
**Opção escolhida:** `user_id` exclusivamente do JWT; path `/chat/messages` sem parâmetro de usuário.  
**Alternativas rejeitadas:** `POST /users/{user_id}/chat/messages` com checagem de ownership (padrão sync SPEC-013).  
**Motivo:** Chat não precisa de `user_id` no contrato; JWT já prova identidade; contrato mais simples para o mobile.

### Decisão: Tools in-process, não via `/mcp` HTTP
**Contexto:** Como o orchestrator executa as ferramentas analíticas.  
**Opção escolhida:** Chamar funções de `mcp/tools/*.py` diretamente com `ActivityRepository` da sessão DB.  
**Alternativas rejeitadas:** Cliente MCP HTTP para `localhost/mcp`; duplicar lógica em Application Service.  
**Motivo:** Menor latência; sem expor `user_id` no transporte MCP; reutiliza handlers e mappers existentes (SPEC-007–012).

### Decisão: Schemas LLM sem `user_id` via `ChatToolRegistry`
**Contexto:** MCP tools em `/mcp` exigem `user_id` no schema (dev/stdio). O LLM não deve ver nem inferir esse valor.  
**Opção escolhida:** Nova camada `ChatToolRegistry` com schemas reduzidos; `/mcp` permanece inalterado.  
**Alternativas rejeitadas:** Remover `user_id` das MCP tools públicas; injetar `user_id` via middleware MCP.  
**Motivo:** Não quebra dev workflow; separação clara entre transporte MCP e orquestração de chat.

### Decisão: OpenAI Chat Completions + function calling
**Contexto:** Qual API e provider usar na POC.  
**Opção escolhida:** `OpenAILLMClient` com SDK oficial `openai`; modelo default `gpt-4o-mini`; interface `LLMClient` provider-agnostic.  
**Alternativas rejeitadas:** LiteLLM como proxy; Anthropic como único provider; Responses API (beta).  
**Motivo:** Padrão de mercado; custo baixo na POC; interface permite Anthropic ou outros depois.

### Decisão: Histórico multi-turn no cliente (stateless server)
**Contexto:** Como manter contexto conversacional.  
**Opção escolhida:** Cliente envia `messages[]` com histórico `user`/`assistant`; servidor não persiste.  
**Alternativas rejeitadas:** Tabela `Conversation`/`Message`; sessão server-side com ID de conversa.  
**Motivo:** Escopo mínimo da POC; sem migrations; mobile já gerencia estado de UI.

### Decisão: Resposta síncrona JSON (sem streaming)
**Contexto:** Formato da resposta HTTP.  
**Opção escolhida:** Response JSON completo após processamento total.  
**Alternativas rejeitadas:** SSE/streaming token-a-token.  
**Motivo:** Simplicidade na POC; streaming em spec futura (SPEC-017+).

### Decisão: Testes sem LLM real no CI
**Contexto:** Como testar seleção de tools e fluxo do orchestrator.  
**Opção escolhida:** `FakeLLMClient` com sequência determinística de completions.  
**Alternativas rejeitadas:** Chamadas reais à OpenAI em CI; gravar/respostar VCR cassettes.  
**Motivo:** CI rápido, determinístico e sem custo de API; E2E com LLM real fica nightly/futuro.

### Decisão: `tool_calls_made` no response
**Contexto:** O que retornar além da mensagem do assistente.  
**Opção escolhida:** Lista de nomes de tools executadas na ordem.  
**Alternativas rejeitadas:** Omitir metadados; retornar payloads completos das tools.  
**Motivo:** Útil para debug, testes de integração e auditoria sem parsear texto natural.

### Decisão: `LLMProviderError` e `ChatProcessingError` no domínio
**Contexto:** Onde classificar falhas de provider e de orquestração.  
**Opção escolhida:** Exceções em `domain/exceptions.py`; API traduz para HTTP 502/500.  
**Alternativas rejeitadas:** Exceções HTTP-specific em `api/`; retorno `None` silencioso.  
**Motivo:** Application não conhece HTTP; falha explícita é melhor que silêncio (princípio 4 do guia).

---

## Notas de Migração

- Nenhuma migration Alembic
- Novas variáveis de ambiente: `OPENAI_API_KEY` (obrigatória em prod), `OPENAI_MODEL`, `CHAT_MAX_TOOL_ITERATIONS`
- Nova dependência direta: `openai>=1.0.0`
- Endpoint novo; sem breaking change em contratos existentes
- `/mcp` HTTP permanece inalterado (com `user_id` no schema)
- Rollback: remover pacote `application/llm/`, `chat_orchestrator.py`, `chat_tools.py`, rota chat, config OpenAI, dependência `openai` — sem impacto em dados

---

## Roadmap pós-SPEC-014

| Spec futura | Conteúdo                                                                                    |
|-------------|---------------------------------------------------------------------------------------------|
| SPEC-015    | App mobile Expo: OAuth Strava via deep link, sessão JWT, sync inicial e tela de chat       |
| SPEC-016    | `period_resolver` server-side (somente se testes E2E mostrarem falha na conversão de períodos pelo LLM) |
| SPEC-017+   | Streaming SSE, persistência de conversas, rate limiting, testes E2E com LLM real            |

---

## Checklist de revisão (seção 12 do guia)

### Clareza
- [ ] O contexto explica o problema sem descrever a solução?
- [ ] O contrato tem tipos explícitos para todos os inputs e outputs?
- [ ] Cada comportamento tem "Dado / Quando / Então" completo?
- [ ] Os critérios de aceite são binários e verificáveis?

### Completude
- [ ] Há ao menos um caso normal (CN-1 a CN-4)?
- [ ] Casos de borda cobertos (sem dados, tool desconhecida, múltiplas tools)?
- [ ] Casos de erro especificados (`401`, `422`, `502`, `500`, secret ausente)?
- [ ] Escopo "Excluído" deixa claro o que ficou de fora (streaming, persistência, period_resolver)?

### Consistência
- [ ] Não contradiz SPEC-001, SPEC-003, SPEC-007–013?
- [ ] Nomes de tipos alinhados ao código existente (`Activity`, `UUID`, `PREngine`, `VolumeEngine`)?
- [ ] Application não acessa HTTP diretamente; API traduz exceções para códigos HTTP?
- [ ] Padrão de overrides de teste consistente com `dependencies.py` existente?
- [ ] Descrições de tools reutilizam constantes MCP sem duplicar texto?

### Testabilidade
- [ ] Cada comportamento mapeia para teste unitário ou de integração?
- [ ] Comportamentos determinísticos com `FakeLLMClient`?
- [ ] Efeitos colaterais explicitados (leitura DB + chamada OpenAI) e testáveis?
