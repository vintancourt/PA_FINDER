"""Busca odds de mercado (1x2 e handicap asiático) para os melhores candidatos."""
from scripts.api_client import ApiClient, CallBudgetExceeded


def _implied_prob_no_vig(odds_list: list[float]) -> list[float]:
    """Remove a margem da casa (overround) das odds decimais."""
    raw = [1 / o for o in odds_list if o and o > 0]
    total = sum(raw)
    if total == 0:
        return [0.0 for _ in odds_list]
    return [r / total for r in raw]


def get_match_winner_odds(client: ApiClient, fixture_id: int) -> dict | None:
    try:
        payload = client.get("/odds", params={"fixture": fixture_id})
    except CallBudgetExceeded:
        raise
    except Exception as e:
        print(f"[fetch_odds] falhou fixture {fixture_id}: {e}")
        return None

    response = payload.get("response") or []
    if not response:
        return None

    for bookmaker_block in response[0].get("bookmakers", []):
        for bet in bookmaker_block.get("bets", []):
            if bet.get("name") in ("Match Winner", "1X2"):
                values = {v["value"]: float(v["odd"]) for v in bet.get("values", [])}
                home_o = values.get("Home")
                draw_o = values.get("Draw")
                away_o = values.get("Away")
                if home_o and draw_o and away_o:
                    p_home, p_draw, p_away = _implied_prob_no_vig([home_o, draw_o, away_o])
                    return {
                        "bookmaker": bookmaker_block.get("name"),
                        "odd_home": home_o,
                        "odd_draw": draw_o,
                        "odd_away": away_o,
                        "implied_prob_home": round(p_home, 4),
                        "implied_prob_draw": round(p_draw, 4),
                        "implied_prob_away": round(p_away, 4),
                    }
    return None
