import ChatSearch from "../components/ChatSearch";

export default function Search() {
  return (
    <section>
      <h2>Conversational search</h2>
      <p className="muted">
        Free-text request &rarr; parsed intent &rarr; grounded retrieval &rarr;
        LLM re-rank &rarr; explanation for the top pick. Every result is a real
        movie from the catalogue &mdash; the LLM never invents a title.
      </p>
      <ChatSearch />
    </section>
  );
}
