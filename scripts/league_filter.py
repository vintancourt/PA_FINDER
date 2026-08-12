"""Filtra a lista bruta de jogos, mantendo só os campeonatos da whitelist."""
from scripts import config


def _normalize(s: str) -> str:
    return (s or "").strip().lower()


def match_league(fx_league_name: str, fx_country: str) -> dict | None:
    """Retorna a entrada da whitelist que casa com esse jogo, ou None."""
    name_norm = _normalize(fx_league_name)
    country_norm = _normalize(fx_country)

    for entry in config.LEAGUE_WHITELIST:
        aliases_norm = [_normalize(a) for a in entry["name_aliases"]]
        if name_norm not in aliases_norm:
            continue
        required_country = entry.get("country")
        if required_country and _normalize(required_country) != country_norm:
            continue
        return entry
    return None


def filter_fixtures(fixtures: list[dict]) -> list[dict]:
    """Mantém só jogos de campeonatos na whitelist e anota o rótulo/ordem."""
    kept = []
    unmatched_leagues = set()

    label_order = {entry["label"]: i for i, entry in enumerate(config.LEAGUE_WHITELIST)}

    for fx in fixtures:
        league = fx.get("league", {})
        entry = match_league(league.get("name", ""), league.get("country", ""))
        if entry is None:
            unmatched_leagues.add(f'{league.get("name")} ({league.get("country")})')
            continue
        fx["_league_label"] = entry["label"]
        fx["_league_order"] = label_order[entry["label"]]
        kept.append(fx)

    if unmatched_leagues:
        print(f"[league_filter] {len(unmatched_leagues)} campeonatos fora da whitelist "
              f"foram ignorados (normal). Exemplos: {sorted(unmatched_leagues)[:5]}")

    matched_labels = {fx["_league_label"] for fx in kept}
    missing = [e["label"] for e in config.LEAGUE_WHITELIST if e["label"] not in matched_labels]
    if missing:
        print(f"[league_filter] aviso: nenhum jogo encontrado hoje/amanhã para: {missing} "
              "— pode ser normal (sem jogos nesses dias) ou os aliases em config.py "
              "precisam de ajuste.")

    return kept
