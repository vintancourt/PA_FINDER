"""
Busca (com cache) médias de gols de cada time, calculadas a partir dos
últimos jogos disputados — com peso maior para os jogos mais recentes.

IMPORTANTE: o endpoint /teams/statistics é bloqueado no plano gratuito da
API-Football pra temporada atual ("Free plans do not have access to this
season"). Por isso calculamos as médias nós mesmos, a partir dos últimos
jogos do time via /fixtures?team=X&last=N — esse endpoint não tem essa
restrição, e pedir mais jogos não gasta cota extra (é 1 chamada de qualquer
forma).
"""
import json
from datetime import datetime, timedelta

from scripts import config
from scripts.api_client import ApiClient, CallBudgetExceeded

LAST_N_MATCHES = 30
FINISHED_STATUSES = "FT-AET-PEN"  # jogos encerrados (normal, prorrogação, pênaltis)
MIN_SPLIT_SAMPLES = 5  # mínimo de jogos em casa/fora pra usar a média separada

# Peso exponencial por recência: o jogo mais recente tem peso 1.0, e cada
# jogo mais antigo pesa RECENCY_DECAY vezes o anterior. Com 0.93, o jogo
# nº10 (contando do mais recente) ainda pesa ~48%, e o nº30 pesa ~11% —
# os últimos jogos dominam a média, mas os mais antigos não somem de vez.
RECENCY_DECAY = 0.93


def _cache_path(team_id: int):
    return config.TEAM_STATS_DIR / f"team_{team_id}.json"


def _is_fresh(path) -> bool:
    if not path.exists():
        return False
    data = json.loads(path.read_text())
    fetched_at = datetime.fromisoformat(data["_fetched_at"])
    return datetime.now() - fetched_at < timedelta(days=config.TEAM_STATS_CACHE_DAYS)


def _weighted_avg(pairs: list[tuple[float, float]], fallback: float) -> float:
    """pairs = [(valor, peso), ...]"""
    total_w = sum(w for _, w in pairs)
    if total_w == 0:
        return fallback
    return round(sum(v * w for v, w in pairs) / total_w, 3)


def _compute_stats(team_id: int, fixtures: list[dict]) -> dict:
    # ordena do mais recente pro mais antigo, pra atribuir os pesos certos
    def kickoff(fx):
        return fx.get("fixture", {}).get("date", "")

    fixtures = sorted(fixtures, key=kickoff, reverse=True)

    home_for, home_against = [], []
    away_for, away_against = [], []
    all_for, all_against = [], []

    for rank, fx in enumerate(fixtures):
        goals = fx.get("goals", {})
        gh, ga = goals.get("home"), goals.get("away")
        if gh is None or ga is None:
            continue

        weight = RECENCY_DECAY ** rank
        is_home = fx["teams"]["home"]["id"] == team_id
        team_goals = gh if is_home else ga
        opp_goals = ga if is_home else gh

        all_for.append((team_goals, weight))
        all_against.append((opp_goals, weight))
        if is_home:
            home_for.append((team_goals, weight))
            home_against.append((opp_goals, weight))
        else:
            away_for.append((team_goals, weight))
            away_against.append((opp_goals, weight))

    overall_for = _weighted_avg(all_for, 1.2)
    overall_against = _weighted_avg(all_against, 1.2)

    return {
        "goals_for_avg_home": _weighted_avg(home_for, overall_for) if len(home_for) >= MIN_SPLIT_SAMPLES else overall_for,
        "goals_against_avg_home": _weighted_avg(home_against, overall_against) if len(home_against) >= MIN_SPLIT_SAMPLES else overall_against,
        "goals_for_avg_away": _weighted_avg(away_for, overall_for) if len(away_for) >= MIN_SPLIT_SAMPLES else overall_for,
        "goals_against_avg_away": _weighted_avg(away_against, overall_against) if len(away_against) >= MIN_SPLIT_SAMPLES else overall_against,
        "sample_size": len(all_for),
    }


def get_team_stats(client: ApiClient, league_id: int, season: int, team_id: int) -> dict | None:
    """A assinatura mantém league_id/season por compatibilidade com quem
    chama, mas eles não são mais usados na consulta (evita a restrição de
    temporada do plano free)."""
    path = _cache_path(team_id)
    if _is_fresh(path):
        return json.loads(path.read_text())["stats"]

    try:
        payload = client.get(
            "/fixtures",
            params={"team": team_id, "last": LAST_N_MATCHES, "status": FINISHED_STATUSES},
        )
    except CallBudgetExceeded:
        raise
    except Exception as e:
        print(f"[fetch_team_stats] falhou time {team_id}: {e}")
        return None

    fixtures = payload.get("response") or []
    if not fixtures:
        print(f"[fetch_team_stats] sem jogos recentes pro time {team_id} — pulando")
        return None

    stats = _compute_stats(team_id, fixtures)
    path.write_text(json.dumps(
        {"_fetched_at": datetime.now().isoformat(), "stats": stats},
        ensure_ascii=False, indent=2,
    ))
    return stats
