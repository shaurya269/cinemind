import { useEffect, useState } from "react";
import { NavLink, Route, Routes } from "react-router-dom";
import { checkHealth } from "./api";
import { useTheme } from "./hooks/useTheme";
import { useWatchlist } from "./hooks/useWatchlist";
import Landing from "./pages/Landing";
import Home from "./pages/Home";
import Search from "./pages/Search";
import Profile from "./pages/Profile";
import Watchlist from "./pages/Watchlist";
import "./App.css";

function App() {
  const [health, setHealth] = useState(null);
  const { theme, toggle } = useTheme();
  const { movies } = useWatchlist();

  useEffect(() => {
    checkHealth()
      .then(setHealth)
      .catch(() => setHealth({ status: "unreachable" }));
  }, []);

  return (
    <div className="app-shell">
      <header className="app-header">
        <NavLink to="/" className="brand">
          <span className="brand-mark">CineMind</span>
        </NavLink>
        <nav className="app-nav">
          <NavLink to="/app" end>
            Recommend
          </NavLink>
          <NavLink to="/search">Search</NavLink>
          <NavLink to="/profile">New user</NavLink>
          <NavLink to="/watchlist">
            Watchlist{movies.length > 0 ? ` (${movies.length})` : ""}
          </NavLink>
        </nav>
        <div className="app-header-right">
          <button
            className="theme-toggle"
            onClick={toggle}
            aria-label={`Switch to ${theme === "dark" ? "light" : "dark"} mode`}
            title={`Switch to ${theme === "dark" ? "light" : "dark"} mode`}
          >
            {theme === "dark" ? "☀" : "☽"}
          </button>
          <div className="health-badge" title="Backend status">
            {health?.status === "ok" ? (
              <span className="badge badge-ok">
                <span className="badge-dot" /> API online &middot; {health.llm_provider || "retrieval only"}
              </span>
            ) : health ? (
              <span className="badge badge-down">
                <span className="badge-dot" /> API unreachable
              </span>
            ) : (
              <span className="badge">Checking&hellip;</span>
            )}
          </div>
        </div>
      </header>

      <main className="app-main">
        <Routes>
          <Route path="/" element={<Landing />} />
          <Route path="/app" element={<Home />} />
          <Route path="/search" element={<Search />} />
          <Route path="/profile" element={<Profile />} />
          <Route path="/watchlist" element={<Watchlist />} />
        </Routes>
      </main>

      <footer className="app-footer">
        <span>CineMind &mdash; two-tower deep learning + LLM reasoning, on MovieLens 100K.</span>
        <a href="https://github.com/shaurya269/cinemind" target="_blank" rel="noreferrer">
          Source on GitHub
        </a>
      </footer>
    </div>
  );
}

export default App;
