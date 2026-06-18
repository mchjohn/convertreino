from uuid import UUID

from convertreino.domain.services.pr_engine import PREngine
from convertreino.mcp.mappers import activity_to_longest_run_result
from convertreino.mcp.schemas import LongestRunResult

GET_LONGEST_RUN_DESCRIPTION = (
    "Retorna a corrida (`Run`) com maior distância do usuário. "
    "Use quando o usuário perguntar sobre sua corrida mais longa, maior distância correndo, "
    "ou recorde de corrida. NÃO use para pedais/ciclismo (`get_longest_ride`), natação, "
    "pace médio geral, volume semanal ou elevação."
)


def get_longest_run(user_id: UUID, engine: PREngine) -> LongestRunResult:
    activity = engine.get_longest_run(user_id)
    return activity_to_longest_run_result(activity)
