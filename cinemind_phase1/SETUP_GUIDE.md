# CineMind Phase 1 — Complete Setup Guide

This guide walks you through everything from zero: installing tools, downloading
data, running every script in VS Code, and saving your work to GitHub. It assumes
**no prior experience** with Python environments or Git.

---

## Part 0 — What you are building

Eight Python scripts that together prove the core idea of CineMind works,
plus a FastAPI backend, a React frontend, and a Streamlit demo built on top
of them (covered in Part 9):

```
01_data_exploration  ->  understand the data, save train/test split
02_rbm_baseline      ->  reproduce the old RBM model (the baseline to beat)
03_content_embeddings->  turn movie text into vectors with the E5 model
04_two_tower         ->  train the modern model (the centrepiece)
05_qdrant_indexing   ->  load vectors into a vector database, test fast search
06_evaluation        ->  compare everything, produce the results table
07_omdb_enrichment   ->  (optional) fetch posters/plot/cast for the UI
08_neo4j_graph       ->  (optional) load ratings/genres into a graph database
```

Each script saves files that the next one uses. Run them **in order, 01 to 06**
(07 and 08 are optional and independent — they only need the output of 01).

---

## Part 1 — Install the tools (one time)

### 1.1 Install Python (3.10 or newer)
- Windows: download from python.org, **tick "Add Python to PATH"** during install.
- Mac: `brew install python` (or download from python.org).
- Check it worked — open a terminal and run:
  ```bash
  python --version
  ```
  You should see `Python 3.10.x` or higher. (On Mac/Linux you may need `python3`.)

### 1.2 Install VS Code
- Download from code.visualstudio.com and install.
- Open VS Code, go to the Extensions panel (the squares icon on the left), and
  install the **Python** extension by Microsoft.

### 1.3 Install Git
- Download from git-scm.com and install with default options.
- Check it worked:
  ```bash
  git --version
  ```

### 1.4 (Optional) Install Docker — only needed for the REAL Qdrant in step 05
- Download Docker Desktop from docker.com.
- Step 05 works WITHOUT Docker (it falls back to a numpy search), so you can
  skip this for now and add it later.

---

## Part 2 — Set up the project folder

### 2.1 Create the project folder on your laptop
Pick a location you will remember, for example `Documents`. Create a folder
called `cinemind_phase1` and put the provided files inside it so the structure
looks like this:

```
cinemind_phase1/
├── README.md
├── SETUP_GUIDE.md          <- this file
├── requirements.txt
├── .gitignore
├── src/
│   ├── cinemind_utils.py
│   ├── 01_data_exploration.py
│   ├── 02_rbm_baseline.py
│   ├── 03_content_embeddings.py
│   ├── 04_two_tower.py
│   ├── 05_qdrant_indexing.py
│   ├── 06_evaluation.py
│   ├── 07_omdb_enrichment.py   <- optional, added after core Phase 1
│   └── 08_neo4j_graph.py       <- optional, added after core Phase 1
├── data/                   <- you will put the downloaded data here
├── artifacts/              <- the scripts create this automatically
├── backend/                <- FastAPI app (Part 9)
├── frontend/                <- React app (Part 9)
└── streamlit_app/           <- Streamlit demo (Part 9)
```

### 2.2 Open the folder in VS Code
- VS Code -> File -> Open Folder -> select `cinemind_phase1`.
- You should now see all the files in the left sidebar.

---

## Part 3 — Download the data

### 3.1 Download MovieLens 100K
1. Go to: **https://grouplens.org/datasets/movielens/**
2. Find **"MovieLens 100K Dataset"** and download **ml-100k.zip** (about 5 MB).
   (Direct link: https://files.grouplens.org/datasets/movielens/ml-100k.zip)
3. Unzip it. You will get a folder called `ml-100k` containing files like
   `u.data`, `u.item`, `u.user`.

### 3.2 Put the data in the right place
Move the whole `ml-100k` folder into your project's `data/` folder so it looks
like this:

```
cinemind_phase1/
└── data/
    └── ml-100k/
        ├── u.data      <- the ratings (who rated what)
        ├── u.item      <- the movies (title + genres)
        ├── u.user      <- the users (age, gender, occupation)
        └── ... (other files, not used)
```

**This is the only data you need for Phase 1 scripts 01, 02, 04, 05, 06.**
Script 03 additionally downloads a model automatically (see Part 5).

### 3.3 Which file feeds which script
You do not paste data into the code — the scripts read these files by path:

| File | Read by | Contains |
|------|---------|----------|
| `data/ml-100k/u.data` | 01 | user_id, movie_id, rating, timestamp |
| `data/ml-100k/u.item` | 01 | movie_id, title, 19 genre flags |
| `data/ml-100k/u.user` | 01 | user demographics |

Scripts 02-06 read the **cleaned CSVs that script 01 creates** in `data/`, not
the raw files. So you must always run 01 first.

### 3.4 If you put the data somewhere else
The data path is set in **one place**: the top of `src/cinemind_utils.py`:
```python
DATA_DIR = os.environ.get("CINEMIND_DATA", "data/ml-100k")
```
If your `ml-100k` folder is elsewhere, either move it to `data/ml-100k`, or set
an environment variable before running:
```bash
# Mac/Linux
export CINEMIND_DATA=/full/path/to/ml-100k
# Windows (PowerShell)
$env:CINEMIND_DATA="C:\full\path\to\ml-100k"
```

---

## Part 4 — Create the Python environment

A "virtual environment" is an isolated box for this project's packages so they
don't clash with other projects.

### 4.1 Open the VS Code terminal
- VS Code -> Terminal -> New Terminal. It opens at the project folder.

### 4.2 Create and activate the environment
```bash
# Create it (one time)
python -m venv .venv

# Activate it (every time you open a new terminal)
# Mac/Linux:
source .venv/bin/activate
# Windows (PowerShell):
.venv\Scripts\Activate.ps1
```
When active, your terminal prompt shows `(.venv)` at the start.

### 4.3 Tell VS Code to use this environment
- Press `Ctrl+Shift+P` (Mac: `Cmd+Shift+P`) -> type "Python: Select Interpreter"
  -> choose the one inside `.venv`.

### 4.4 Install the packages
```bash
pip install -r requirements.txt
```
This installs numpy, pandas, matplotlib, torch, sentence-transformers, and
qdrant-client. It may take a few minutes (torch is large).

---

## Part 5 — Run the scripts (in order)

Run each from the project root with the environment active. After each one,
read the printed output — every script ends by telling you what to run next.

### Step 1 — Data exploration
```bash
python src/01_data_exploration.py
```
Creates `data/train_positives.csv`, `data/test_positives.csv`, `data/items.csv`,
and a plot at `artifacts/eda_overview.png` (double-click it in VS Code to view).

### Step 2 — RBM baseline
```bash
python src/02_rbm_baseline.py
```
Prints the RBM's Precision@10 / Recall@10 — the numbers to beat.

### Step 3 — Content embeddings
```bash
python src/03_content_embeddings.py
```
**First run only:** downloads the E5 model (~130 MB) automatically. Needs
internet. Creates `artifacts/content_vecs.npy`. Shows "movies like X" examples.

### Step 4 — Two-tower model (the centrepiece)
```bash
python src/04_two_tower.py
```
Trains for 60 epochs (a couple of minutes on a laptop CPU). Prints the
comparison table and saves `artifacts/two_tower.pt` + `artifacts/item_vecs.npy`.

### Step 5 — Qdrant vector search
```bash
python src/05_qdrant_indexing.py
```
**Without Docker:** runs a numpy fallback automatically — totally fine for
learning. **With Docker:** first run `docker run -p 6333:6333 qdrant/qdrant` in
a separate terminal, then run this script to use the real database.

### Step 6 — Final evaluation
```bash
python src/06_evaluation.py
```
Produces the final comparison table and saves `artifacts/results.csv`, plus
example recommendations for one user.

### Expected final numbers (yours will be very close)
```
Popularity baseline      Precision@10 0.061   Recall@10 0.066
RBM                      Precision@10 0.075   Recall@10 0.082
Two-tower                Precision@10 0.058   Recall@10 0.091
Two-tower + pop prior    Precision@10 0.093   Recall@10 0.126
```

### Step 7 — Poster/plot/cast enrichment (optional)
```bash
python src/07_omdb_enrichment.py
```
Needs an `OMDB_API_KEY` in a `.env` file at the project root — get a free key
(email-only signup, instant) at **omdbapi.com/apikey.aspx**. The free tier
allows 1,000 requests/day; with ~1,700 movies to look up, one run may not
finish the whole catalogue. That's fine — the script saves progress as it
goes and picks up where it left off next time you run it. You can also set
`OMDB_API_KEY=key1,key2` (comma-separated) to rotate to a second key
automatically once the first runs out for the day.
Without this step, the API/frontend/Streamlit demo all still work — movie
cards just show no poster image instead.

### Step 8 — Graph insights (optional)
```bash
docker compose --env-file .env -f backend/docker-compose.yml up -d neo4j
python src/08_neo4j_graph.py
```
Needs a running Neo4j (started above via Docker; no separate signup or key).
Loads every rating and genre into a graph so the app can answer questions
like "which other users also liked this movie, and what else did they like"
as a direct graph traversal. Browse the graph yourself at
`http://localhost:7474` (user `neo4j`, password from `NEO4J_PASSWORD` in
`.env` / `backend/docker-compose.yml`). Without this step, the API/frontend/
Streamlit demo all still work — the "Graph insights" button just reports no
data available.

---

## Part 6 — Save your work to GitHub

GitHub stores your code online so it is safe and shareable (great for a
portfolio). The data and trained models are deliberately NOT uploaded — the
`.gitignore` file excludes them because they are large and regenerable.

### 6.1 Create a GitHub account
- Sign up at github.com if you do not have an account.

### 6.2 Create a new empty repository
- On github.com, click the **+** (top right) -> **New repository**.
- Name it `cinemind-phase1`. Leave it empty (no README, since you have one).
- Click **Create repository**. Copy the URL shown, e.g.
  `https://github.com/YOURNAME/cinemind-phase1.git`.

### 6.3 Initialise Git in your project (one time)
In the VS Code terminal, at the project root:
```bash
git init
git add .
git commit -m "Phase 1: data, RBM baseline, two-tower, embeddings, evaluation"
```

### 6.4 Connect and push to GitHub
```bash
git branch -M main
git remote add origin https://github.com/YOURNAME/cinemind-phase1.git
git push -u origin main
```
The first push may ask you to sign in to GitHub — follow the browser prompt.

### 6.5 Saving changes later
Whenever you change a file:
```bash
git add .
git commit -m "describe what you changed"
git push
```

### 6.6 Using VS Code's Git panel instead (no commands)
- Click the **Source Control** icon (branch shape) in the left sidebar.
- Type a message, click the checkmark to commit, then "Sync Changes" to push.

---

## Part 7 — Where things are saved

| What | Where | In Git? |
|------|-------|---------|
| Your code | `src/*.py` | Yes (this is the point) |
| Raw MovieLens data | `data/ml-100k/` | No (download it again instead) |
| Cleaned CSVs | `data/*.csv` | No (script 01 regenerates them) |
| Trained model + vectors | `artifacts/` | No (scripts 04, 05 regenerate them) |

Anyone who clones your repo just downloads the data (Part 3) and runs the
scripts (Part 5) to reproduce everything.

---

## Part 8 — Common problems and fixes

**"FileNotFoundError: could not find data/ml-100k/u.data"**
The data is not in the right place. Re-check Part 3.2 — you need
`data/ml-100k/u.data` exactly.

**"ModuleNotFoundError: No module named 'torch'" (or pandas, etc.)**
Your environment is not active or packages are not installed. Run
`source .venv/bin/activate` (or the Windows equivalent) then
`pip install -r requirements.txt`.

**Script 03 hangs or errors on "huggingface.co"**
You need internet for the first run of script 03 (it downloads the model).
After the first successful run it works offline.

**"Run step 1 first" message**
Scripts 02-06 need the CSVs that script 01 creates. Run
`python src/01_data_exploration.py` first.

**Want to convert scripts to Jupyter notebooks?**
Each `.py` file runs as-is. If you prefer notebooks, in VS Code you can right
-click a `.py` file and there are extensions to open it as a notebook, or you
can copy each section into notebook cells. The `.py` form is recommended
because it is easier to run and version-control.

---

## Part 9 — What comes after Phase 1

The artifacts you produced here (`two_tower.pt`, `item_vecs.npy`,
`content_vecs.npy`) are loaded by the API and demo app.

### 9.1 Start the FastAPI backend
```bash
uvicorn backend.main:app --reload --port 8000
```
Open `http://127.0.0.1:8000/docs` to try the routes.

### 9.2 Start the Streamlit demo
```bash
pip install -r streamlit_app/requirements.txt
streamlit run streamlit_app/app.py
```
Use the returning-user tab with a MovieLens user ID like `42`, or use the
search/new-user tabs for content-based recommendations.

### 9.3 Start the React frontend
Needs Node.js (18+) installed separately — download from nodejs.org.
```bash
cd frontend
npm install
npm run dev
```
Open the URL it prints (usually `http://localhost:5173`). The frontend talks
to the FastAPI backend, so start that first (9.1) or the pages will show
"API unreachable". If you get CORS errors in the browser console, check that
`backend/main.py`'s CORS origin list includes the port Vite printed.

### 9.4 Optional services
Docker is optional. If Qdrant is not reachable, CineMind uses numpy search. If
Postgres is not configured, feedback is stored in `backend/feedback.db`. To
run the full stack in Docker instead (API + Qdrant + Postgres + Redis + Neo4j):
```bash
docker compose --env-file .env -f backend/docker-compose.yml up -d --build
python src/08_neo4j_graph.py   # load the graph once Neo4j is up (Part 5, Step 8)
```
Pass `--env-file` explicitly as shown — Compose's automatic `.env` lookup can
silently miss it depending on which shell you run it from, which would make
your API keys quietly disappear inside the container.

Set `ANTHROPIC_API_KEY` or `GROQ_API_KEY` to enable LLM parsing, reranking, and
explanations. Without an API key, the app still works in retrieval-only mode.
Live semantic search uses the cached E5 model when available. Set
`CINEMIND_ALLOW_MODEL_DOWNLOAD=1` before starting the app if you want it to
download `intfloat/e5-small-v2` on first use. Set `OMDB_API_KEY` (Part 5,
Step 7) to show posters/plot/cast in either UI. Set `LANGFUSE_PUBLIC_KEY`/
`LANGFUSE_SECRET_KEY` to trace every LLM call at cloud.langfuse.com. Redis
caches recommendation responses for 5 minutes when reachable; Neo4j powers
the "Graph insights" button once loaded (Part 5, Step 8) — both are optional
and everything works without them, just without the cache speedup / graph
panel.
