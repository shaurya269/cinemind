"""
CineMind Streamlit demo.

Run from the project root:
    streamlit run streamlit_app/app.py
"""

import os
import re
import sys

import streamlit as st

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BACKEND_DIR = os.path.join(PROJECT_ROOT, "backend")
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)
if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)

import feedback
import graph
import llm_chains
import recommender


st.set_page_config(
    page_title="CineMind",
    page_icon="\U0001F3AC",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# Custom CSS layered on top of .streamlit/config.toml's theme tokens -- config.toml
# sets the base palette (shared with frontend/src/index.css so both interfaces
# read as one product), this fills in the details Streamlit's theme API doesn't
# expose: display font, card borders/shadows, genre chips, the marquee title rule.
CUSTOM_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Bebas+Neue&family=Inter:wght@400;500;600;700;800&display=swap');

html, body, [class*="css"] {
    font-family: 'Inter', 'Segoe UI', sans-serif;
}

.cm-title {
    font-family: 'Bebas Neue', 'Arial Narrow', sans-serif;
    font-size: 3.2rem;
    letter-spacing: 0.02em;
    color: #ede9e0;
    margin-bottom: 0;
    line-height: 1;
    position: relative;
    display: inline-block;
}
.cm-title::after {
    content: "";
    position: absolute;
    left: 0; right: 0; bottom: -6px;
    height: 4px;
    background: #e8493a;
    border-radius: 2px;
}
.cm-tagline {
    color: #9aa1ad;
    font-size: 0.95rem;
    margin-top: 14px;
}

div[data-testid="stMetric"] {
    background: #171b21;
    border: 1px solid #262c35;
    border-radius: 10px;
    padding: 10px 14px;
}
div[data-testid="stMetricLabel"] {
    color: #9aa1ad !important;
}
div[data-testid="stMetricValue"] {
    color: #e8493a !important;
    font-family: 'Cascadia Code', 'JetBrains Mono', monospace;
}

div[data-testid="stVerticalBlockBorderWrapper"] {
    border-radius: 12px !important;
}

.cm-genre-chip {
    display: inline-block;
    font-size: 0.7rem;
    font-weight: 600;
    letter-spacing: 0.02em;
    background: #0e1115;
    color: #2a8f88;
    padding: 3px 10px;
    border-radius: 20px;
    margin: 0 6px 6px 0;
}

.cm-why-box {
    background: #0e1115;
    border-radius: 8px;
    padding: 10px 14px;
    margin-top: 8px;
    font-size: 0.9rem;
}

.cm-score {
    font-family: 'Cascadia Code', 'JetBrains Mono', monospace;
    color: #c9a15a;
    font-size: 0.85rem;
}
</style
"""


def genre_chips_html(genres_repr: str) -> str:
    """items.csv stores genres as a Python-list repr string; render as chips."""
    names = re.findall(r"'([^']*)'|\"([^\"]*)\"", genres_repr or "")
    flat = [a or b for a, b in names]
    if not flat:
        return ""
    return "".join(f'<span class="cm-genre-chip">{g}</span>' for g in flat)


@st.cache_resource(show_spinner="Loading recommendation artifacts...")
def load_recommender():
    recommender.load()
    graph.load()
    return True


@st.cache_data(ttl=300, show_spinner="Fetching recommendations...")
def cached_recommend_for_user(user_id: int, k: int):
    """Streamlit-local cache mirroring recommender.py's Redis cache-aside (5 min TTL),
    since Streamlit Cloud has no Redis sidecar to fall back on."""
    return recommender.recommend_for_user(user_id, k=k)


@st.cache_data(ttl=300, show_spinner="Searching...")
def cached_conversational_search(query: str):
    return llm_chains.conversational_search(query)


@st.cache_data(ttl=300, show_spinner="Finding seed movies...")
def cached_onboard_new_user(answers: str):
    return llm_chains.onboard_new_user(answers)


@st.cache_data(ttl=60, show_spinner=False)
def cached_similar_to_movie(movie_id: int, k: int = 3):
    return recommender.similar_to_movie(movie_id, k=k)


def render_results_with_genre_filter(results, *, key, show_feedback=False, user_id=None):
    """Shared genre-multiselect + filtered card list, used by every results tab.
    key_prefix keeps widget keys unique across tabs -- all tabs render in the same
    script run, so the same movie appearing in two tabs at once would otherwise
    collide on e.g. "explain-{movie_id}-{title}"."""
    if not results:
        return
    all_genres = sorted({
        g for m in results for g in re.findall(r"'([^']*)'", m.get("genres", ""))
    })
    genre_filter = st.multiselect("Filter by genre", all_genres, key=key)
    for movie in results:
        if genre_filter:
            movie_genres = re.findall(r"'([^']*)'", movie.get("genres", ""))
            if not any(g in movie_genres for g in genre_filter):
                continue
        render_movie_card(movie, show_feedback=show_feedback, user_id=user_id, key_prefix=f"{key}-")


def is_watchlisted(movie_id: int) -> bool:
    return movie_id in st.session_state.setdefault("watchlist", {})


def toggle_watchlist(movie):
    movie_id = int(movie.get("movie_id", -1))
    watchlist = st.session_state.setdefault("watchlist", {})
    if movie_id in watchlist:
        del watchlist[movie_id]
    else:
        watchlist[movie_id] = movie


def render_movie_card(movie, *, show_feedback=False, user_id=None, key_prefix=""):
    title = movie.get("title", "Unknown title")
    movie_id = int(movie.get("movie_id", -1))
    score = movie.get("score")
    genres = movie.get("genres", "[]")
    poster_url = movie.get("poster_url")
    overview = movie.get("overview")
    cast = movie.get("cast")

    with st.container(border=True):
        poster_col, body_col = st.columns([0.16, 0.84])
        with poster_col:
            if poster_url:
                st.image(poster_url, width=90)
            else:
                st.caption("No poster")

        with body_col:
            top = st.columns([0.6, 0.2, 0.2])
            top[0].markdown(f"### {title}")
            star = "★ Saved" if is_watchlisted(movie_id) else "☆ Save"
            if top[1].button(star, key=f"{key_prefix}watchlist-{movie_id}-{title}"):
                toggle_watchlist(movie)
                st.rerun()
            if score is not None:
                top[2].markdown(
                    f'<div class="cm-score" style="text-align:right;padding-top:14px;">score {float(score):.3f}</div>',
                    unsafe_allow_html=True,
                )
            st.markdown(genre_chips_html(genres), unsafe_allow_html=True)

            if overview:
                st.write(overview)
            if cast:
                st.caption(f"Cast: {cast}")
            if movie.get("why"):
                st.markdown(f'<div class="cm-why-box">{movie["why"]}</div>', unsafe_allow_html=True)

        actions = st.columns([0.25, 0.25, 0.17, 0.17, 0.16])
        if actions[0].button("Why this?", key=f"{key_prefix}explain-{movie_id}-{title}"):
            st.info(llm_chains.explain_recommendation(movie_id) or "No metadata found.")
        if actions[1].button("Graph insights", key=f"{key_prefix}graph-{movie_id}-{title}"):
            insights = graph.graph_insights(movie_id, k=3)
            if insights is None:
                st.info("No graph data for this movie (or Neo4j isn't reachable).")
            else:
                st.write(f"**{insights['total_raters']}** users rated this movie in the graph.")
                if insights["also_liked_by_raters"]:
                    also_liked = ", ".join(m["title"] for m in insights["also_liked_by_raters"])
                    st.write(f"Also liked by the same raters: {also_liked}")
                if insights["shared_genre_movies"]:
                    shared = ", ".join(m["title"] for m in insights["shared_genre_movies"])
                    st.write(f"Shares the most genres with: {shared}")

        if show_feedback and user_id is not None:
            if actions[2].button("Liked", key=f"{key_prefix}like-{movie_id}"):
                st.success(feedback.log_feedback(user_id, movie_id, clicked=True, rating=5.0))
            if actions[3].button("Skip", key=f"{key_prefix}skip-{movie_id}"):
                st.success(feedback.log_feedback(user_id, movie_id, clicked=False))
            if actions[4].button("Similar", key=f"{key_prefix}similar-{movie_id}"):
                for neighbour in cached_similar_to_movie(movie_id, k=3):
                    st.write(f"{neighbour['title']} ({neighbour['score']:.3f})")


def main():
    st.markdown(CUSTOM_CSS, unsafe_allow_html=True)

    st.markdown('<div class="cm-title">CineMind</div>', unsafe_allow_html=True)
    st.markdown(
        '<p class="cm-tagline">Personalised &middot; Explainable &middot; Conversational '
        "&mdash; hybrid two-tower deep learning + LLM reasoning, on MovieLens 100K.</p>",
        unsafe_allow_html=True,
    )
    st.write("")

    try:
        load_recommender()
    except Exception as exc:
        st.error(str(exc))
        st.stop()

    status = st.columns(4)
    status[0].metric("LLM", llm_chains.LLM_PROVIDER or "retrieval only")
    status[1].metric("Feedback", feedback.backend_in_use())
    status[2].metric("Movies", len(recommender.title_of))
    status[3].metric("Graph", "connected" if graph.GRAPH_AVAILABLE else "unavailable")

    st.write("")
    tab_recs, tab_search, tab_onboarding, tab_watchlist = st.tabs([
        "Returning user",
        "Conversational search",
        "New user",
        f"Watchlist ({len(st.session_state.get('watchlist', {}))})",
    ])

    # Results are stashed in session_state and re-rendered on every script
    # run (not just the run where the primary button was clicked) --
    # otherwise clicking ANY per-card button (Explain, Graph insights,
    # Liked, ...) triggers a Streamlit rerun where the primary button's
    # own st.button() call returns False again, and the whole list of
    # results would vanish even though nothing about them changed.
    with tab_recs:
        st.caption(
            "Hybrid two-tower + popularity-prior recommendations for a user with "
            "existing rating history. New here? Use the **New user** tab instead."
        )
        col1, col2, col3 = st.columns([0.3, 0.3, 0.4])
        user_id = col1.number_input("User ID", min_value=1, max_value=943, value=42, step=1)
        k = col2.slider("Recommendations", 5, 20, 10)
        col3.write("")
        col3.write("")
        if col3.button("Recommend", type="primary"):
            if not recommender.known_user(int(user_id)):
                st.session_state["recs_warning"] = "No training history for this user. Try the New user tab."
                st.session_state.pop("recs_results", None)
            else:
                st.session_state.pop("recs_warning", None)
                st.session_state["recs_results"] = cached_recommend_for_user(int(user_id), int(k))
                st.session_state["recs_user_id"] = int(user_id)

        if st.session_state.get("recs_warning"):
            st.warning(st.session_state["recs_warning"])

        render_results_with_genre_filter(
            st.session_state.get("recs_results", []),
            key="recs_genre_filter",
            show_feedback=True,
            user_id=st.session_state.get("recs_user_id"),
        )

    with tab_search:
        st.caption(
            "Free-text request → parsed intent → grounded retrieval → LLM re-rank "
            "→ explanation for the top pick. Every result is a real movie from the catalogue."
        )
        query = st.text_input("Search request", value="smart funny science fiction with some heart")
        suggestions = [
            "slow-burn mystery I can watch with my parents",
            "underrated 90s action movies",
            "something uplifting after a hard week",
        ]
        chip_cols = st.columns(len(suggestions))
        for col, s in zip(chip_cols, suggestions):
            if col.button(s, key=f"suggest-{s}"):
                query = s
                st.session_state["search_results"] = cached_conversational_search(query)
        if st.button("Search", type="primary"):
            st.session_state["search_results"] = cached_conversational_search(query)
        render_results_with_genre_filter(
            st.session_state.get("search_results", []), key="search_genre_filter"
        )

    with tab_onboarding:
        st.caption(
            "No rating history yet? Describe what you like and we'll seed your first "
            "recommendations from content alone — no collaborative history required."
        )
        answers = st.text_area(
            "Taste notes",
            value="I like clever thrillers, heartfelt sci-fi, and movies with strong characters.",
            height=110,
        )
        if st.button("Find seed movies", type="primary"):
            st.session_state["onboarding_results"] = cached_onboard_new_user(answers)
        render_results_with_genre_filter(
            st.session_state.get("onboarding_results", []), key="onboarding_genre_filter"
        )

    with tab_watchlist:
        st.caption(
            "Movies you've saved with ☆ Save on any card, this session. "
            "Session-only — closing the tab clears it (no account/login in this demo)."
        )
        watchlist = st.session_state.get("watchlist", {})
        if not watchlist:
            st.info("No saved movies yet. Save one from any tab with the ☆ Save button.")
        else:
            for movie in watchlist.values():
                render_movie_card(movie, key_prefix="watchlist-")

    st.write("")
    st.divider()
    st.caption("CineMind — two-tower deep learning + LLM reasoning, on MovieLens 100K. [Source on GitHub](https://github.com/shaurya269/cinemind)")


if __name__ == "__main__":
    main()
