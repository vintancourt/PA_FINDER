"""Gera o site estático (docs/index.html), agrupado por campeonato,
mostrando vereditos em texto ('duplo green' e 'PA') em vez de números."""
import html
from collections import defaultdict
from datetime import datetime, timezone

from scripts import config

DUPLO_GREEN_CSS = {
    "GRANDE CHANCE DE DUPLO GREEN": "hi",
    "CHANCE MODERADA DE DUPLO GREEN": "mid",
    "CHANCE QUASE NULA DE DUPLO GREEN": "lo",
}
PA_TIER_CSS = {
    "forte": "hi",
    "duplo": "blue",
    "moderado": "mid",
    "evitar": "lo",
}


def _fmt_kickoff(iso_str: str) -> str:
    try:
        dt = datetime.fromisoformat(iso_str.replace("Z", "+00:00"))
        return dt.astimezone().strftime("%d/%m %H:%M")
    except Exception:
        return iso_str


def _match_row(row: dict) -> str:
    m = row["model"]
    dg_label = m["duplo_green_label"]
    dg_css = DUPLO_GREEN_CSS.get(dg_label, "lo")
    pa_css = PA_TIER_CSS.get(m["pa_tier"], "lo")

    tooltip = (
        f'+2 gols: casa {m["prob_lead_2_home"]:.0%} / fora {m["prob_lead_2_away"]:.0%} · '
        f'+3 gols: casa {m["prob_lead_3_home"]:.0%} / fora {m["prob_lead_3_away"]:.0%}'
    )

    return f'''<div class="match-row conf-{dg_css}" title="{html.escape(tooltip)}">
      <div class="mr-time">{_fmt_kickoff(row["kickoff_utc"])}</div>
      <div class="mr-teams">{html.escape(row["home_team"])} <span class="vs">x</span> {html.escape(row["away_team"])}</div>
      <div class="mr-badges">
        <span class="badge badge-{dg_css}">{dg_label}</span>
        <span class="badge badge-{pa_css}">{html.escape(m["pa_label"])}</span>
      </div>
    </div>'''


def _league_card(league_label: str, rows: list[dict], open_first: bool) -> str:
    matches_html = "\n".join(_match_row(r) for r in rows)
    open_attr = " open" if open_first else ""
    return f'''<details class="league-card"{open_attr}>
      <summary>
        <span class="league-dot"></span>
        <span class="league-name">{html.escape(league_label)}</span>
        <span class="league-count">{len(rows)} jogos</span>
        <span class="chevron">&#9662;</span>
      </summary>
      <div class="league-matches">
        {matches_html}
      </div>
    </details>'''


def build(output: dict) -> None:
    ranking = output["ranking"]
    generated = datetime.now(timezone.utc).astimezone().strftime("%d/%m/%Y %H:%M")

    grouped: dict[str, list[dict]] = defaultdict(list)
    order_by_label: dict[str, int] = {}
    for row in ranking:
        grouped[row["league_label"]].append(row)
        order_by_label[row["league_label"]] = row["league_order"]

    ordered_labels = sorted(grouped.keys(), key=lambda lbl: order_by_label[lbl])

    cards_html = "\n".join(
        _league_card(label, grouped[label], open_first=(i == 0))
        for i, label in enumerate(ordered_labels)
    )
    if not cards_html:
        cards_html = '<p class="empty">Nenhum jogo encontrado nos campeonatos configurados para hoje/amanhã.</p>'

    html_doc = f'''<!DOCTYPE html>
<html lang="pt-BR">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>PA Finder — Radar diário de Pagamento Antecipado</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@500;700&family=IBM+Plex+Mono:wght@400;500;600&display=swap" rel="stylesheet">
<style>
  :root {{
    --bg: #0B0E11;
    --panel: #11161B;
    --panel-2: #161C22;
    --line: #232A31;
    --text: #E7ECEF;
    --muted: #7C8792;
    --hi: #3ECF8E;
    --mid: #E8B94E;
    --lo: #566270;
    --blue: #4EA1E8;
  }}
  * {{ box-sizing: border-box; }}
  body {{
    margin: 0;
    background: var(--bg);
    color: var(--text);
    font-family: 'IBM Plex Mono', ui-monospace, monospace;
    -webkit-font-smoothing: antialiased;
  }}
  header {{ padding: 28px 20px 18px; border-bottom: 1px solid var(--line); }}
  h1 {{
    font-family: 'Space Grotesk', sans-serif;
    font-weight: 700;
    font-size: 22px;
    margin: 0 0 4px;
    letter-spacing: -0.01em;
  }}
  .sub {{ color: var(--muted); font-size: 13px; margin: 0; }}
  .meta {{ color: var(--muted); font-size: 12px; margin-top: 10px; display: flex; gap: 18px; flex-wrap: wrap; }}
  .meta b {{ color: var(--text); }}
  main {{ padding: 18px 20px 48px; max-width: 900px; margin: 0 auto; }}
  .disclaimer {{
    background: var(--panel);
    border: 1px solid var(--line);
    border-left: 3px solid var(--mid);
    padding: 12px 16px;
    font-size: 12.5px;
    color: var(--muted);
    border-radius: 4px;
    margin-bottom: 20px;
    line-height: 1.5;
  }}
  .empty {{ color: var(--muted); text-align: center; padding: 40px 0; }}

  .league-card {{
    position: relative;
    background: var(--panel);
    border: 1px solid var(--line);
    border-radius: 10px;
    margin-bottom: 12px;
    overflow: hidden;
  }}
  .league-card::before {{
    content: "";
    position: absolute;
    top: 0; left: 0; right: 0;
    height: 2px;
    background: linear-gradient(90deg, var(--hi), var(--blue));
    opacity: 0.7;
  }}
  .league-card summary {{
    list-style: none;
    cursor: pointer;
    display: flex;
    align-items: center;
    gap: 12px;
    padding: 16px 18px;
  }}
  .league-card summary::-webkit-details-marker {{ display: none; }}
  .league-dot {{
    width: 10px; height: 10px; border-radius: 50%;
    background: linear-gradient(135deg, var(--hi), var(--blue));
    flex-shrink: 0;
  }}
  .league-name {{
    font-family: 'Space Grotesk', sans-serif;
    font-weight: 700;
    font-size: 15px;
    flex: 1;
  }}
  .league-count {{
    font-size: 11.5px;
    color: var(--hi);
    background: rgba(62,207,142,0.12);
    padding: 4px 10px;
    border-radius: 20px;
    white-space: nowrap;
  }}
  .chevron {{
    color: var(--muted);
    transition: transform 0.15s ease;
    font-size: 12px;
  }}
  .league-card[open] .chevron {{ transform: rotate(180deg); }}

  .league-matches {{ border-top: 1px solid var(--line); }}
  .match-row {{
    display: grid;
    grid-template-columns: 78px 1fr;
    gap: 4px 14px;
    padding: 12px 18px;
    border-bottom: 1px solid var(--line);
    border-left: 3px solid transparent;
  }}
  .match-row:last-child {{ border-bottom: none; }}
  .match-row.conf-hi {{ border-left-color: var(--hi); }}
  .match-row.conf-mid {{ border-left-color: var(--mid); }}
  .match-row.conf-lo {{ border-left-color: transparent; }}
  .mr-time {{ color: var(--muted); font-size: 12px; align-self: center; }}
  .mr-teams {{ font-weight: 600; font-size: 13.5px; align-self: center; }}
  .vs {{ color: var(--muted); font-weight: 400; }}
  .mr-badges {{ grid-column: 2; display: flex; gap: 8px; flex-wrap: wrap; }}

  .badge {{
    display: inline-block;
    font-size: 10.5px;
    font-family: 'Space Grotesk', sans-serif;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.02em;
    padding: 4px 10px;
    border-radius: 20px;
    white-space: nowrap;
  }}
  .badge-hi {{ background: rgba(62,207,142,0.15); color: var(--hi); }}
  .badge-mid {{ background: rgba(232,185,78,0.15); color: var(--mid); }}
  .badge-lo {{ background: rgba(86,98,112,0.2); color: var(--lo); }}
  .badge-blue {{ background: rgba(78,161,232,0.15); color: var(--blue); }}

  footer {{ padding: 20px; color: var(--muted); font-size: 11.5px; border-top: 1px solid var(--line); text-align: center; }}

  @media (max-width: 520px) {{
    .match-row {{ grid-template-columns: 1fr; }}
    .mr-time {{ order: -1; }}
    .mr-badges {{ grid-column: 1; }}
  }}
</style>
</head>
<body>
<header>
  <h1>PA Finder</h1>
  <p class="sub">Radar diário de candidatos a Pagamento Antecipado — jogos de hoje e amanhã, separados por campeonato</p>
  <div class="meta">
    <span>Atualizado: <b>{generated}</b></span>
    <span>Jogos avaliados: <b>{output["total_fixtures_evaluated"]}</b></span>
    <span>Chamadas de API usadas: <b>{output["calls_used"]}/{output["call_budget"]}</b></span>
  </div>
</header>
<main>
  <div class="disclaimer">
    Vereditos baseados em estimativa estatística (médias de gols dos times), não são garantia de que a casa vai
    disparar o pagamento antecipado — cada casa tem sua própria regra de gatilho. Use como priorização pra não
    perder tempo analisando jogo por jogo; a decisão final e as odds ficam com o seu processo de sempre.
  </div>
  {cards_html}
</main>
<footer>
  PA Finder · gerado automaticamente via GitHub Actions · dados: API-Football
</footer>
</body>
</html>'''

    (config.DOCS_DIR / "index.html").write_text(html_doc, encoding="utf-8")
    print("[build_site] docs/index.html gerado")
