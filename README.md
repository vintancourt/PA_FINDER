# PA Finder

Radar diário (jogos de hoje + amanhã, dos campeonatos que você escolheu) de
candidatos a **Pagamento Antecipado (PA)** para quem opera com
arbitragem/surebet: pega o PA num time favorito e protege os outros
resultados em outras casas.

O site atualiza sozinho todo dia via GitHub Actions e fica publicado no
GitHub Pages, **agrupado por campeonato**, com vereditos direto em texto —
sem números, sem odds (você já tem seu próprio programa pra isso):

- **"GRANDE CHANCE DE DUPLO GREEN"** / **"CHANCE MODERADA DE DUPLO GREEN"** /
  **"CHANCE QUASE NULA DE DUPLO GREEN"** — o quanto o jogo favorece a
  estratégia de PA + proteção.
- **"PEGAR PA NESSE TIME: {time}"** / **"BOM PEGAR PA NOS DOIS TIMES"** /
  **"EVITAR PA NESSE JOGO"** — em qual time (ou times) vale a pena buscar o PA.

**⚠️ Importante:** isso é uma ferramenta estatística de priorização, não uma
garantia. Ela não sabe a regra exata de PA de cada casa (algumas disparam
com 2 gols de vantagem, outras com 3, algumas só depois de X minutos). Use
os vereditos pra saber **onde olhar primeiro** e sempre confira ao vivo
antes de operar, com o seu processo de sempre.

---

## Como funciona (visão geral)

1. **Busca os jogos** de hoje e amanhã, de todas as ligas do mundo, na
   [API-Football](https://www.api-football.com/) (2 chamadas de API).
2. **Filtra** só os campeonatos da sua whitelist (`scripts/config.py` →
   `LEAGUE_WHITELIST`) — os mesmos que você selecionou.
3. Para cada jogo, busca (com **cache de 3 dias**) as médias de gols
   marcados/sofridos dos dois times e calcula, com um modelo de Poisson, a
   chance de cada time abrir vantagem de 2 ou 3 gols.
4. Converte isso em vereditos em texto ("duplo green" e "PA") usando os
   limiares configuráveis em `config.py`.
5. Gera `docs/index.html` — os jogos **agrupados em cards por campeonato**,
   cada um expansível, com contagem de jogos — e publica no GitHub Pages.
6. Guarda um histórico diário em `data/history/` — isso vira, com o tempo,
   uma base de dados própria que você pode usar pra validar/calibrar os
   limiares do modelo (comparar o que o site apontou com o que realmente
   aconteceu).

## Campeonatos cobertos

A whitelist em `scripts/config.py` já vem configurada com:

Brasileirão Série A e B, Copa do Brasil, Copa Libertadores, Copa
Sudamericana, Premier League, Championship (Inglaterra), LaLiga, LaLiga 2,
Bundesliga, 2. Bundesliga, Ligue 1, Série A (Itália), Liga Portugal, SuperLig
(Turquia), Eliteserien, Allsvenskan, Champions League, Europa League,
Conference League, Copa do Mundo 2026, Copa Centro-Americana CONCACAF, Copa
das Ligas, MLS, Liga MX, Liga Profesional de Fútbol (Argentina), J1 (Japão)
e Superliga (China).

Pra adicionar, remover ou corrigir algum campeonato, edite a lista
`LEAGUE_WHITELIST` em `scripts/config.py` — cada entrada tem o rótulo de
exibição, os nomes que a API costuma usar (`name_aliases`) e o país pra
desambiguar (ex.: "Série A" sozinho existe tanto no Brasil quanto na Itália).
Na primeira execução real, o log do workflow avisa quais campeonatos da
whitelist não tiveram jogo encontrado — isso ajuda a conferir se algum
alias precisa de ajuste.

## Passo a passo pra colocar no ar

### 1. Criar o repositório
Suba esta pasta para um repositório novo no seu GitHub (pode ser privado).

### 2. Conseguir a chave da API-Football (grátis)
1. Crie uma conta grátis em **https://dashboard.api-football.com/register**
   (o plano free dá **100 requisições/dia**, que é suficiente pro uso diário
   deste projeto).
2. Copie sua API Key no painel.
3. No seu repositório do GitHub: **Settings → Secrets and variables →
   Actions → New repository secret**
   - Nome: `API_FOOTBALL_KEY`
   - Valor: sua chave (cole só ali, nunca em código ou no chat comigo)

> Se preferir usar a mesma API via RapidAPI, veja as variáveis opcionais
> `API_FOOTBALL_BASE_URL` e `API_FOOTBALL_RAPIDAPI_HOST` no `.env.example`
> — configure-as como **Variables** (não Secrets) do Actions se usar essa via.

### 3. Ativar o GitHub Pages
**Settings → Pages → Build and deployment → Source: "Deploy from a branch"
→ Branch: `main` → Folder: `/docs`** → Save.
Depois de a Action rodar pela primeira vez, seu site vai ficar em:
`https://SEU_USUARIO.github.io/NOME_DO_REPO/`

### 4. Ativar as Actions
Vá na aba **Actions** do repositório e habilite os workflows (o GitHub
pede confirmação na primeira vez em repositórios novos).

### 5. Rodar pela primeira vez
Na aba **Actions → Atualização diária PA Finder → Run workflow** — isso
dispara a primeira execução manualmente, sem esperar o horário do cron.
Depois disso ele roda sozinho todo dia às 09:00 (horário de Brasília).

## Rodando localmente (opcional, pra testar/ajustar)

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # preencha sua API_FOOTBALL_KEY no .env
export $(cat .env | xargs)
python -m scripts.run_pipeline
# abra docs/index.html no navegador
```

## Ajustando o modelo

Tudo fica configurável em `scripts/config.py`:

- `PA_LEAD_THRESHOLDS` — margens de gol consideradas (padrão: 2 e 3).
- `DUPLO_GREEN_ALTA` / `DUPLO_GREEN_MODERADA` — limiares de probabilidade
  que definem os três vereditos de "duplo green".
- `PA_FORTE` / `PA_MODERADA` / `PA_DIFF_DOMINANCIA` — limiares que definem
  quando é "pegar PA num time só", "bom pegar nos dois" ou "evitar".
- `LEAGUE_WHITELIST` — quais campeonatos entram no site (veja seção acima).
- O modelo estatístico em si (conversão de médias de gols em probabilidade
  de abrir vantagem) está em `scripts/model.py` — comece calibrando os
  limiares acima com base no seu histórico real de acertos em
  `data/history/`.

## Sobre a cota gratuita da API

O plano free da API-Football dá 100 req/dia. Como o projeto não consulta
odds (você já tem seu próprio programa pra isso) e cobre só os ~28
campeonatos da whitelist (não o mundo todo), a cota costuma sobrar bastante:
- ~2 chamadas pra pegar todos os jogos do mundo (hoje + amanhã) — o filtro
  de liga acontece depois, localmente, sem gastar cota extra;
- 2 chamadas de estatística por jogo (um time casa, um fora), com **cache
  de 3 dias** — times que já apareceram recentemente não gastam cota de novo;
- se ainda assim faltar cota num dia de calendário muito cheio, o pipeline
  para de forma organizada (processando a whitelist na ordem que você
  definiu) e continua de onde parou na execução seguinte, sem perder nada
  graças ao cache.

## Estrutura do projeto

```
scripts/            código do pipeline (fetch + modelo + geração do site)
data/latest_ranking.json   último resultado calculado
data/history/        snapshots diários (sua base histórica crescente)
data/team_stats/     cache de estatísticas de times
docs/index.html      o site publicado no GitHub Pages
.github/workflows/   automação diária
```
