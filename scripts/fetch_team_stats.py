"""
Busca (com cache) médias de gols de cada time, usando football-data.org
como fonte de histórico — só disponível pras ligas em
config.FOOTBALL_DATA_COMPETITIONS (veja o motivo em config.py).

Pra ligas fora dessa lista, retorna None (o pipeline mostra o jogo mesmo
assim, só que sem veredito estatístico).
"""
import json
from datetime import datetime, timedelta, date

from scripts import config
from scripts import stats_calc
from scripts.football_data_client import FootballDataClient
from scripts.team_name_matcher import get_competition_team_index, match_team_id

MATCH_HISTORY_DAYS = 220  # ~7 meses pra trás, o suficiente pra pegar uns 30 jogos


def _cache_path(fd_team_id: int):
    return config.TEAM_STATS_DIR / f"fd_stats_{fd_team_id}.json"


def _is_fresh(path) -> bool:
    if not path.exists():
        return False
    data = json.loads(path.read_text())
    fetched_at = datetime.fromisoformat(data["_fetched_at"])
    return datetime.now() - fetched_at < timedelta(days=config.TEAM_STATS_CACHE_DAYS)


def _fetch_recent_matches(client: FootballDataClient, fd_team_id: int) -> list[dict]:
    date_from = (date.today() - timedelta(days=MATCH_HISTORY_DAYS)).isoformat()
    date_to = date.today().isoformat()
    payload = client.get(
        f"/teams/{fd_team_id}/matches",
        params={"status": "FINISHED", "dateFrom": date_from, "dateTo": date_to},
    )
    if not payload:
        return []

    matches = []
    for m in payload.get("matches", []):
        score = m.get("score", {}).get("fullTime", {})
        matches.append({
            "date": m.get("utcDate", ""),
            "home_id": m.get("homeTeam", {}).get("id"),
            "away_id": m.get("awayTeam", {}).get("id"),
            "home_goals": score.get("home"),
            "away_goals": score.get("away"),
        })
    # mais recentes primeiro, pega só os últimos 30
    matches.sort(key=lambda m: m["date"], reverse=True)
    return matches[:30]


def get_team_stats(client: FootballDataClient, league_label: str, team_name: str) -> dict | None:
    competition_code = config.FOOTBALL_DATA_COMPETITIONS.get(league_label)
    if not competition_code:
        return None  # liga fora da cobertura gratuita

    team_index = get_competition_team_index(client, competition_code)
    if not team_index:
        return None

    fd_team_id = match_team_id(team_name, team_index)
    if fd_team_id is None:
        print(f"[fetch_team_stats] não achei '{team_name}' na football-data.org ({competition_code})")
        return None

    path = _cache_path(fd_team_id)
    if _is_fresh(path):
        return json.loads(path.read_text())["stats"]

    matches = _fetch_recent_matches(client, fd_team_id)
    if not matches:
        return None

    stats = stats_calc.compute_weighted_stats(fd_team_id, matches)
    path.write_text(json.dumps(
        {"_fetched_at": datetime.now().isoformat(), "stats": stats},
        ensure_ascii=False, indent=2,
    ))
    return stats
