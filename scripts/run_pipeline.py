"""
Pipeline principal do PA Finder.

1. Busca todos os jogos de hoje + amanhã na API-Football (2 chamadas).
2. Filtra só os campeonatos da whitelist.
3. Pra cada jogo, tenta calcular o veredito estatístico usando histórico da
   football-data.org — só disponível pras ~10 ligas grandes que ela cobre
   de graça (config.FOOTBALL_DATA_COMPETITIONS). Fora dessas, o jogo ainda
   aparece no site, só que marcado como "sem dados suficientes".
4. Gera docs/index.html, agrupado por campeonato.
"""
import json
from datetime import datetime

from scripts import config
from scripts.api_client import ApiClient, CallBudgetExceeded
from scripts.fetch_fixtures import run as fetch_fixtures_run
from scripts.fetch_team_stats import get_team_stats
from scripts.football_data_client import FootballDataClient
from scripts.league_filter import filter_fixtures
from scripts.model import score_fixture, no_data_model
from scripts.build_site import build


def main():
    client = ApiClient()
    fd_client = FootballDataClient()

    if not config.FOOTBALL_DATA_KEY:
        print("[pipeline] aviso: FOOTBALL_DATA_API_KEY não configurada — "
              "todos os jogos vão aparecer sem veredito estatístico. "
              "Crie uma chave grátis em football-data.org/client/register "
              "e adicione como secret no GitHub Actions.")

    try:
        fixtures = fetch_fixtures_run(client)
    except CallBudgetExceeded as e:
        print(f"[pipeline] {e}")
        return

    fixtures = filter_fixtures(fixtures)
    fixtures.sort(key=lambda fx: (fx["_league_order"], fx["fixture"]["date"]))
    print(f"[pipeline] jogos dentro da whitelist a avaliar: {len(fixtures)}")

    scored = []
    with_data = 0

    for fx in fixtures:
        home = fx.get("teams", {}).get("home", {})
        away = fx.get("teams", {}).get("away", {})
        if not (home.get("id") and away.get("id")):
            continue

        league_label = fx["_league_label"]
        home_stats = get_team_stats(fd_client, league_label, home["name"])
        away_stats = get_team_stats(fd_client, league_label, away["name"])

        if home_stats and away_stats:
            model_out = score_fixture(home_stats, away_stats, home["name"], away["name"])
            with_data += 1
        else:
            model_out = no_data_model()

        scored.append({
            "fixture_id": fx["fixture"]["id"],
            "kickoff_utc": fx["fixture"]["date"],
            "league_label": league_label,
            "league_order": fx["_league_order"],
            "home_team": home["name"],
            "away_team": away["name"],
            "model": model_out,
        })

    print(f"[pipeline] jogos com veredito estatístico: {with_data} de {len(scored)} "
          f"(o resto aparece como 'sem dados suficientes' — normal pras ligas fora "
          f"da cobertura gratuita da football-data.org)")

    output = {
        "generated_at": datetime.now().isoformat(),
        "calls_used": client.calls_used,
        "call_budget": client.budget,
        "fd_calls_used": fd_client.calls_used,
        "total_fixtures_evaluated": len(scored),
        "ranking": scored,
    }
    out_path = config.DATA_DIR / "latest_ranking.json"
    out_path.write_text(json.dumps(output, ensure_ascii=False, indent=2))

    hist_path = config.HISTORY_DIR / f"ranking_{datetime.now().date().isoformat()}.json"
    hist_path.write_text(json.dumps(output, ensure_ascii=False, indent=2))

    print(f"[pipeline] chamadas API-Football: {client.calls_used}/{client.budget} · "
          f"chamadas football-data.org: {fd_client.calls_used}")

    build(output)


if __name__ == "__main__":
    main()
