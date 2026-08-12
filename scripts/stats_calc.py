"""Cálculo de médias de gols ponderadas por recência, a partir de uma lista
genérica de jogos já finalizados (independente da fonte de dados)."""

MIN_SPLIT_SAMPLES = 5  # mínimo de jogos em casa/fora pra usar a média separada

# Peso exponencial por recência: o jogo mais recente pesa 1.0, e cada jogo
# mais antigo pesa RECENCY_DECAY vezes o anterior. Com 0.93, o jogo nº10
# (contando do mais recente) ainda pesa ~48%, e o nº30 pesa ~11%.
RECENCY_DECAY = 0.93


def _weighted_avg(pairs: list[tuple[float, float]], fallback: float) -> float:
    total_w = sum(w for _, w in pairs)
    if total_w == 0:
        return fallback
    return round(sum(v * w for v, w in pairs) / total_w, 3)


def compute_weighted_stats(team_id, matches: list[dict]) -> dict:
    """matches: lista de dicts com date (iso str), home_id, away_id,
    home_goals, away_goals — já ordenáveis por data."""
    matches = sorted(matches, key=lambda m: m["date"], reverse=True)

    home_for, home_against = [], []
    away_for, away_against = [], []
    all_for, all_against = [], []

    for rank, m in enumerate(matches):
        gh, ga = m.get("home_goals"), m.get("away_goals")
        if gh is None or ga is None:
            continue

        weight = RECENCY_DECAY ** rank
        is_home = m["home_id"] == team_id
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
