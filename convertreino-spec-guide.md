# ConverTreino — Guia de Criação de Specs (SDD + TDD)

> **Propósito deste documento:** Estabelecer o processo, os templates e os critérios de qualidade que toda spec de desenvolvimento do ConverTreino deve seguir, combinando Specification-Driven Development (SDD) com Test-Driven Development (TDD).

---

## Índice

1. [Filosofia e Princípios](#1-filosofia-e-princípios)
2. [Quando criar uma spec](#2-quando-criar-uma-spec)
3. [Anatomia de uma spec](#3-anatomia-de-uma-spec)
4. [Template de spec](#4-template-de-spec)
5. [Ciclo SDD — Especificar antes de implementar](#5-ciclo-sdd--especificar-antes-de-implementar)
6. [Ciclo TDD — Red → Green → Refactor](#6-ciclo-tdd--red--green--refactor)
7. [Como escrever bons testes a partir da spec](#7-como-escrever-bons-testes-a-partir-da-spec)
8. [Níveis de teste e cobertura mínima](#8-níveis-de-teste-e-cobertura-mínima)
9. [Spec por camada da arquitetura](#9-spec-por-camada-da-arquitetura)
10. [Critérios de aceite e Definition of Done](#10-critérios-de-aceite-e-definition-of-done)
11. [Exemplos comentados](#11-exemplos-comentados)
12. [Checklist de revisão de spec](#12-checklist-de-revisão-de-spec)

---

## 1. Filosofia e Princípios

### Por que SDD + TDD neste projeto?

O ConverTreino combina três domínios com falhas silenciosas em potencial:

- **LLM com tool use** — o modelo pode selecionar a ferramenta errada sem nenhum erro explícito.
- **Cálculos analíticos** — um bug em pace médio ou sequência de semanas pode passar despercebido visualmente.
- **Integrações externas** — Strava API tem rate limits, formatos variáveis e comportamento de webhook imprevisível.

Especificar antes de implementar e testar antes de "funcionar" são a resposta a esses três riscos.

### Princípios inegociáveis

| # | Princípio | O que significa na prática |
|---|-----------|---------------------------|
| 1 | **Spec primeiro** | Nenhuma tarefa de implementação começa sem spec aprovada. |
| 2 | **Testes antes do código** | O teste que valida o comportamento é escrito antes da implementação. |
| 3 | **Comportamento, não implementação** | Specs descrevem *o quê*, não *como*. Testes testam contratos, não detalhes internos. |
| 4 | **Falha explícita é melhor que silêncio** | Toda condição de erro deve ter comportamento esperado documentado. |
| 5 | **Specs são vivas** | Quando o comportamento muda, a spec muda primeiro — antes do código. |

---

## 2. Quando criar uma spec

Uma spec é obrigatória para qualquer item que se enquadre em ao menos uma das condições abaixo:

```
✅ Nova ferramenta MCP exposta ao LLM
✅ Novo Domain Service ou método em Domain Service existente
✅ Novo endpoint de API
✅ Novo fluxo de autenticação ou autorização
✅ Mudança em cálculo analítico (ex: como pace médio é computado)
✅ Mudança em comportamento de cache ou invalidação
✅ Novo tipo de evento processado pelo webhook
✅ Mudança em schema do banco de dados
✅ Qualquer comportamento que envolva o LLM tomando uma decisão
```

**Não é necessária spec formal para:**

```
❌ Refatoração interna sem mudança de contrato externo
❌ Correção de typo ou ajuste de mensagem de log
❌ Atualização de dependência sem breaking change
❌ Melhoria de performance sem mudança de comportamento observável
```

> Regra de ouro: se você precisaria atualizar um teste existente ou escrever um novo, precisa de uma spec.

---

## 3. Anatomia de uma spec

Toda spec do ConverTreino é composta por seis seções obrigatórias e duas opcionais:

```
Obrigatórias:
  [1] Identificação        — título, autor, status, dependências
  [2] Contexto             — por que isso existe, qual problema resolve
  [3] Escopo               — o que está e o que não está incluído
  [4] Contrato             — inputs, outputs, efeitos colaterais
  [5] Comportamentos       — casos normais, limites e erros
  [6] Critérios de aceite  — como saber que está pronto e correto

Opcionais:
  [7] Decisões de design   — trade-offs e alternativas rejeitadas
  [8] Notas de migração    — impacto em dados ou contratos existentes
```

Cada seção tem um propósito distinto. Não colapse seções para economizar tempo — a separação é intencional.

---

## 4. Template de spec

Copie este template para cada nova spec. O nome do arquivo segue o padrão: `SPEC-<número>-<slug>.md`.

Exemplo: `SPEC-012-pr-engine-longest-activity.md`

---

```markdown
# SPEC-XXX — [Título descritivo do comportamento]

| Campo        | Valor                              |
|--------------|------------------------------------|
| **Status**   | Draft / Review / Aprovada / Obsoleta |
| **Autor**    | @nome                              |
| **Revisor**  | @nome                              |
| **Criada em**| YYYY-MM-DD                         |
| **Camada**   | Domain / Application / API / MCP / Frontend |
| **Depende de** | SPEC-XXX, SPEC-YYY               |
| **Épico**    | PR / Consistência / Tendência / Volume / Infra |

---

## Contexto

<!--
  Explique o problema de negócio ou técnico que esta spec resolve.
  Uma ou duas frases claras. Evite descrever a solução aqui.
  
  Bom:   "O usuário pergunta qual foi sua corrida mais longa e o sistema
          precisa retornar a atividade correta com dados de distância e pace."
  Ruim:  "Vamos implementar o método get_longest_activity no PREngine."
-->

## Escopo

### Incluído
- 

### Excluído (explicitamente fora desta spec)
- 

---

## Contrato

### Assinatura
<!--
  Para Domain Services e Application Services: assinatura do método.
  Para MCP Tools: nome da tool e schema de input/output.
  Para APIs: método HTTP, path, request body, response body.
  Para workers: evento de entrada e efeito esperado.
-->

```python
# Exemplo para Domain Service
def get_longest_activity(user_id: UUID) -> Activity | None:
    ...
```

### Inputs

| Parâmetro | Tipo | Obrigatório | Descrição |
|-----------|------|-------------|-----------|
| `user_id` | UUID | Sim         | ID interno do usuário |

### Outputs

| Campo      | Tipo     | Descrição                          |
|------------|----------|------------------------------------|
| `activity` | Activity | Atividade com maior distância. `None` se não houver dados. |

### Efeitos colaterais
<!--
  Liste qualquer efeito além do retorno: escrita em banco, invalidação de cache,
  publicação em fila, envio de email, etc.
  Se não houver: escreva "Nenhum."
-->

---

## Comportamentos

### Casos normais (Happy Path)

#### CN-1: [Nome do caso]
**Dado** [estado inicial do sistema]  
**Quando** [ação ou chamada]  
**Então** [resultado esperado]

#### CN-2: [Nome do caso]
...

### Casos de borda (Edge Cases)

#### CB-1: [Nome do caso]
**Dado** ...  
**Quando** ...  
**Então** ...

### Casos de erro

#### CE-1: [Nome do caso]
**Dado** ...  
**Quando** ...  
**Então** [exceção lançada OU código de erro OU resposta de fallback]

---

## Critérios de Aceite

<!--
  Lista binária (sim/não). Cada item deve ser verificável sem ambiguidade.
  Evite: "funciona corretamente", "retorna dados certos".
  Use: "retorna None quando não há atividades", "lança ValueError quando user_id é inválido".
-->

- [ ] ...
- [ ] ...
- [ ] ...

---

## Decisões de Design *(opcional)*

<!--
  Documente trade-offs relevantes e alternativas consideradas.
  Útil quando a decisão não é óbvia.
-->

### Decisão: [título]
**Contexto:** ...  
**Opção escolhida:** ...  
**Alternativas rejeitadas:** ...  
**Motivo:** ...

---

## Notas de Migração *(opcional)*

<!--
  Impacto em dados existentes, mudanças de schema, breaking changes de contrato.
-->
```

---

## 5. Ciclo SDD — Especificar antes de implementar

O fluxo de trabalho para cada funcionalidade segue esta sequência obrigatória:

```
┌─────────────────────────────────────────────────────────────┐
│                    CICLO SDD + TDD                          │
└─────────────────────────────────────────────────────────────┘

  1. SPEC DRAFT
     └─ Engenheiro escreve spec completa com comportamentos e contrato.
        Status: Draft

  2. SPEC REVIEW
     └─ Outro engenheiro revisa:
        • Contrato está completo?
        • Edge cases cobertos?
        • Critérios de aceite são verificáveis?
        Status: Review → Aprovada

  3. TESTES RED
     └─ Engenheiro escreve testes a partir dos comportamentos da spec.
        Todos os testes falham (RED). Nenhuma implementação ainda.

  4. IMPLEMENTAÇÃO
     └─ Engenheiro implementa o mínimo necessário para os testes passarem.
        Sem adicionar comportamentos não especificados.

  5. TESTES GREEN
     └─ Todos os testes da spec passam. Cobertura mínima atingida.

  6. REFACTOR
     └─ Código limpo sem quebrar testes. Spec não muda.

  7. REVIEW + MERGE
     └─ PR inclui: spec aprovada + testes + implementação.
        Sem spec aprovada = PR não é mergeado.
```

### Regras do ciclo

- **Spec aprovada é pré-requisito para abrir PR.** PRs sem spec referenciada são rejeitados automaticamente.
- **Testes são escritos pelo mesmo engenheiro que escreve a spec**, não após a implementação.
- **Se a implementação revelar um comportamento não especificado**, o engenheiro para, atualiza a spec, passa por review novamente, e só então continua.
- **Refactor não requer nova spec**, mas não pode mudar comportamentos observáveis.

---

## 6. Ciclo TDD — Red → Green → Refactor

### Red — escreva o teste antes

O teste é derivado diretamente dos **Comportamentos** da spec. Cada caso (CN, CB, CE) vira um ou mais testes.

```python
# A partir de CN-1 da spec: usuário com atividades retorna a mais longa
def test_get_longest_activity_returns_activity_with_max_distance():
    # Arrange — estado inicial descrito no "Dado"
    user_id = uuid4()
    activities = [
        build_activity(user_id=user_id, distance_meters=5000),
        build_activity(user_id=user_id, distance_meters=21097),  # mais longa
        build_activity(user_id=user_id, distance_meters=10000),
    ]
    repo = InMemoryActivityRepository(activities)
    engine = PREngine(repo)

    # Act — ação descrita no "Quando"
    result = engine.get_longest_activity(user_id)

    # Assert — resultado descrito no "Então"
    assert result.distance_meters == 21097
```

Neste ponto, `PREngine` e `get_longest_activity` ainda não existem. O teste **deve falhar**.

### Green — implemente o mínimo

Implemente apenas o suficiente para os testes passarem. Sem antecipar requisitos futuros.

```python
class PREngine:
    def __init__(self, activity_repo: ActivityRepository):
        self._repo = activity_repo

    def get_longest_activity(self, user_id: UUID) -> Activity | None:
        activities = self._repo.get_all(user_id)
        if not activities:
            return None
        return max(activities, key=lambda a: a.distance_meters)
```

### Refactor — limpe sem quebrar

Melhore a legibilidade, extraia constantes, renomeie para clareza. Os testes devem continuar passando.

---

## 7. Como escrever bons testes a partir da spec

### Mapeamento Spec → Teste

| Seção da spec | Tipo de teste | Localização |
|---------------|---------------|-------------|
| Casos normais (CN) | Testes de caminho feliz | `test_<módulo>/test_<feature>.py` |
| Casos de borda (CB) | Testes de limites | Mesmo arquivo |
| Casos de erro (CE) | Testes de exceção/erro | Mesmo arquivo |
| Contrato (assinatura) | Testes de tipo/interface | `test_contracts/` |
| Critérios de aceite | Testes de integração | `test_integration/` |

### Estrutura de teste: AAA obrigatório

Todo teste segue o padrão **Arrange → Act → Assert**, com separação visual explícita:

```python
def test_nome_descritivo_do_comportamento():
    # Arrange
    ...

    # Act
    result = ...

    # Assert
    assert ...
```

**Nunca** colapse as três fases em uma linha só. A separação explícita é parte da documentação viva.

### Nomenclatura de testes

O nome do teste deve descrever o comportamento, não a implementação:

```python
# ✅ Correto — descreve o comportamento esperado
def test_get_longest_activity_returns_none_when_user_has_no_activities():
def test_consistency_engine_counts_only_weeks_with_at_least_one_run():
def test_trend_engine_returns_improvement_when_recent_pace_is_faster():

# ❌ Errado — descreve a implementação
def test_max_function_on_activities_list():
def test_filter_by_date_range():
def test_sql_query_execution():
```

### Fixtures e builders

Use **builders** para construir objetos de domínio nos testes. Nunca construa dicionários crus ou objetos com todos os campos preenchidos manualmente em cada teste.

```python
# builders/activity_builder.py
def build_activity(
    user_id: UUID | None = None,
    distance_meters: float = 5000.0,
    elapsed_time_seconds: int = 1800,
    start_date: datetime | None = None,
    activity_type: str = "Run",
    **kwargs
) -> Activity:
    return Activity(
        id=uuid4(),
        user_id=user_id or uuid4(),
        distance_meters=distance_meters,
        elapsed_time_seconds=elapsed_time_seconds,
        start_date=start_date or datetime.now(UTC),
        activity_type=activity_type,
        **kwargs
    )
```

### Repositórios in-memory para testes de domínio

Domain Services **nunca** devem ser testados contra o banco real. Use repositórios in-memory que implementam a mesma interface:

```python
class InMemoryActivityRepository(ActivityRepository):
    def __init__(self, activities: list[Activity] | None = None):
        self._store: dict[UUID, list[Activity]] = {}
        for activity in (activities or []):
            self._store.setdefault(activity.user_id, []).append(activity)

    def get_all(self, user_id: UUID) -> list[Activity]:
        return self._store.get(user_id, [])

    def save(self, activity: Activity) -> None:
        self._store.setdefault(activity.user_id, []).append(activity)
```

---

## 8. Níveis de teste e cobertura mínima

### Pirâmide de testes do ConverTreino

```
          ▲
         /E2E\          → Fluxos críticos completos (chat → resposta)
        /──────\           2-3 por épico. Lentos, rodados em CI nightly.
       / Integr \
      /──────────\       → Camada de API + banco real (test database)
     /   ação    \          1 por endpoint. Rodados em CI a cada PR.
    /──────────────\
   /   Unitários   \    → Domain Services + Application Services
  /────────────────\       Todos os comportamentos da spec.
 /                  \      Rodados localmente e em CI a cada commit.
└────────────────────┘
```

### Cobertura mínima por camada

| Camada | Cobertura mínima | Foco principal |
|--------|-----------------|----------------|
| Domain Services | 95% | Toda lógica de cálculo e regra de negócio |
| Application Services | 80% | Coordenação e fluxo |
| MCP Tools | 90% | Mapeamento de intenção → ferramenta |
| API Endpoints | 80% | Request/response e códigos HTTP |
| Analytics Workers | 85% | Cálculo de métricas e idempotência |
| Frontend | 70% | Componentes críticos de UI |

> Cobertura é necessária mas não suficiente. 100% de cobertura com asserts fracos vale menos que 70% com asserts precisos.

### Testes obrigatórios para cada spec

Toda spec aprovada deve ter ao menos:

```
✅ Um teste para cada Caso Normal (CN)
✅ Um teste para cada Caso de Borda (CB)
✅ Um teste para cada Caso de Erro (CE)
✅ Um teste de contrato (assinatura e tipos de retorno)
✅ Um teste de integração cobrindo ao menos um Critério de Aceite
```

---

## 9. Spec por camada da arquitetura

Cada camada tem preocupações específicas que a spec deve endereçar.

### Domain Services

A spec deve descrever:
- **Regra de negócio** exata (ex: "semana ativa = ao menos 1 atividade do tipo Run ou Ride").
- **Definição de termos** (o que é "pace médio"? média das paces por atividade ou distância total / tempo total?).
- **Comportamento com dados ausentes** (zero atividades, usuário novo).
- **Precisão numérica** quando relevante (arredondar pace para 2 casas decimais).

### Application Services

A spec deve descrever:
- **Ordem de operações** (busca no cache → banco → calcula?).
- **Política de cache** (qual chave, qual TTL, quando invalidar).
- **Transações** (o que deve ser atômico?).
- **Comportamento em falha parcial** (cache indisponível → continua sem cache?).

### MCP Tools (Ferramentas expostas ao LLM)

A spec deve descrever:
- **Nome e descrição da tool** — a descrição é lida pelo LLM para decidir quando usá-la. Deve ser precisa.
- **Schema de input** com tipos e restrições.
- **Schema de output** com estrutura exata.
- **Exemplos de perguntas** que devem acionar esta tool.
- **Exemplos de perguntas** que NÃO devem acionar esta tool (fronteiras de intenção).

```markdown
## Contrato — MCP Tool

**Nome:** `get_longest_activity`

**Descrição para o LLM:**
"Retorna a atividade com maior distância percorrida pelo usuário.
Use quando o usuário perguntar sobre sua corrida/pedalada/atividade mais longa,
maior distância ou percurso mais extenso. NÃO use para perguntas sobre
velocidade, pace, elevação ou frequência."

**Input schema:**
{
  "user_id": "UUID do usuário autenticado (injetado pelo sistema)"
}

**Output schema:**
{
  "activity_id": "string",
  "distance_km": "number",
  "date": "ISO 8601",
  "duration_minutes": "number",
  "average_pace_min_per_km": "number | null"
}
```

### API Endpoints

A spec deve descrever:
- Método HTTP, path e parâmetros.
- Request body com tipos e validações.
- Response body para cada código HTTP possível (200, 400, 401, 404, 422, 500).
- Autenticação e autorização necessárias.
- Rate limiting aplicado.

### Analytics Workers

A spec deve descrever:
- Evento de entrada (estrutura do payload da fila).
- Métricas recalculadas (quais registros no banco são afetados).
- **Idempotência**: processar o mesmo evento duas vezes deve produzir o mesmo resultado.
- Comportamento em falha (retry? dead letter queue?).

---

## 10. Critérios de aceite e Definition of Done

### Definition of Done (DoD) — válido para toda spec

Uma spec está "Done" quando **todos** os itens abaixo são verdadeiros:

```
Spec:
  ☐ Spec com status "Aprovada" no repositório
  ☐ Todos os comportamentos (CN, CB, CE) descritos
  ☐ Contrato completo com tipos de input e output
  ☐ Critérios de aceite listados e verificáveis

Testes:
  ☐ Testes escritos para todos os comportamentos da spec
  ☐ Cobertura mínima da camada atingida
  ☐ Nenhum teste com assert fraco (assert result is not None sem verificar o valor)
  ☐ Testes passam no CI

Implementação:
  ☐ Código implementa exatamente o que a spec descreve (nem mais, nem menos)
  ☐ Nenhum comportamento não especificado foi adicionado
  ☐ Linting e type checking passando

PR:
  ☐ PR referencia o número da spec (ex: "Implements SPEC-012")
  ☐ Revisado por ao menos um outro engenheiro
  ☐ CI verde
```

### Critérios de aceite vs. testes

| Critério de aceite | Tipo de teste correspondente |
|--------------------|------------------------------|
| Comportamento funcional correto | Teste unitário de Domain Service |
| Contrato de API respeitado | Teste de integração de endpoint |
| LLM seleciona a tool correta | Teste de MCP tool selection |
| Performance dentro do SLO | Teste de carga (pós-MVP) |
| Dado persistido corretamente | Teste de integração com banco |

---

## 11. Exemplos comentados

### Exemplo 1 — Domain Service completo

```markdown
# SPEC-007 — PR Engine: Atividade com Maior Distância

| Campo      | Valor        |
|------------|--------------|
| Status     | Aprovada     |
| Autor      | @dev1        |
| Revisor    | @dev2        |
| Camada     | Domain       |
| Épico      | PR           |

## Contexto

O usuário pergunta qual foi sua corrida mais longa. O PREngine precisa
retornar a atividade de corrida com maior distância percorrida, considerando
apenas atividades do tipo "Run".

## Escopo

### Incluído
- Busca da atividade com maior distance_meters entre atividades do tipo "Run"
- Retorno de None quando não há atividades

### Excluído
- Outros tipos de atividade (Ride, Swim) — spec separada por tipo
- Filtro por período de tempo — spec SPEC-008

## Contrato

### Assinatura
def get_longest_run(user_id: UUID) -> Activity | None

### Inputs
| Parâmetro | Tipo | Obrigatório | Descrição |
|-----------|------|-------------|-----------|
| user_id   | UUID | Sim         | ID interno do usuário |

### Outputs
Activity com todos os campos preenchidos, ou None.

### Efeitos colaterais
Nenhum. Operação somente leitura.

## Comportamentos

### Casos normais

#### CN-1: Usuário tem múltiplas corridas
Dado que o usuário tem 3 atividades do tipo "Run" com distâncias
de 5km, 21km e 10km  
Quando get_longest_run(user_id) é chamado  
Então retorna a atividade com distance_meters = 21097

#### CN-2: Usuário tem apenas uma corrida
Dado que o usuário tem exatamente 1 atividade do tipo "Run"  
Quando get_longest_run(user_id) é chamado  
Então retorna essa atividade

### Casos de borda

#### CB-1: Usuário tem atividades mas nenhuma é corrida
Dado que o usuário tem atividades do tipo "Ride" e "Swim"  
Quando get_longest_run(user_id) é chamado  
Então retorna None

#### CB-2: Duas corridas com distância idêntica
Dado que o usuário tem 2 corridas com exatamente a mesma distância  
Quando get_longest_run(user_id) é chamado  
Então retorna qualquer uma das duas (comportamento determinístico
preferível: a mais recente por start_date)

### Casos de erro

#### CE-1: Usuário sem atividades
Dado que o usuário não tem nenhuma atividade registrada  
Quando get_longest_run(user_id) é chamado  
Então retorna None (não lança exceção)

#### CE-2: user_id inválido
Dado que user_id não corresponde a nenhum usuário registrado  
Quando get_longest_run(user_id) é chamado  
Então retorna None

## Critérios de Aceite
- [ ] Retorna a atividade com maior distance_meters quando há múltiplas
- [ ] Filtra apenas atividades do tipo "Run"
- [ ] Retorna None (não levanta exceção) quando não há corridas
- [ ] Comportamento determinístico em caso de empate (mais recente)
- [ ] Operação é somente leitura (sem efeitos colaterais)
```

---

### Exemplo 2 — MCP Tool com fronteiras de intenção

```markdown
# SPEC-015 — MCP Tool: get_weekly_volume

## Contrato — MCP Tool

**Nome:** `get_weekly_volume`

**Descrição para o LLM:**
"Retorna o volume total de corridas (em km) de uma semana específica
ou da semana atual. Use quando o usuário perguntar quanto correu em
uma semana, volume semanal, ou distância acumulada na semana.
NÃO use para meses, anos ou períodos customizados."

**Perguntas que DEVEM acionar esta tool:**
- "Quanto corri essa semana?"
- "Qual foi meu volume semanal?"
- "Quantos km na semana passada?"

**Perguntas que NÃO devem acionar esta tool:**
- "Quanto corri esse mês?" → get_monthly_volume
- "Quantos km esse ano?" → get_yearly_volume
- "Qual foi minha corrida mais longa?" → get_longest_run

## Comportamentos

### CE-1: Semana sem atividades
Dado que a semana solicitada não tem atividades  
Quando a tool é chamada  
Então retorna { "total_km": 0, "activities_count": 0 }
(não retorna erro — zero é uma resposta válida)
```

---

## 12. Checklist de revisão de spec

Use este checklist ao revisar uma spec antes de aprovar:

### Clareza
- [ ] O contexto explica o problema sem descrever a solução?
- [ ] O contrato tem tipos explícitos para todos os inputs e outputs?
- [ ] Cada comportamento tem "Dado / Quando / Então" completo?
- [ ] Os critérios de aceite são binários e verificáveis sem ambiguidade?

### Completude
- [ ] Há ao menos um caso normal (CN)?
- [ ] Os casos de borda óbvios estão cobertos (lista vazia, usuário novo, empate)?
- [ ] Os casos de erro estão especificados com comportamento esperado?
- [ ] O escopo "Excluído" deixa claro o que foi conscientemente deixado de fora?

### Consistência
- [ ] A spec não contradiz specs existentes aprovadas?
- [ ] Os nomes de tipos e entidades são consistentes com o restante do sistema?
- [ ] A camada está correta (domínio não acessa banco diretamente, etc.)?

### Testabilidade
- [ ] É possível escrever um teste para cada comportamento descrito?
- [ ] Os comportamentos são determinísticos (mesmo input → mesmo output)?
- [ ] Efeitos colaterais estão explicitados e são testáveis?

---

*Este guia é um documento vivo. Atualize-o quando o processo evoluir — mas nunca remova seções sem consenso da equipe.*

---

**Versão:** 1.0  
**Projeto:** ConverTreino  
**Metodologia:** SDD + TDD
```
