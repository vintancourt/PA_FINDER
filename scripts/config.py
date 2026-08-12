"""
Configurações centrais do PA Finder.

Todas as chaves sensíveis vêm de variáveis de ambiente (nunca hardcode aqui).
No GitHub Actions, configure o secret API_FOOTBALL_KEY em:
  Settings > Secrets and variables > Actions > New repository secret
"""
import os
from pathlib import Path


def _int_env(key: str, default: str) -> int:
    """Como os.environ.get, mas trata variável vazia ("") como se não
    existisse — o GitHub Actions manda "" quando uma Variable não foi
    criada, em vez de simplesmente omitir a variável."""
    value = os.environ.get(key, "").strip()
    return int(value) if value else int(default)


def _str_env(key: str, default: str) -> str:
    """Mesma ideia de _int_env, mas para strings."""
    value = os.environ.get(key, "").strip()
    return value if value else default


# --- API-Football (api-football.com / api-sports.io) ---
API_FOOTBALL_KEY = _str_env("API_FOOTBALL_KEY", "")
API_BASE_URL = _str_env("API_FOOTBALL_BASE_URL", "https://v3.football.api-sports.io")
API_HEADERS = {"x-apisports-key": API_FOOTBALL_KEY}

# Se o usuário preferir usar via RapidAPI em vez do endpoint direto,
# defina API_FOOTBALL_BASE_URL=https://api-football-v1.p.rapidapi.com/v3
# e API_FOOTBALL_RAPIDAPI_HOST=api-football-v1.p.rapidapi.com nos secrets,
# e o código ajusta o header automaticamente:
_RAPIDAPI_HOST = _str_env("API_FOOTBALL_RAPIDAPI_HOST", "")
if _RAPIDAPI_HOST:
    API_HEADERS = {
        "x-rapidapi-key": API_FOOTBALL_KEY,
        "x-rapidapi-host": _RAPIDAPI_HOST,
    }

# --- football-data.org (fonte gratuita de HISTÓRICO de jogos) ---
# A API-Football bloqueia, no plano free, qualquer forma de puxar jogos
# passados (nem por "season" nem por "last"). A football-data.org tem um
# plano free permanente que libera histórico de verdade, mas só pra 12
# competições (majoritariamente ligas europeias grandes). Por isso usamos
# ela só pra calcular as médias de gols dessas ligas específicas; o resto
# continua aparecendo no site, só que sem veredito estatístico.
# Cadastro grátis em: https://www.football-data.org/client/register
FOOTBALL_DATA_KEY = _str_env("FOOTBALL_DATA_API_KEY", "")
FOOTBALL_DATA_BASE_URL = "https://api.football-data.org/v4"

# rótulo (igual ao "label" em LEAGUE_WHITELIST) -> código da competição na
# football-data.org
FOOTBALL_DATA_COMPETITIONS: dict[str, str] = {
    "Brasileirão Série A": "BSA",
    "Premier League": "PL",
    "Championship (Inglaterra)": "ELC",
    "LaLiga": "PD",
    "Bundesliga": "BL1",
    "Ligue 1": "FL1",
    "Série A": "SA",
    "Liga Portugal": "PPL",
    "Champions League": "CL",
    "Copa do Mundo 2026": "WC",
}

# --- Orçamento de chamadas (plano free = 100 req/dia) ---
# Deixamos uma margem de segurança porque outras automações podem usar a mesma chave.
DAILY_CALL_BUDGET = _int_env("DAILY_CALL_BUDGET", "90")

# Sem consulta de odds nesse projeto (o usuário já usa outro programa pra odds).
# Isso libera praticamente toda a cota pra estatísticas de time.

# --- Diretórios ---
ROOT_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT_DIR / "data"
TEAM_STATS_DIR = DATA_DIR / "team_stats"
HISTORY_DIR = DATA_DIR / "history"
DOCS_DIR = ROOT_DIR / "docs"

for d in (DATA_DIR, TEAM_STATS_DIR, HISTORY_DIR, DOCS_DIR):
    d.mkdir(parents=True, exist_ok=True)

# --- Regras do modelo ---
# Cache de estatísticas de time válido por N dias (evita gastar cota repetindo).
TEAM_STATS_CACHE_DAYS = _int_env("TEAM_STATS_CACHE_DAYS", "3")

# Linhas de gol usadas como "gatilho típico de PA" nas casas (ajustável).
PA_LEAD_THRESHOLDS = [2, 3]  # ex: chance de abrir vantagem de 2 ou 3 gols

# --- Limiares dos vereditos em texto (ajuste livre conforme seu histórico) ---
# "Duplo green" = o jogo favorece muito a estratégia de PA + proteção
# (favorito com alta chance de abrir vantagem folgada).
DUPLO_GREEN_ALTA = 0.50      # >= disso: "GRANDE CHANCE DE DUPLO GREEN"
DUPLO_GREEN_MODERADA = 0.28  # >= disso (e < ALTA): "CHANCE MODERADA DE DUPLO GREEN"
                              # abaixo disso: "CHANCE QUASE NULA DE DUPLO GREEN"

PA_FORTE = 0.45       # chance mínima do favorito p/ "PEGAR PA NESSE TIME" (recomendação forte)
PA_MODERADA = 0.30    # chance mínima p/ recomendação moderada
PA_DIFF_DOMINANCIA = 0.15  # diferença mínima entre os dois lados p/ considerar "um time só"
# Se os dois lados ficam próximos e ambos >= PA_MODERADA: "BOM PEGAR PA NOS DOIS TIMES"

# --- Campeonatos cobertos (whitelist) ---
# Cada item: rótulo pra exibir + aliases de nome (como a API-Football costuma
# retornar em fixture["league"]["name"]) + país opcional pra desambiguar
# (ex.: "Série A" sozinho seria ambíguo entre Brasil e Itália).
# A ordem da lista também define a ordem de prioridade quando a cota aperta,
# e a ordem de exibição no site.
LEAGUE_WHITELIST: list[dict] = [
    {"label": "Brasileirão Série A", "name_aliases": ["Serie A"], "country": "Brazil"},
    {"label": "Brasileirão Série B", "name_aliases": ["Serie B"], "country": "Brazil"},
    {"label": "Copa do Brasil", "name_aliases": ["Copa do Brasil"], "country": "Brazil"},
    {"label": "Copa Libertadores", "name_aliases": ["Copa Libertadores"], "country": None},
    {"label": "Copa Sudamericana", "name_aliases": ["Copa Sudamericana"], "country": None},
    {"label": "Premier League", "name_aliases": ["Premier League"], "country": "England"},
    {"label": "Championship (Inglaterra)", "name_aliases": ["Championship"], "country": "England"},
    {"label": "LaLiga", "name_aliases": ["La Liga", "LaLiga"], "country": "Spain"},
    {"label": "LaLiga 2", "name_aliases": ["Segunda Division", "Segunda División", "LaLiga2", "La Liga 2"], "country": "Spain"},
    {"label": "Bundesliga", "name_aliases": ["Bundesliga"], "country": "Germany"},
    {"label": "2. Bundesliga", "name_aliases": ["2. Bundesliga", "2 Bundesliga"], "country": "Germany"},
    {"label": "Ligue 1", "name_aliases": ["Ligue 1"], "country": "France"},
    {"label": "Série A", "name_aliases": ["Serie A"], "country": "Italy"},
    {"label": "Liga Portugal", "name_aliases": ["Primeira Liga", "Liga Portugal"], "country": "Portugal"},
    {"label": "SuperLig (Turquia)", "name_aliases": ["Super Lig", "Süper Lig"], "country": "Turkey"},
    {"label": "Eliteserien", "name_aliases": ["Eliteserien"], "country": "Norway"},
    {"label": "Allsvenskan", "name_aliases": ["Allsvenskan"], "country": "Sweden"},
    {"label": "Champions League", "name_aliases": ["UEFA Champions League", "Champions League"], "country": None},
    {"label": "Europa League", "name_aliases": ["UEFA Europa League", "Europa League"], "country": None},
    {"label": "Conference League", "name_aliases": ["UEFA Europa Conference League", "Conference League"], "country": None},
    {"label": "Copa do Mundo 2026", "name_aliases": ["World Cup"], "country": None},
    {"label": "Copa Centro-Americana CONCACAF", "name_aliases": ["Central American Cup", "CONCACAF Central American Cup"], "country": None},
    {"label": "Copa das Ligas", "name_aliases": ["Leagues Cup"], "country": None},
    {"label": "MLS", "name_aliases": ["MLS", "Major League Soccer"], "country": "USA"},
    {"label": "Liga MX", "name_aliases": ["Liga MX"], "country": "Mexico"},
    {"label": "Liga Profesional de Fútbol", "name_aliases": ["Liga Profesional Argentina", "Primera Division", "Primera División"], "country": "Argentina"},
    {"label": "J1 (Japão)", "name_aliases": ["J1 League"], "country": "Japan"},
    {"label": "Superliga (China)", "name_aliases": ["Super League"], "country": "China"},
]
