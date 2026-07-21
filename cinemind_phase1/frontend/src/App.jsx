import { useEffect, useState } from "react";
import { NavLink, Route, Routes } from "react-router-dom";
import { checkHealth } from "./api";
import Home from "./pages/Home";
import Search from "./pages/Search";
import Profile from "./pages/Profile";
import "./App.css";

function App() {
  const [health, setHealth] = useState(null);

  useEffect(() => {
    checkHealth()
      .then(setHealth)
      .catch(() => setHealth({ status: "unreachable" }));
  }, []);

  return (
    <div className="app-shell">
      <header className="app-header">
        <div className="brand">CineMind</div>
        <nav className="app-nav">
          <NavLink to="/" end>
            Home
          </NavLink>
          <NavLink to="/search">Search</NavLink>
          <NavLink to="/profile">New user</NavLink>
        </nav>
        <div className="health-badge" title="Backend status">
          {health?.status === "ok" ? (
            <span className="badge badge-ok">
              API online - LLM: {health.llm_provider || "retrieval only"}
            </span>
          ) : health ? (
            <span className="badge badge-down">API unreachable</span>
          ) : (
            <span className="badge">Checking...</span>
          )}
        </div>
      </header>

      <main className="app-main">
        <Routes>
          <Route path="/" element={<Home />} />
          <Route path="/search" element={<Search />} />
          <Route path="/profile" element={<Profile />} />
        </Routes>
      </main>
    </div>
  );
}

export default App;
