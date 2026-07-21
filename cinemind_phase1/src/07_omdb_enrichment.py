"""
07_omdb_enrichment.py
======================
Enriches the catalogue with OMDb metadata: poster image, plot, and cast --
closing the gap called out in CLAUDE.md's data layer (movie metadata beyond
what MovieLens itself provides).

IMPORTANT: MovieLens 100K (unlike the newer 25M/latest releases) does NOT
ship a links.csv mapping movie_id -> an external id. So movies are matched by
parsing the "Title (Year)" format already in u.item/items.csv and querying
OMDb's title-lookup endpoint (?t=...&y=...) -- a fuzzy title+year match, not
a database join. A handful of movies won't find a confident match; those
rows are kept with null poster/overview/cast so downstream code can render a
placeholder.

REQUIRES:
    OMDB_API_KEY in .env (free key: omdbapi.com/apikey.aspx -- instant,
    email-only signup, 1,000 requests/day on the free tier). Supports
    multiple comma-separated keys, e.g. OMDB_API_KEY=key1,key2 -- when one
    key's daily quota is exhausted, the script automatically rotates to the
    next before giving up.
    data/items.csv (created by step 1)

OUTPUT:
    artifacts/movie_meta.csv  (movie_id, imdb_id, poster_url, overview, cast)

HOW TO RUN (from project root):
    python src/07_omdb_enrichment.py

Idempotent / resumable: re-running after an interruption only fetches
movie_ids missing from artifacts/movie_meta.csv, and checkpoints every 50
movies. With 1,682 movies and a 1,000/day free quota per key, ONE run may
not finish the whole catalogue on a single key -- when all configured keys'
daily limits are hit, the script saves progress and exits cleanly; just
re-run it again the next day (or with additional keys) to pick up where it
left off.
"""

import os
import re
import sys

import pandas as pd
import requests

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import cinemind_utils as cu

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

OMDB_API_KEYS = [k.strip() for k in os.environ.get("OMDB_API_KEY", "").split(",") if k.strip()]
OMDB_BASE = "https://www.omdbapi.com/"
OUT_PATH = "artifacts/movie_meta.csv"


class QuotaExceeded(Exception):
    pass


class AllKeysExhausted(Exception):
    pass


class KeyRotator:
    """Tries each configured OMDb key in turn, moving to the next once the
    current one's daily quota is hit, instead of stopping the whole run."""

    def __init__(self, keys):
        self.keys = keys
        self.index = 0

    @property
    def current(self):
        return self.keys[self.index]

    def advance(self):
        """Move to the next key. Raises AllKeysExhausted if none are left."""
        self.index += 1
        if self.index >= len(self.keys):
            raise AllKeysExhausted()
        print(f"  Switching to OMDB_API_KEY #{self.index + 1}/{len(self.keys)}.")


def unreverse_article(title):
    """MovieLens stores the leading article at the end for alphabetising,
    e.g. "Godfather, The" for "The Godfather" -- OMDb's title search doesn't
    know this convention and can silently match a wrong film instead (this
    is exactly what happened for "Godfather, The (1972)" before this fix:
    OMDb matched an unrelated film instead of Coppola's). Un-reverse it
    before querying."""
    match = re.match(r"^(.*),\s+(The|A|An)$", title.strip())
    if not match:
        return title
    return f"{match.group(2)} {match.group(1)}"


def parse_title_year(title):
    """"Toy Story (1995)" -> ("Toy Story", 1995). Some MovieLens titles have
    an alternate-language title in parens too, e.g. "Shanghai Triad (Yao a
    yao yao dao waipo qiao) (1995)" -- only the trailing (YYYY) is the year,
    so the query keeps everything before it, alt-title included."""
    match = re.search(r"^(.*)\s\((\d{4})\)\s*$", title.strip())
    if not match:
        return unreverse_article(title.strip()), None
    return unreverse_article(match.group(1).strip()), int(match.group(2))


def lookup_movie(title, year, session, api_key):
    """OMDb's ?t= does a direct best-match title lookup (unlike TMDB's
    /search, which returns a list) -- one call gets poster+plot+cast
    together, no separate credits request needed."""
    params = {"apikey": api_key, "t": title, "type": "movie"}
    if year:
        params["y"] = year
    r = session.get(OMDB_BASE, params=params, timeout=10)
    data = r.json()

    if data.get("Error") == "Request limit reached!":
        raise QuotaExceeded()

    if data.get("Response") == "False" and year:
        # Some titles are off by a year between MovieLens and OMDb -- retry
        # without the year constraint before giving up.
        params.pop("y")
        r = session.get(OMDB_BASE, params=params, timeout=10)
        data = r.json()
        if data.get("Error") == "Request limit reached!":
            raise QuotaExceeded()

    return data if data.get("Response") == "True" else None


def main():
    print("=" * 60)
    print("CineMind Phase 1 — Step 7: OMDb Enrichment")
    print("=" * 60)

    if not OMDB_API_KEYS:
        raise SystemExit(
            "OMDB_API_KEY not set. Add it to a .env file at the project root "
            "-- get a free key at omdbapi.com/apikey.aspx. Multiple keys can "
            "be comma-separated to rotate through when one's quota runs out."
        )
    print(f"{len(OMDB_API_KEYS)} OMDb API key(s) configured.")

    cu.ensure_dirs()
    if not os.path.exists("data/items.csv"):
        raise FileNotFoundError("Run step 1 first: python src/01_data_exploration.py")

    items = pd.read_csv("data/items.csv")

    rows = []
    done_ids = set()
    if os.path.exists(OUT_PATH):
        done_df = pd.read_csv(OUT_PATH)
        rows = done_df.to_dict("records")
        done_ids = set(done_df.movie_id.astype(int))
        print(f"\nResuming: {len(done_ids)}/{len(items)} movies already fetched.")

    session = requests.Session()
    misses = 0
    quota_hit = False
    keys = KeyRotator(OMDB_API_KEYS)

    for i, row in enumerate(items.itertuples(), 1):
        movie_id = int(row.movie_id)
        if movie_id in done_ids:
            continue

        title, year = parse_title_year(row.title)
        try:
            result = lookup_movie(title, year, session, keys.current)
        except QuotaExceeded:
            print(f"  Key #{keys.index + 1} quota reached after {len(rows)} movies.")
            try:
                keys.advance()
            except AllKeysExhausted:
                print(f"\n  All {len(OMDB_API_KEYS)} OMDb key(s) exhausted for today.")
                quota_hit = True
                break
            # Retry the same movie immediately with the next key rather
            # than skipping it, since we haven't actually fetched it yet.
            try:
                result = lookup_movie(title, year, session, keys.current)
            except QuotaExceeded:
                print(f"\n  All {len(OMDB_API_KEYS)} OMDb key(s) exhausted for today.")
                quota_hit = True
                break
            except requests.RequestException as e:
                print(f"  [{movie_id}] {row.title}: request failed ({e}) -- will retry next run")
                continue
        except requests.RequestException as e:
            # A network/DNS/timeout failure is NOT the same as "OMDb has no
            # match" -- caching it as a permanent null would make it
            # un-retryable, since resuming only skips movie_ids already in
            # the output. Skip it entirely so the next run retries it.
            print(f"  [{movie_id}] {row.title}: request failed ({e}) -- will retry next run")
            continue

        if result is None:
            misses += 1
            rows.append({
                "movie_id": movie_id, "imdb_id": None,
                "poster_url": None, "overview": None, "cast": None,
            })
        else:
            poster = result.get("Poster")
            rows.append({
                "movie_id": movie_id,
                "imdb_id": result.get("imdbID"),
                "poster_url": poster if poster and poster != "N/A" else None,
                "overview": result.get("Plot") if result.get("Plot") not in (None, "N/A") else None,
                "cast": result.get("Actors") if result.get("Actors") not in (None, "N/A") else None,
            })

        if i % 50 == 0 or i == len(items):
            print(f"  {i}/{len(items)} processed ({misses} unmatched so far)")
            pd.DataFrame(rows).to_csv(OUT_PATH, index=False)  # checkpoint

    df = pd.DataFrame(rows)
    df.to_csv(OUT_PATH, index=False)
    matched = df.imdb_id.notna().sum()
    print(f"\nMatched {matched}/{len(items)} movies to OMDb ({misses} unmatched).")
    print(f"Saved {OUT_PATH}")
    if quota_hit:
        print(f"\n{len(items) - len(rows)} movies still unfetched -- re-run this script "
              "tomorrow (or with additional OMDB_API_KEY entries) to continue where it left off.")
    else:
        print("Step 7 complete. recommender.py will pick this up automatically on next load().")


if __name__ == "__main__":
    main()
