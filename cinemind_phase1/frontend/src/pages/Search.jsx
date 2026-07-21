import ChatSearch from "../components/ChatSearch";

export default function Search() {
  return (
    <section>
      <h2>Conversational search</h2>
      <p className="muted">
        Free-text request -&gt; parsed intent -&gt; grounded retrieval -&gt;
        LLM re-rank -&gt; explanation for the top pick. Every result is a real
        movie from the catalogue -- the LLM never invents a title.
      </p>
      <ChatSearch />
    </section>
  );
}
