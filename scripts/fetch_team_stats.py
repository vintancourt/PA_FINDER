"""Busca (com cache) estatísticas de ataque/defesa de cada time por liga/temporada."""
import json
import time as _time
from datetime import datetime, timedelta

from scripts import config
from scripts.api_client import ApiClient, CallBudgetExceeded


def _cache_path(league_id: int, season: int, team_id: int):
    return config.TEAM_STATS_DIR / f"{league_id}_{season}_{team_id}.json"


def _is_fresh(path) -> bool:
    if not path.exists():
        return False
    data = json.loads(path.read_text())
    fetched_at = datetime.fromisoformat(data["_fetched_at"])
    return datetime.now() - fetched_at < timedelta(days=config.TEAM_STATS_CACHE_DAYS)


def _parse_stats(raw: dict) -> dict:
    """Extrai só os números que o modelo precisa, num formato simples."""
    goals = raw.get("goals", {})
    try:
        gf_home = float(goals["for"]["average"]["home"])
        gf_away = float(goals["for"]["average"]["away"])
        ga_home = float(goals["against"]["average"]["home"])
        ga_away = float(goals["against"]["average"]["away"])
    except (KeyError, TypeError, ValueError):
        gf_home = gf_away = ga_home = ga_away = 1.2  # fallback neutro

    return {
        "goals_for_avg_home": gf_home,
        "goals_for_avg_away": gf_away,
        "goals_against_avg_home": ga_home,
        "goals_against_avg_away": ga_away,
    }


def get_team_stats(client: ApiClient, league_id: int, season: int, team_id: int) -> dict | None:
    path = _cache_path(league_id, season, team_id)
    if _is_fresh(path):
        return json.loads(path.read_text())["stats"]

    try:
        payload = client.get(
            "/teams/statistics",
            params={"league": league_id, "season": season, "team": team_id},
        )
    except CallBudgetExceeded:
        raise
    except Exception as e:
        print(f"[fetch_team_stats] falhou time {team_id} liga {league_id}: {e}")
        return None

    raw = payload.get("response")
    if not raw:
        return None

    stats = _parse_stats(raw)
    path.write_text(json.dumps(
        {"_fetched_at": datetime.now().isoformat(), "stats": stats},
        ensure_ascii=False, indent=2,
    ))
    return stats
