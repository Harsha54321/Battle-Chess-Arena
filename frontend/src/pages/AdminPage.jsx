import { useEffect, useState } from "react";
import { Activity, Ban, ChevronLeft, ChevronRight, Gift, LogOut, Search, ShieldCheck, Users } from "lucide-react";
import "../styles/admin.css";

const API_ROOT = `${import.meta.env.VITE_API_URL || "http://127.0.0.1:8000/api"}/admin`;
const ADMIN_TOKEN_KEY = "battleChessAdminToken";

async function adminRequest(path, token, options = {}) {
  const response = await fetch(`${API_ROOT}${path}`, {
    ...options,
    headers: {
      "Content-Type": "application/json",
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
      ...options.headers,
    },
  });
  const data = await response.json();
  if (!response.ok) {
    if (response.status === 401 && token) sessionStorage.removeItem(ADMIN_TOKEN_KEY);
    throw new Error(data.error || "Admin request failed.");
  }
  return data;
}

function AdminPage() {
  const [token, setToken] = useState(() => sessionStorage.getItem(ADMIN_TOKEN_KEY) || "");
  const [admin, setAdmin] = useState(null);
  const [overview, setOverview] = useState(null);
  const [players, setPlayers] = useState([]);
  const [matches, setMatches] = useState([]);
  const [challengeConfig, setChallengeConfig] = useState(null);
  const [challengeTarget, setChallengeTarget] = useState("");
  const [challengeReward, setChallengeReward] = useState("");
  const [challengeNotice, setChallengeNotice] = useState("");
  const [isSavingChallenge, setIsSavingChallenge] = useState(false);
  const [activeTab, setActiveTab] = useState("overview");
  const [query, setQuery] = useState("");
  const [page, setPage] = useState(1);
  const [pagination, setPagination] = useState(null);
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [isLoading, setIsLoading] = useState(() => Boolean(sessionStorage.getItem(ADMIN_TOKEN_KEY)));
  const [busyPlayerId, setBusyPlayerId] = useState("");

  useEffect(() => {
    if (!token) return;
    let current = true;
    const requests = [adminRequest("/overview/", token)];
    if (activeTab === "players") {
      requests.push(adminRequest(`/players/?q=${encodeURIComponent(query)}&page=${page}`, token));
    }
    if (activeTab === "matches") requests.push(adminRequest("/matches/", token));
    if (activeTab === "challenges") requests.push(adminRequest("/challenges/", token));
    Promise.all(requests)
      .then(([overviewData, contentData]) => {
        if (!current) return;
        setAdmin(overviewData.admin);
        setOverview(overviewData.overview);
        if (activeTab === "players") {
          setPlayers(contentData.players);
          setPagination(contentData.pagination);
        }
        if (activeTab === "matches") setMatches(contentData.matches);
        if (activeTab === "challenges") {
          setChallengeConfig(contentData);
          setChallengeTarget(String(contentData.target));
          setChallengeReward(String(contentData.reward_coins));
        }
        setError("");
      })
      .catch((requestError) => {
        if (!current) return;
        setError(requestError.message);
        if (!sessionStorage.getItem(ADMIN_TOKEN_KEY)) {
          setToken("");
          setAdmin(null);
        }
      })
      .finally(() => {
        if (current) setIsLoading(false);
      });
    return () => { current = false; };
  }, [token, activeTab, query, page]);

  async function handleLogin(event) {
    event.preventDefault();
    setIsLoading(true);
    setError("");
    try {
      const data = await adminRequest("/login/", "", {
        method: "POST",
        body: JSON.stringify({ username, password }),
      });
      sessionStorage.setItem(ADMIN_TOKEN_KEY, data.token);
      setAdmin(data.admin);
      setToken(data.token);
      setPassword("");
    } catch (loginError) {
      setError(loginError.message);
    } finally {
      setIsLoading(false);
    }
  }

  async function handleSuspension(player) {
    const suspended = !player.is_suspended;
    const action = suspended ? "suspend" : "restore access for";
    if (!window.confirm(`Are you sure you want to ${action} ${player.username}?`)) return;
    setBusyPlayerId(player.id);
    setError("");
    try {
      await adminRequest(`/players/${player.id}/suspension/`, token, {
        method: "POST",
        body: JSON.stringify({ suspended }),
      });
      setPlayers((current) => current.map((item) => (
        item.id === player.id ? { ...item, is_suspended: suspended } : item
      )));
      const refreshed = await adminRequest("/overview/", token);
      setOverview(refreshed.overview);
    } catch (requestError) {
      setError(requestError.message);
    } finally {
      setBusyPlayerId("");
    }
  }

  async function handleChallengeSave(event) {
    event.preventDefault();
    setIsSavingChallenge(true);
    setError("");
    setChallengeNotice("");
    try {
      const data = await adminRequest("/challenges/", token, {
        method: "POST",
        body: JSON.stringify({
          target: Number(challengeTarget),
          reward_coins: Number(challengeReward),
        }),
      });
      setChallengeConfig(data);
      setChallengeTarget(String(data.target));
      setChallengeReward(String(data.reward_coins));
      setChallengeNotice("Settings saved and applied to today's active challenges.");
    } catch (requestError) {
      setError(requestError.message);
    } finally {
      setIsSavingChallenge(false);
    }
  }

  function handleLogout() {
    sessionStorage.removeItem(ADMIN_TOKEN_KEY);
    setToken("");
    setAdmin(null);
    setOverview(null);
    setPlayers([]);
    setMatches([]);
    setPassword("");
    setError("");
  }

  if (!token) {
    return <main className="admin-shell admin-login-shell">
      <section className="admin-login-card">
        <div className="admin-mark"><ShieldCheck size={26} /></div>
        <p className="admin-eyebrow">BATTLE CHESS ARENA · RESTRICTED</p>
        <h1>Administrator login</h1>
        <p className="admin-muted">Sign in with an authorized staff account to manage the arena.</p>
        <form className="admin-login-form" onSubmit={handleLogin}>
          <label>Username<input autoComplete="username" value={username} onChange={(event) => setUsername(event.target.value)} required /></label>
          <label>Password<input type="password" autoComplete="current-password" value={password} onChange={(event) => setPassword(event.target.value)} required /></label>
          {error && <p className="admin-error" role="alert">{error}</p>}
          <button className="admin-primary-button" type="submit" disabled={isLoading}>{isLoading ? "VERIFYING..." : "SIGN IN SECURELY"}</button>
        </form>
      </section>
    </main>;
  }

  return <main className="admin-shell">
    <header className="admin-header">
      <div className="admin-brand"><span className="admin-mark"><ShieldCheck size={22} /></span><div><p className="admin-eyebrow">ARENA CONTROL</p><h1>Admin console</h1></div></div>
      <div className="admin-header-actions"><span>Signed in as <strong>{admin?.username || "Administrator"}</strong></span><button type="button" onClick={handleLogout}><LogOut size={15} /> Sign out</button></div>
    </header>
    <section className="admin-content">
      <nav className="admin-tabs" aria-label="Admin sections">
        {[["overview", "Overview"], ["players", "Players"], ["matches", "Matches"], ["challenges", "Challenges & rewards"]].map(([tab, label]) => <button type="button" key={tab} className={activeTab === tab ? "is-active" : ""} aria-current={activeTab === tab ? "page" : undefined} onClick={() => { setActiveTab(tab); setError(""); setChallengeNotice(""); setIsLoading(true); }}>{label}</button>)}
      </nav>
      {error && <p className="admin-error" role="alert">{error}</p>}
      {isLoading && !overview && <p className="admin-muted" role="status">Loading admin data...</p>}
      {activeTab === "overview" && overview && <section className="admin-metrics" aria-label="Arena overview">
        {[
          ["Players", overview.players_total, Users],
          ["Suspended players", overview.players_suspended, Ban],
          ["Matches in progress", overview.matches_active, Activity],
          ["Matches today", overview.matches_today, ShieldCheck],
          ["All matches", overview.matches_total, Activity],
        ].map(([label, value, Icon]) => <article className="admin-metric" key={label}><Icon size={18} /><span>{label}</span><strong>{value.toLocaleString()}</strong></article>)}
        <article className="admin-welcome"><p className="admin-eyebrow">ADMINISTRATION</p><h2>Keep the arena fair and running smoothly.</h2><p>Search the player list to review accounts and suspend access when needed. Suspension revokes active player sessions immediately.</p></article>
      </section>}
      {activeTab === "players" && <section className="admin-section">
        <div className="admin-section-heading"><div><p className="admin-eyebrow">ACCOUNT MANAGEMENT</p><h2>Players</h2></div><form className="admin-search" onSubmit={(event) => { event.preventDefault(); setPage(1); }}><Search size={16} /><input aria-label="Search players" placeholder="Username or player ID" value={query} onChange={(event) => { setQuery(event.target.value); setPage(1); setIsLoading(true); }} /></form></div>
        <div className="admin-table-wrap"><table className="admin-table"><thead><tr><th>Player</th><th>Rating</th><th>Level</th><th>Coins</th><th>Joined</th><th>Account</th><th>Action</th></tr></thead><tbody>
          {players.map((player) => <tr key={player.id}><td><strong>{player.username}</strong><small>{player.id}</small></td><td>{player.rating}</td><td>{player.level}</td><td>{player.coins}</td><td>{new Date(player.created_at).toLocaleDateString()}</td><td><span className={`admin-status ${player.is_suspended ? "is-suspended" : ""}`}>{player.is_suspended ? "Suspended" : "Active"}</span></td><td><button className={`admin-action ${player.is_suspended ? "is-restore" : "is-suspend"}`} type="button" disabled={busyPlayerId === player.id} onClick={() => handleSuspension(player)}>{busyPlayerId === player.id ? "Saving..." : player.is_suspended ? "Restore" : "Suspend"}</button></td></tr>)}
          {!players.length && !isLoading && <tr><td colSpan="7" className="admin-empty">No players matched your search.</td></tr>}
        </tbody></table></div>
        <div className="admin-pagination"><span>{pagination?.total || 0} players</span><div><button type="button" aria-label="Previous page" disabled={!pagination || page <= 1} onClick={() => { setPage((current) => current - 1); setIsLoading(true); }}><ChevronLeft size={16} /></button><span>Page {page} of {Math.max(1, pagination?.pages || 1)}</span><button type="button" aria-label="Next page" disabled={!pagination || page >= pagination.pages} onClick={() => { setPage((current) => current + 1); setIsLoading(true); }}><ChevronRight size={16} /></button></div></div>
      </section>}
      {activeTab === "matches" && <section className="admin-section">
        <div className="admin-section-heading"><div><p className="admin-eyebrow">ARENA ACTIVITY</p><h2>Recent matches</h2></div><span className="admin-muted">Latest 50</span></div>
        <div className="admin-table-wrap"><table className="admin-table"><thead><tr><th>Players</th><th>Mode</th><th>Status</th><th>Result</th><th>Started</th><th>Match ID</th></tr></thead><tbody>
          {matches.map((match) => <tr key={match.id}><td><strong>{match.white_player}</strong><small>vs {match.black_player}</small></td><td>{match.mode}</td><td><span className="admin-status">{match.status}</span></td><td>{match.result || "—"}</td><td>{new Date(match.created_at).toLocaleString()}</td><td><small>{match.id}</small></td></tr>)}
          {!matches.length && !isLoading && <tr><td colSpan="6" className="admin-empty">No matches to show.</td></tr>}
        </tbody></table></div>
      </section>}
      {activeTab === "challenges" && <section className="admin-section">
        <div className="admin-section-heading"><div><p className="admin-eyebrow">PLAYER REWARDS</p><h2>Daily challenge</h2></div><span className="admin-muted">Changes apply today</span></div>
        <p className="admin-challenge-description">Set how many quick-match wins players need to complete today's challenge and the coins they receive when claiming it. Existing unclaimed progress is preserved, and progress is adjusted if you lower the goal.</p>
        {challengeConfig && <form className="admin-challenge-form" onSubmit={handleChallengeSave}>
          <label>Wins required<input type="number" min="1" max="20" step="1" required value={challengeTarget} onChange={(event) => { setChallengeTarget(event.target.value); setChallengeNotice(""); }} /><small>Choose from 1 to 20 wins.</small></label>
          <label>Coin reward<input type="number" min="0" max="100000" step="1" required value={challengeReward} onChange={(event) => { setChallengeReward(event.target.value); setChallengeNotice(""); }} /><small>Choose from 0 to 100,000 coins.</small></label>
          <button className="admin-primary-button admin-challenge-save" type="submit" disabled={isSavingChallenge}>{isSavingChallenge ? "SAVING..." : <><Gift size={15} /> SAVE CHALLENGE</>}</button>
          {challengeNotice && <p className="admin-success" role="status">{challengeNotice}</p>}
        </form>}
        {!challengeConfig && isLoading && <p className="admin-muted" role="status">Loading challenge settings...</p>}
      </section>}
    </section>
  </main>;
}

export default AdminPage;
