"""
Modelo estatístico simples (Poisson) para estimar a chance de um time abrir
uma vantagem de N gols numa partida — usado como proxy para "chance de bater
o gatilho de Pagamento Antecipado" das casas de aposta.

IMPORTANTE: isso é uma estimativa estatística baseada em médias de gols,
não uma garantia. As casas variam a regra exata de PA (algumas pagam com
2 gols de vantagem, outras só com 3, algumas só na 2ª etapa, etc).
Use o resultado como ranking/priorização, não como certeza.
"""
import math

from scripts import config

MAX_GOALS = 8  # grade de gols considerada (0..8) — cobre >99.9% dos casos reais


def poisson_pmf(k: int, lam: float) -> float:
    if lam <= 0:
        return 1.0 if k == 0 else 0.0
    return math.exp(-lam) * (lam ** k) / math.factorial(k)


def goal_diff_distribution(lambda_home: float, lambda_away: float) -> dict[int, float]:
    """Distribuição de probabilidade da diferença de gols (casa - fora)."""
    dist: dict[int, float] = {}
    for gh in range(MAX_GOALS + 1):
        ph = poisson_pmf(gh, lambda_home)
        for ga in range(MAX_GOALS + 1):
            pa = poisson_pmf(ga, lambda_away)
            diff = gh - ga
            dist[diff] = dist.get(diff, 0.0) + ph * pa
    return dist


def prob_lead_at_least(dist: dict[int, float], n: int, side: str) -> float:
    """Probabilidade de o placar final ter vantagem >= n gols para um lado.

    Isso é usado como PROXY do "abrir vantagem de N gols em algum momento do
    jogo" — na prática a chance de bater o gatilho durante o jogo costuma ser
    um pouco MAIOR que a chance do placar final ter essa margem (times abrem
    vantagem e depois o rival descontam). Aplicamos um pequeno fator de ajuste.
    """
    if side == "home":
        p_final = sum(p for d, p in dist.items() if d >= n)
    else:
        p_final = sum(p for d, p in dist.items() if d <= -n)

    # Fator de ajuste empírico (heurístico): abrir a vantagem "em algum
    # momento" é mais fácil do que terminar o jogo com ela. Fator maior para
    # margens menores (2 gols é mais comum de acontecer e depois cair para 1).
    adjustment = {2: 1.35, 3: 1.55}.get(n, 1.25)
    return min(p_final * adjustment, 0.97)


def expected_goals(home_stats: dict, away_stats: dict) -> tuple[float, float]:
    """Estima gols esperados combinando ataque de um time com defesa do outro.

    home_stats / away_stats vêm do endpoint /teams/statistics da API-Football,
    já filtrados para home.average / away.average de goals for/against.
    """
    home_attack = home_stats.get("goals_for_avg_home", 1.2)
    home_defense = home_stats.get("goals_against_avg_home", 1.2)
    away_attack = away_stats.get("goals_for_avg_away", 1.0)
    away_defense = away_stats.get("goals_against_avg_away", 1.4)

    lambda_home = (home_attack + away_defense) / 2
    lambda_away = (away_attack + home_defense) / 2

    # trava valores extremos (dados incompletos no início de temporada etc.)
    lambda_home = max(0.3, min(lambda_home, 4.5))
    lambda_away = max(0.3, min(lambda_away, 4.5))
    return lambda_home, lambda_away


def classify_duplo_green(best_p2: float) -> str:
    """Veredito em texto sobre a chance de 'duplo green' do jogo (o lado
    mais forte entre os dois times abrir vantagem de 2+ gols)."""
    if best_p2 >= config.DUPLO_GREEN_ALTA:
        return "GRANDE CHANCE DE DUPLO GREEN"
    if best_p2 >= config.DUPLO_GREEN_MODERADA:
        return "CHANCE MODERADA DE DUPLO GREEN"
    return "CHANCE QUASE NULA DE DUPLO GREEN"


def classify_pa(p_home_2: float, p_away_2: float, home_team: str, away_team: str) -> dict:
    """Veredito em texto sobre em qual time (ou times) vale a pena pegar PA."""
    diff = abs(p_home_2 - p_away_2)
    stronger_team = home_team if p_home_2 >= p_away_2 else away_team
    stronger_p = max(p_home_2, p_away_2)

    if stronger_p >= config.PA_FORTE and diff >= config.PA_DIFF_DOMINANCIA:
        return {"label": f"PEGAR PA NESSE TIME: {stronger_team}", "tier": "forte"}

    if p_home_2 >= config.PA_MODERADA and p_away_2 >= config.PA_MODERADA and diff < config.PA_DIFF_DOMINANCIA:
        return {"label": "BOM PEGAR PA NOS DOIS TIMES", "tier": "duplo"}

    if stronger_p >= config.PA_MODERADA:
        return {"label": f"PEGAR PA NESSE TIME: {stronger_team}", "tier": "moderado"}

    return {"label": "EVITAR PA NESSE JOGO", "tier": "evitar"}


def score_fixture(home_stats: dict, away_stats: dict, home_team: str, away_team: str) -> dict:
    """Calcula o veredito estatístico (sem odds) para um confronto."""
    lambda_home, lambda_away = expected_goals(home_stats, away_stats)
    dist = goal_diff_distribution(lambda_home, lambda_away)

    p_home_2 = prob_lead_at_least(dist, 2, "home")
    p_home_3 = prob_lead_at_least(dist, 3, "home")
    p_away_2 = prob_lead_at_least(dist, 2, "away")
    p_away_3 = prob_lead_at_least(dist, 3, "away")

    best_p2 = max(p_home_2, p_away_2)
    best_p3 = max(p_home_3, p_away_3)
    favorite_side = "home" if p_home_2 >= p_away_2 else "away"

    pa_verdict = classify_pa(p_home_2, p_away_2, home_team, away_team)

    return {
        "lambda_home": round(lambda_home, 2),
        "lambda_away": round(lambda_away, 2),
        "favorite_side": favorite_side,
        "prob_lead_2_home": round(p_home_2, 4),
        "prob_lead_2_away": round(p_away_2, 4),
        "prob_lead_3_home": round(p_home_3, 4),
        "prob_lead_3_away": round(p_away_3, 4),
        "duplo_green_label": classify_duplo_green(best_p2),
        "pa_label": pa_verdict["label"],
        "pa_tier": pa_verdict["tier"],
        # score bruto usado só pra ordenar dentro de cada liga (mais forte primeiro).
        "raw_score": round(best_p2 * 0.7 + best_p3 * 0.3, 4),
    }
