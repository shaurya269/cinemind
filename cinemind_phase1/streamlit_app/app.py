"""
CineMind Streamlit demo.

Run from the project root:
    streamlit run streamlit_app/app.py
"""

import os
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


st.set_page_config(page_title="CineMind", page_icon="CM", layout="wide")


@st.cache_resource(show_spinner="Loading recommendation artifacts...")
def load_recommender():
    recommender.load()
    graph.load()
    return True


def render_movie_card(movie, *, show_feedback=False, user_id=None):
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
            top = st.columns([0.68, 0.16, 0.16])
            top[0].subheader(title)
            top[1].metric("Movie ID", movie_id)
            if score is not None:
                top[2].metric("Score", f"{float(score):.3f}")
            st.caption(genres)

            if overview:
                st.write(overview)
            if cast:
                st.caption(f"Cast: {cast}")
            if movie.get("why"):
                st.write(movie["why"])

        actions = st.columns([0.25, 0.25, 0.17, 0.17, 0.16])
        if actions[0].button("Explain", key=f"explain-{movie_id}-{title}"):
            st.info(llm_chains.explain_recommendation(movie_id) or "No metadata found.")
        if actions[1].button("Graph insights", key=f"graph-{movie_id}-{title}"):
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
            if actions[2].button("Liked", key=f"like-{movie_id}"):
                st.success(feedback.log_feedback(user_id, movie_id, clicked=True, rating=5.0))
            if actions[3].button("Skip", key=f"skip-{movie_id}"):
                st.success(feedback.log_feedback(user_id, movie_id, clicked=False))
            if actions[4].button("Similar", key=f"similar-{movie_id}"):
                for neighbour in recommender.similar_to_movie(movie_id, k=3):
                    st.write(f"{neighbour['title']} ({neighbour['score']:.3f})")


def main():
    st.title("CineMind")
    st.caption("Hybrid movie recommendations from collaborative vectors, content search, and optional LLM reranking.")

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

    tab_recs, tab_search, tab_onboarding = st.tabs([
        "Returning user",
        "Conversational search",
        "New user",
    ])

    # Results are stashed in session_state and re-rendered on every script
    # run (not just the run where the primary button was clicked) --
    # otherwise clicking ANY per-card button (Explain, Graph insights,
    # Liked, ...) triggers a Streamlit rerun where the primary button's
    # own st.button() call returns False again, and the whole list of
    # results would vanish even though nothing about them changed.
    with tab_recs:
        user_id = st.number_input("User ID", min_value=1, max_value=943, value=42, step=1)
        k = st.slider("Recommendations", 5, 20, 10)
        if st.button("Recommend", type="primary"):
            if not recommender.known_user(int(user_id)):
                st.session_state["recs_warning"] = "No training history for this user. Try the new-user tab."
                st.session_state.pop("recs_results", None)
            else:
                st.session_state.pop("recs_warning", None)
                st.session_state["recs_results"] = recommender.recommend_for_user(int(user_id), k=int(k))
                st.session_state["recs_user_id"] = int(user_id)

        if st.session_state.get("recs_warning"):
            st.warning(st.session_state["recs_warning"])
        for movie in st.session_state.get("recs_results", []):
            render_movie_card(movie, show_feedback=True, user_id=st.session_state["recs_user_id"])

    with tab_search:
        query = st.text_input("Search request", value="smart funny science fiction with some heart")
        if st.button("Search", type="primary"):
            st.session_state["search_results"] = llm_chains.conversational_search(query)
        for movie in st.session_state.get("search_results", []):
            render_movie_card(movie)

    with tab_onboarding:
        answers = st.text_area(
            "Taste notes",
            value="I like clever thrillers, heartfelt sci-fi, and movies with strong characters.",
            height=110,
        )
        if st.button("Find seed movies", type="primary"):
            st.session_state["onboarding_results"] = llm_chains.onboard_new_user(answers)
        for movie in st.session_state.get("onboarding_results", []):
            render_movie_card(movie)


if __name__ == "__main__":
    main()
