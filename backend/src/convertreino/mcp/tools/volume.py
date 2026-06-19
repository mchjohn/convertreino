from datetime import datetime
from uuid import UUID

from convertreino.domain.services.volume_engine import VolumeEngine
from convertreino.mcp.mappers import (
    volume_result_to_ride_volume_result,
    volume_result_to_run_volume_result,
)
from convertreino.mcp.schemas import RideVolumeResult, RunVolumeResult

GET_RUN_VOLUME_DESCRIPTION = (
    "Retorna o volume total de corridas (`Run`) do usuário — soma de distâncias e contagem de "
    "atividades — opcionalmente filtrado por intervalo de datas. "
    "Use quando o usuário perguntar quanto correu, volume de corrida, "
    "distância acumulada correndo, "
    "quantos km em um período, ou quantas corridas fez — com ou sem menção a período "
    "(semana, mês, ano, intervalo customizado). "
    "Quando o usuário mencionar um período, passe `start_date` e/ou `end_date` em ISO 8601 UTC. "
    "NÃO use para pedais/ciclismo (`get_ride_volume`), "
    "recorde de corrida individual (`get_longest_run`), "
    "natação, pace médio ou elevação. "
    "Conversão intenção → parâmetros: "
    "'essa semana' → primeiro instante da semana corrente UTC (segunda 00:00) e último instante "
    "(domingo 23:59:59); "
    "'em 2024' → start_date=2024-01-01T00:00:00+00:00, end_date=2024-12-31T23:59:59+00:00; "
    "'neste mês' → primeiro e último instante do mês corrente UTC; "
    "'entre março e junho de 2024' → start_date=2024-03-01T00:00:00+00:00, "
    "end_date=2024-06-30T23:59:59+00:00; "
    "sem período → omitir start_date e end_date (histórico completo). "
    "Perguntas que DEVEM acionar: 'Quanto corri essa semana?', "
    "'Quantos km corri em 2024?', 'Qual meu volume total de corrida?', "
    "'Quantas corridas fiz neste mês?', "
    "'Qual a distância acumulada correndo entre março e junho?', "
    "'Quanto corri no ano passado?' (converter para intervalo ISO 8601). "
    "Perguntas que NÃO devem acionar: 'Qual foi minha corrida mais longa?' → get_longest_run; "
    "'Qual a maior distância que já corri?' → get_longest_run; "
    "'Quanto pedalei essa semana?' → get_ride_volume; "
    "'Quanto treinei no total?' (Run + Ride) → fora de escopo; "
    "'Qual meu pace médio?' → engine de pace."
)


def get_run_volume(
    user_id: UUID,
    engine: VolumeEngine,
    *,
    start_date: datetime | None = None,
    end_date: datetime | None = None,
) -> RunVolumeResult:
    result = engine.get_run_volume(
        user_id, start_date=start_date, end_date=end_date
    )
    return volume_result_to_run_volume_result(result)


GET_RIDE_VOLUME_DESCRIPTION = (
    "Retorna o volume total de pedais (`Ride`) do usuário — soma de distâncias e contagem de "
    "atividades — opcionalmente filtrado por intervalo de datas. "
    "Use quando o usuário perguntar quanto pedalou, volume de ciclismo, "
    "distância acumulada pedalando, "
    "quantos km em um período, ou quantos pedais fez — com ou sem menção a período "
    "(semana, mês, ano, intervalo customizado). "
    "Quando o usuário mencionar um período, passe `start_date` e/ou `end_date` em ISO 8601 UTC. "
    "NÃO use para corridas (`get_run_volume`), recorde de pedal individual (`get_longest_ride`), "
    "natação ou elevação. "
    "Conversão intenção → parâmetros: "
    "'essa semana' → primeiro instante da semana corrente UTC (segunda 00:00) e último instante "
    "(domingo 23:59:59); "
    "'em 2024' → start_date=2024-01-01T00:00:00+00:00, end_date=2024-12-31T23:59:59+00:00; "
    "'neste mês' → primeiro e último instante do mês corrente UTC; "
    "'entre março e junho de 2024' → start_date=2024-03-01T00:00:00+00:00, "
    "end_date=2024-06-30T23:59:59+00:00; "
    "sem período → omitir start_date e end_date (histórico completo). "
    "Perguntas que DEVEM acionar: 'Quanto pedalei essa semana?', "
    "'Quantos km pedalei em 2024?', 'Qual meu volume total de pedal?', "
    "'Quantos pedais fiz neste mês?', "
    "'Qual a distância acumulada pedalando entre março e junho?'. "
    "Perguntas que NÃO devem acionar: 'Qual foi meu pedal mais longo?' → get_longest_ride; "
    "'Qual a maior distância que já pedalei?' → get_longest_ride; "
    "'Quanto corri essa semana?' → get_run_volume; "
    "'Quanto treinei no total?' (Run + Ride) → fora de escopo; "
    "'Qual minha velocidade média geral?' → engine de velocidade."
)


def get_ride_volume(
    user_id: UUID,
    engine: VolumeEngine,
    *,
    start_date: datetime | None = None,
    end_date: datetime | None = None,
) -> RideVolumeResult:
    result = engine.get_ride_volume(
        user_id, start_date=start_date, end_date=end_date
    )
    return volume_result_to_ride_volume_result(result)
