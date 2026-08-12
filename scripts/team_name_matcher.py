"""Casa o nome de um time (vindo da API-Football) com o ID equivalente na
football-data.org. As duas fontes usam sistemas de ID diferentes, então
comparamos por nome normalizado."""
import json
import re
import unicodedata
from datetime import datetime, timedelta

from scripts import config
from scripts.football_data_client import FootballDataClient

# Sufixos/prefixos comuns de nome de clube que atrapalham o casamento
# (ex.: API-Football às vezes manda "Manchester United", football-data
# manda "Manchester United FC").
_NOISE_TOKENS = {
    "fc", "cf", "afc", "sc", "ac", "cd", "cfc", "sad", "clube", "futebol",
    "club", "calcio", "spa", "srl", "sporting", "athletic", "atletico",
}


def normalize_name(name: str) -> str:
    name = unicodedata.normalize("NFKD", name or "").encode("ascii", "ignore").decode()
    name = name.lower()
    name = re.sub(r"[^a-z0-9\s]", " ", name)
    tokens = [t for t in name.split() if t not in _NOISE_TOKENS]
    return " ".join(tokens).strip()


def _index_cache_path(competition_code: str):
    return config.TEAM_STATS_DIR / f"fd_teams_{competition_code}.json"


def _is_fresh(path) -> bool:
    if not path.exists():
        return False
    data = json.loads(path.read_text())
    fetched_at = datetime.fromisoformat(data["_fetched_at"])
    return datetime.now() - fetched_at < timedelta(days=config.TEAM_STATS_CACHE_DAYS)


def get_competition_team_index(client: FootballDataClient, competition_code: str) -> dict[str, int]:
    """Retorna {nome_normalizado: id_na_football_data} pra uma competição."""
    path = _index_cache_path(competition_code)
    if _is_fresh(path):
        return json.loads(path.read_text())["index"]

    payload = client.get(f"/competitions/{competition_code}/teams")
    if not payload:
        return {}

    index = {}
    for team in payload.get("teams", []):
        norm = normalize_name(team.get("name", ""))
        if norm:
            index[norm] = team["id"]
        short_norm = normalize_name(team.get("shortName", ""))
        if short_norm and short_norm not in index:
            index[short_norm] = team["id"]

    path.write_text(json.dumps(
        {"_fetched_at": datetime.now().isoformat(), "index": index},
        ensure_ascii=False, indent=2,
    ))
    return index


def match_team_id(team_name: str, index: dict[str, int]) -> int | None:
    norm = normalize_name(team_name)
    if norm in index:
        return index[norm]
    # fallback: casamento parcial (um nome contém o outro)
    for candidate_name, team_id in index.items():
        if norm in candidate_name or candidate_name in norm:
            return team_id
    return None
