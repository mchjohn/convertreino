from datetime import datetime
from uuid import UUID

from convertreino.domain.services.pr_engine import PREngine
from convertreino.mcp.mappers import activity_to_longest_ride_result, activity_to_longest_run_result
from convertreino.mcp.schemas import LongestRideResult, LongestRunResult

GET_LONGEST_RUN_DESCRIPTION = (
    "Retorna a corrida (`Run`) com maior distância do usuário, "
    "opcionalmente filtrada por intervalo de datas. "
    "Use quando o usuário perguntar sobre sua corrida mais longa, maior distância correndo, "
    "ou recorde de corrida — com ou sem menção a período (ano, mês, intervalo customizado). "
    "Quando o usuário mencionar um período, passe `start_date` e/ou `end_date` em ISO 8601 UTC. "
    "NÃO use para pedais/ciclismo (`get_longest_ride`), natação, volume semanal/mensal agregado, "
    "pace médio geral ou elevação. "
    "Conversão intenção → parâmetros: "
    "'em 2024' → start_date=2024-01-01T00:00:00+00:00, end_date=2024-12-31T23:59:59+00:00; "
    "'neste mês' → primeiro e último instante do mês corrente UTC; "
    "'entre março e junho de 2024' → start_date=2024-03-01T00:00:00+00:00, "
    "end_date=2024-06-30T23:59:59+00:00; "
    "sem período → omitir start_date e end_date (histórico completo). "
    "Perguntas que DEVEM acionar: 'Qual foi minha corrida mais longa?', "
    "'Qual meu recorde de corrida em km?', 'Qual a maior distância que já corri?', "
    "'Qual foi minha corrida mais longa em 2024?', 'Qual meu recorde de corrida neste mês?', "
    "'Qual a maior distância que corri entre março e junho?'. "
    "Perguntas que NÃO devem acionar: 'Qual foi meu pedal mais longo?' → get_longest_ride; "
    "'Quanto corri essa semana?' → volume engine; "
    "'Quanto corri em 2024?' (soma total) → volume engine; "
    "'Qual meu pace médio?' → engine de pace."
)


def get_longest_run(
    user_id: UUID,
    engine: PREngine,
    *,
    start_date: datetime | None = None,
    end_date: datetime | None = None,
) -> LongestRunResult:
    activity = engine.get_longest_run(
        user_id, start_date=start_date, end_date=end_date
    )
    return activity_to_longest_run_result(activity)


GET_LONGEST_RIDE_DESCRIPTION = (
    "Retorna o pedal (`Ride`) com maior distância do usuário, "
    "opcionalmente filtrado por intervalo de datas. "
    "Use quando o usuário perguntar sobre seu pedal mais longo, maior distância pedalando, "
    "ou recorde de ciclismo — com ou sem menção a período (ano, mês, intervalo customizado). "
    "Quando o usuário mencionar um período, passe `start_date` e/ou `end_date` em ISO 8601 UTC. "
    "NÃO use para corridas (`get_longest_run`), natação, volume semanal/mensal agregado "
    "ou elevação. "
    "Conversão intenção → parâmetros: "
    "'em 2024' → start_date=2024-01-01T00:00:00+00:00, end_date=2024-12-31T23:59:59+00:00; "
    "'neste mês' → primeiro e último instante do mês corrente UTC; "
    "'entre março e junho de 2024' → start_date=2024-03-01T00:00:00+00:00, "
    "end_date=2024-06-30T23:59:59+00:00; "
    "sem período → omitir start_date e end_date (histórico completo). "
    "Perguntas que DEVEM acionar: 'Qual foi meu pedal mais longo?', "
    "'Qual meu recorde de pedal em km?', 'Qual a maior distância que já pedalei?', "
    "'Qual foi meu pedal mais longo em 2024?', 'Qual meu recorde de ciclismo neste mês?'. "
    "Perguntas que NÃO devem acionar: 'Qual foi minha corrida mais longa?' → get_longest_run; "
    "'Quanto pedalei essa semana?' → volume engine; "
    "'Quanto pedalei em 2024?' (soma total) → volume engine; "
    "'Qual minha velocidade média geral?' → engine de velocidade."
)


def get_longest_ride(
    user_id: UUID,
    engine: PREngine,
    *,
    start_date: datetime | None = None,
    end_date: datetime | None = None,
) -> LongestRideResult:
    activity = engine.get_longest_ride(
        user_id, start_date=start_date, end_date=end_date
    )
    return activity_to_longest_ride_result(activity)
