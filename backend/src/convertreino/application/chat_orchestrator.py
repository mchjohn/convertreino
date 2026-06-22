import json
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from uuid import UUID

from convertreino.application.chat_tools import ChatToolRegistry
from convertreino.application.llm.client import LLMClient
from convertreino.application.llm.types import ChatMessage
from convertreino.domain.exceptions import ChatProcessingError

DEFAULT_SYSTEM_PROMPT = (
    "Você é o ConverTreino, assistente de performance esportiva para atletas com dados do Strava. "
    "Responda sempre em português do Brasil. "
    "Use as ferramentas disponíveis para obter dados analíticos; nunca invente números. "
    "Se a ferramenta retornar dados vazios ou nulos, informe claramente que não há dados. "
    "Diferencie recorde individual (get_longest_run / get_longest_ride) de volume agregado "
    "(get_run_volume / get_ride_volume). "
    "Diferencie corrida (Run) de pedal (Ride). "
    "Converta períodos mencionados pelo usuário em start_date/end_date "
    "ISO 8601 UTC ao chamar tools."
)


@dataclass(frozen=True, slots=True)
class ChatResponse:
    message: ChatMessage
    tool_calls_made: tuple[str, ...]


def _utc_week_bounds(reference: datetime) -> tuple[datetime, datetime]:
    monday = reference.astimezone(UTC).replace(hour=0, minute=0, second=0, microsecond=0)
    monday -= timedelta(days=monday.weekday())
    sunday_end = monday + timedelta(days=6, hours=23, minutes=59, seconds=59)
    return monday, sunday_end


def _build_system_prompt(base: str, now_utc: datetime) -> str:
    this_start, this_end = _utc_week_bounds(now_utc)
    last_start, last_end = _utc_week_bounds(this_start - timedelta(seconds=1))
    return (
        f"{base} "
        f"A data e hora atuais em UTC são: {now_utc.isoformat()}. "
        "A semana civil em UTC começa na segunda-feira 00:00 e termina no domingo 23:59:59. "
        "Use essa data como referência para períodos relativos. "
        f"Referência: 'essa semana' = {this_start.isoformat()} a {this_end.isoformat()}; "
        f"'semana passada' = {last_start.isoformat()} a {last_end.isoformat()}."
    )


class ChatOrchestrator:
    def __init__(
        self,
        llm_client: LLMClient,
        tool_registry: ChatToolRegistry,
        *,
        max_tool_iterations: int = 5,
        system_prompt: str = DEFAULT_SYSTEM_PROMPT,
    ) -> None:
        self._llm_client = llm_client
        self._tool_registry = tool_registry
        self._max_tool_iterations = max_tool_iterations
        self._system_prompt = system_prompt

    def handle(self, user_id: UUID, messages: list[ChatMessage]) -> ChatResponse:
        conversation: list[ChatMessage] = [
            ChatMessage(
                role="system",
                content=_build_system_prompt(self._system_prompt, datetime.now(UTC)),
            ),
            *messages,
        ]
        tool_calls_made: list[str] = []
        iterations = 0
        tools = self._tool_registry.get_tool_definitions()

        while True:
            completion = self._llm_client.complete(conversation, tools)

            if completion.tool_calls:
                iterations += 1
                if iterations > self._max_tool_iterations:
                    raise ChatProcessingError("Exceeded max tool iterations")

                assistant_content = completion.message.content if completion.message else ""
                conversation.append(
                    ChatMessage(
                        role="assistant",
                        content=assistant_content,
                        tool_calls=completion.tool_calls,
                    )
                )

                for tool_call in completion.tool_calls:
                    tool_calls_made.append(tool_call.name)
                    try:
                        result = self._tool_registry.execute(
                            user_id,
                            tool_call.name,
                            tool_call.arguments,
                        )
                    except ValueError as exc:
                        raise ChatProcessingError(str(exc)) from exc
                    conversation.append(
                        ChatMessage(
                            role="tool",
                            content=json.dumps(result),
                            tool_call_id=tool_call.id,
                        )
                    )
                continue

            if completion.message is not None and completion.message.role == "assistant":
                return ChatResponse(
                    message=completion.message,
                    tool_calls_made=tuple(tool_calls_made),
                )

            raise ChatProcessingError("LLM did not return a final assistant message")
