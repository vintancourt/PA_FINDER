"""Cliente HTTP para a football-data.org — fonte gratuita de histórico
pras ~10 ligas grandes que ela cobre. O limite dela é 10 requisições por
MINUTO (não por dia), então em vez de um orçamento diário, controlamos o
ritmo entre chamadas."""
import time
import requests
from scripts import config

# 10 req/min = 1 a cada 6s. Usamos 6.5s de folga de segurança.
_PACE_SECONDS = 6.5

# Trava de segurança pra não rodar indefinidamente num dia com muitíssimos
# jogos nas ligas cobertas (não é um limite oficial da API, é só um teto
# nosso de bom senso pro tempo de execução do workflow).
MAX_CALLS_PER_RUN = 200


class FootballDataClient:
    def __init__(self):
        self.calls_used = 0

    def get(self, path: str, params: dict | None = None) -> dict | None:
        if not config.FOOTBALL_DATA_KEY:
            return None
        if self.calls_used >= MAX_CALLS_PER_RUN:
            print("[football_data_client] teto de chamadas da execução atingido, parando por hoje.")
            return None

        url = f"{config.FOOTBALL_DATA_BASE_URL}{path}"
        headers = {"X-Auth-Token": config.FOOTBALL_DATA_KEY}
        try:
            resp = requests.get(url, headers=headers, params=params or {}, timeout=30)
        except Exception as e:
            print(f"[football_data_client] erro de rede em {path}: {e}")
            return None

        self.calls_used += 1
        time.sleep(_PACE_SECONDS)

        if resp.status_code == 429:
            print("[football_data_client] rate limit atingido, pulando essa chamada.")
            return None
        if resp.status_code != 200:
            print(f"[football_data_client] aviso em {path}: status {resp.status_code}")
            return None

        return resp.json()
