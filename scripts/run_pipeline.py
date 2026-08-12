"""
Pipeline principal do PA Finder.

1. Busca todos os jogos de hoje + amanhã (2 chamadas de API).
2. Filtra só os campeonatos da whitelist (scripts/config.py).
3. Para cada jogo, busca (com cache) estatísticas dos dois times e calcula,
   via modelo de Poisson, os vereditos em texto de "duplo green" e "PA".
4. Salva um JSON consolidado (data/latest_ranking.json) e gera o site,
   agrupado por campeonato.

Sem consulta de odds (o usuário já usa outro programa pra isso) — isso deixa
praticamente toda a cota de API livre para estatísticas de time.
"""
import json
from datetime import datetime

from scripts import config
from scripts.api_client import ApiClient, CallBudgetExceeded
from scripts.fetch_fixtures import run as fetch_fixtures_run
from scripts.fetch_team_stats import get_team_stats
from scripts.league_filter import filter_fixtures
from scripts.model import score_fixture
from scripts.build_site import build


def main():
    client = ApiClient()

    try:
        fixtures = fetch_fixtures_run(client)
    except CallBudgetExceeded as e:
        print(f"[pipeline] {e}")
        return

    fixtures = filter_fixtures(fixtures)
    # processa na ordem da whitelist, e dentro de cada liga por horário do jogo
    fixtures.sort(key=lambda fx: (fx["_league_order"], fx["fixture"]["date"]))
    print(f"[pipeline] jogos dentro da whitelist a avaliar: {len(fixtures)}")

    scored = []
    skipped_no_stats = 0

    for fx in fixtures:
        league_id = fx.get("league", {}).get("id")
        season = fx.get("league", {}).get("season")
        home = fx.get("teams", {}).get("home", {})
        away = fx.get("teams", {}).get("away", {})
        if not (league_id and season and home.get("id") and away.get("id")):
            continue

        try:
            home_stats = get_team_stats(client, league_id, season, home["id"])
            away_stats = get_team_stats(client, league_id, season, away["id"])
        except CallBudgetExceeded:
            print("[pipeline] orçamento de API esgotado durante coleta de estatísticas — "
                  "parando aqui, o restante fica para a próxima execução (que já vai achar "
                  "esses times em cache, então o progresso não se perde).")
            break

        if not home_stats or not away_stats:
            skipped_no_stats += 1
            continue

        model_out = score_fixture(home_stats, away_stats, home["name"], away["name"])
        scored.append({
            "fixture_id": fx["fixture"]["id"],
            "kickoff_utc": fx["fixture"]["date"],
            "league_label": fx["_league_label"],
            "league_order": fx["_league_order"],
            "home_team": home["name"],
            "away_team": away["name"],
            "model": model_out,
        })

    print(f"[pipeline] jogos com estatísticas suficientes: {len(scored)} "
          f"(pulados por falta de dados: {skipped_no_stats})")

    output = {
        "generated_at": datetime.now().isoformat(),
        "calls_used": client.calls_used,
        "call_budget": client.budget,
        "total_fixtures_evaluated": len(scored),
        "ranking": scored,
    }
    out_path = config.DATA_DIR / "latest_ranking.json"
    out_path.write_text(json.dumps(output, ensure_ascii=False, indent=2))

    hist_path = config.HISTORY_DIR / f"ranking_{datetime.now().date().isoformat()}.json"
    hist_path.write_text(json.dumps(output, ensure_ascii=False, indent=2))

    print(f"[pipeline] chamadas de API usadas hoje: {client.calls_used}/{client.budget}")

    build(output)


if __name__ == "__main__":
    main()
