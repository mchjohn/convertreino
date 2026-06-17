# ConverTreino

## Visão Geral do Produto 

O ConverTreino é um assistente conversacional móvel que transforma dados de performance do Strava em insights acionáveis através de uma interface de chat intuitiva. 

O produto opera como um Assistente Especialista Direcionado: toda lógica analítica é executada por serviços determinísticos; o LLM atua exclusivamente no entendimento de intenção, roteamento de ferramentas e formatação de respostas em linguagem natural. Isso garante precisão matemática, controle de custo operacional e segurança de execução.

## Backend (SPEC-001)

A fundação do backend está em [`backend/`](backend/) com spec aprovada em [`specs/SPEC-001-backend-foundation.md`](specs/SPEC-001-backend-foundation.md).

```bash
cd backend
docker compose up -d
uv sync --all-extras --dev   # ou: python3 -m venv .venv && pip install -e ".[dev]"
uv run alembic upgrade head
uv run pytest
```
