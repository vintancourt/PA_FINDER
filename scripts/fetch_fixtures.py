"""Busca todos os jogos (todas as ligas) de hoje e de amanhã."""
import json
from datetime import date, timedelta

from scripts import config
from scripts.api_client import ApiClient


def fetch_fixtures_for_date(client: ApiClient, iso_date: str) -> list[dict]:
    """Uma única chamada traz TODOS os jogos do mundo naquela data."""
    payload = client.get("/fixtures", params={"date": iso_date})
    return payload.get("response", [])


def run(client: ApiClient) -> list[dict]:
    today = date.today()
    tomorrow = today + timedelta(days=1)

    all_fixtures = []
    for d in (today, tomorrow):
        iso = d.isoformat()
        fixtures = fetch_fixtures_for_date(client, iso)
        print(f"[fetch_fixtures] {iso}: {len(fixtures)} jogos encontrados")
        all_fixtures.extend(fixtures)

    out_path = config.DATA_DIR / "latest_fixtures.json"
    out_path.write_text(json.dumps(all_fixtures, ensure_ascii=False, indent=2))

    # Também guarda um snapshot histórico por dia, para a base de dados crescer.
    snap_path = config.HISTORY_DIR / f"fixtures_{today.isoformat()}.json"
    if not snap_path.exists():
        snap_path.write_text(json.dumps(all_fixtures, ensure_ascii=False, indent=2))

    return all_fixtures


if __name__ == "__main__":
    c = ApiClient()
    run(c)
    print(f"[fetch_fixtures] chamadas usadas: {c.calls_used}")
