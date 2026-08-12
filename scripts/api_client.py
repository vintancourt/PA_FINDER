"""Cliente HTTP simples para a API-Football, com contador de chamadas."""
import time
import requests
from scripts import config


class CallBudgetExceeded(Exception):
    pass


class ApiClient:
    def __init__(self, budget: int = config.DAILY_CALL_BUDGET):
        self.budget = budget
        self.calls_used = 0

    def get(self, path: str, params: dict | None = None) -> dict:
        if self.calls_used >= self.budget:
            raise CallBudgetExceeded(
                f"Orçamento de {self.budget} chamadas/dia atingido. "
                "Rode novamente amanhã ou aumente DAILY_CALL_BUDGET."
            )
        if not config.API_FOOTBALL_KEY:
            raise RuntimeError(
                "API_FOOTBALL_KEY não configurada. Defina a variável de ambiente "
                "ou o secret do GitHub Actions."
            )

        url = f"{config.API_BASE_URL}{path}"
        resp = requests.get(url, headers=config.API_HEADERS, params=params or {}, timeout=30)
        self.calls_used += 1
        resp.raise_for_status()
        payload = resp.json()

        errors = payload.get("errors")
        if errors:
            # A API retorna 200 mesmo com erro de cota/plano às vezes; log e segue.
            print(f"[api_client] aviso da API em {path}: {errors}")

        # Educado com o rate limit por segundo do plano free (~10 req/min costuma bastar).
        time.sleep(0.35)
        return payload
