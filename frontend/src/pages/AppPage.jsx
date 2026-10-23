import { useEffect, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { Chess } from "chess.js";
import { ArrowLeft, Bell, Brain, Check, ChevronRight, Coins, Crown, Gift, Lightbulb, Music2, RotateCcw, Search, Settings, Shield, ShoppingBag, SlidersHorizontal, Swords, Trophy, UserRound, Users, Volume2 } from "lucide-react";
import ParticleBackground from "../components/ParticleBackground";
import GlowBackground from "../components/GlowBackground";
import { addFriend, challengeFriend, claimDailyChallenge, getDailyChallenge, getFriends, getNotifications, getPlayerProfileSummary, getPlayerTraining, markAllNotificationsRead, markNotificationRead, respondToChallenge, respondToFriendRequest, searchPlayers, submitTrainingAttempt } from "../services/api";
import { setBackgroundMusicVolume, startBackgroundMusic, stopBackgroundMusic } from "../services/gameAudio";
import { getGameSettings, saveGameSettings } from "../services/gameSettings";
import "../styles/app-page.css";
import "../styles/settings.css";
import "../styles/training.css";

const pageContent = {
  profile: { eyebrow: "PLAYER PROFILE", title: "Your battle identity", description: "Track your progress, ratings, and arena achievements.", icon: UserRound },
  notifications: { eyebrow: "INBOX", title: "Notifications", description: "Stay up to date with your matches, friends, and rewards.", icon: Bell },
  settings: { eyebrow: "CONTROL ROOM", title: "Game settings", description: "Tune your arena experience to your preference.", icon: Settings },
  rankings: { eyebrow: "GLOBAL ARENA", title: "Full rankings", description: "See the players shaping this season's leaderboard.", icon: Trophy },
  shop: { eyebrow: "ARENA SHOP", title: "Upgrade your loadout", description: "Use your coins to personalize your battle station.", icon: ShoppingBag },
  rewards: { eyebrow: "DAILY REWARDS", title: "Claim your streak", description: "Come back each day to unlock bigger rewards.", icon: Gift },
  friends: { eyebrow: "SOCIAL ARENA", title: "Your friends", description: "Challenge your squad or find a new rival.", icon: Users },
  ai: { eyebrow: "SOLO ARENA", title: "Play vs AI", description: "Choose your difficulty and sharpen your tactics.", icon: Shield },
  training: { eyebrow: "CHESS CLASSROOM", title: "Learn chess step by step", description: "Short guided lessons take you from the basics to advanced tactics.", icon: Brain },
  multiplayer: { eyebrow: "LIVE ARENA", title: "Multiplayer", description: "Invite a friend or jump into a competitive match.", icon: Swords },
  tournament: { eyebrow: "TOURNAMENT HALL", title: "Compete for glory", description: "Enter an event and climb the bracket.", icon: Crown },
};

const rankings = ["kaiser_knight", "NovaBishop", "QueenVoltage", "RookRunner", "PixelPawn", "Checkmate42"];
const aiDifficulties = [
  { id: "beginner", label: "Beginner", detail: "Relaxed practice" },
  { id: "intermediate", label: "Intermediate", detail: "A tactical challenge" },
  { id: "advanced", label: "Advanced", detail: "Think several moves ahead" },
];
const pieceGlyphs = {
  w: { p: "♙", n: "♘", b: "♗", r: "♖", q: "♕", k: "♔" },
  b: { p: "♟", n: "♞", b: "♝", r: "♜", q: "♛", k: "♚" },
};

function AppPage({ type }) {
  const content = pageContent[type];
  const PageIcon = content.icon;
  const isMode = ["ai", "multiplayer", "tournament"].includes(type);

  return (
    <main className="app-page-shell">
      <ParticleBackground /><GlowBackground />
      <header className="app-page-header"><Link to="/dashboard" className="app-back-link"><ArrowLeft size={17} /> Dashboard</Link><span className="app-brand">BATTLE CHESS ARENA</span><Link to="/profile" className="app-profile-link"><UserRound size={17} /></Link></header>
      <section className="app-page-content">
        <div className="app-page-intro"><div className="app-page-icon"><PageIcon size={28} /></div><div><p className="app-eyebrow">{content.eyebrow}</p><h1>{content.title}</h1><p className="app-description">{content.description}</p></div></div>
        {type === "profile" && <ProfileContent />}
        {type === "notifications" && <NotificationsContent />}
        {type === "settings" && <SettingsContent />}
        {type === "rankings" && <RankingsContent />}
        {type === "shop" && <ShopContent />}
        {type === "rewards" && <RewardsContent />}
        {type === "friends" && <FriendsContent />}
        {type === "training" && <TrainingContent />}
        {isMode && <ModeContent type={type} />}
      </section>
    </main>
  );
}

function Panel({ children, className = "" }) { return <div className={`app-panel ${className}`}>{children}</div>; }
function ProfileContent() {
  const [summary, setSummary] = useState(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState("");
  const playerId = getStoredPlayerId();

  useEffect(() => {
    let isCurrent = true;
    if (!playerId) return undefined;
    getPlayerProfileSummary(playerId)
      .then((data) => {
        if (isCurrent) {
          setSummary(data);
          setError("");
        }
      })
      .catch((requestError) => {
        if (isCurrent) setError(requestError.response?.data?.error || "Unable to load your profile.");
      })
      .finally(() => {
        if (isCurrent) setIsLoading(false);
      });
    return () => { isCurrent = false; };
  }, [playerId]);

  if (!playerId) return <Panel><p className="app-description" role="alert">Sign in to view your profile.</p></Panel>;
  if (isLoading) return <Panel><p className="app-description" role="status">Loading your profile...</p></Panel>;
  if (error || !summary) return <Panel><p className="app-description" role="alert">{error || "Profile information is unavailable."}</p></Panel>;

  const { player, stats, training, achievements } = summary;
  const winRate = stats.win_rate_percent === null ? "—" : `${stats.win_rate_percent}%`;
  const trainingCompletion = training.lessons_total
    ? Math.round(training.lessons_completed * 100 / training.lessons_total)
    : 0;

  return <div className="app-grid profile-grid">
    <Panel className="profile-hero">
      <div className="large-avatar">{player.avatar || player.username.charAt(0).toUpperCase()}</div>
      <div><h2>{player.username}</h2><p>Level {player.level} · {player.rating.toLocaleString()} ELO</p></div>
    </Panel>
    <Panel>
      <p className="app-eyebrow">MATCH RECORD</p>
      <div className="stat-row">
        <strong>{stats.matches_played}</strong><span>Matches played</span>
        <strong>{winRate}</strong><span>Win rate</span>
        <strong>{stats.wins}</strong><span>Wins</span>
        <strong>{stats.losses}</strong><span>Losses</span>
        <strong>{stats.draws}</strong><span>Draws</span>
      </div>
    </Panel>
    <Panel>
      <p className="app-eyebrow">TRAINING PROGRESS</p>
      <h2>{training.lessons_completed} / {training.lessons_total} lessons</h2>
      <div className="profile-progress-track" role="progressbar" aria-label="Training lessons completed" aria-valuenow={trainingCompletion} aria-valuemin={0} aria-valuemax={100}>
        <span style={{ width: `${trainingCompletion}%` }} />
      </div>
      <p className="app-description">{trainingCompletion}% of the chess course completed.</p>
    </Panel>
    <Panel>
      <p className="app-eyebrow">ACHIEVEMENTS</p>
      {achievements.length
        ? achievements.map((achievement) => <div className="achievement-row" key={achievement.id}>
          <span aria-hidden="true">✦</span><span><strong>{achievement.title}</strong><small>{achievement.description}</small></span><Check size={16} aria-label="Earned" />
        </div>)
        : <p className="app-description">No achievements yet. Play a match or complete a lesson to earn your first one.</p>}
    </Panel>
  </div>;
}
function getStoredPlayerId() {
  try {
    return JSON.parse(localStorage.getItem("battleChessUser") || "null")?.id || null;
  } catch {
    return null;
  }
}

function NotificationsContent() {
  const [items, setItems] = useState([]);
  const [unreadCount, setUnreadCount] = useState(0);
  const [isLoading, setIsLoading] = useState(true);
  const [busyId, setBusyId] = useState(null);
  const [error, setError] = useState("");
  const playerId = getStoredPlayerId();

  useEffect(() => {
    let isCurrent = true;
    if (!playerId) return undefined;
    getNotifications(playerId)
      .then((data) => {
        if (!isCurrent) return;
        setItems(data.notifications);
        setUnreadCount(data.unread_count);
        setError("");
      })
      .catch((requestError) => {
        if (isCurrent) setError(requestError.response?.data?.error || "Unable to load notifications.");
      })
      .finally(() => {
        if (isCurrent) setIsLoading(false);
      });
    return () => { isCurrent = false; };
  }, [playerId]);

  if (!playerId) return <Panel><p className="app-description" role="alert">Sign in to view your notifications.</p></Panel>;

  async function respond(item, action) {
    if (!playerId) return;
    setBusyId(item.id);
    setError("");
    try {
      if (item.type === "friend_request" && item.connection_id) {
        await respondToFriendRequest(item.connection_id, playerId, action);
      } else if (item.type === "match_challenge" && item.match_id) {
        await respondToChallenge(item.match_id, playerId, action);
      } else {
        throw new Error("This notification can no longer be acted on.");
      }
      if (item.type === "friend_request" && action === "reject") {
        setItems((current) => current.filter((notification) => notification.id !== item.id));
      } else {
        setItems((current) => current.map((notification) => (
          notification.id === item.id ? { ...notification, read: true } : notification
        )));
      }
      const nextUnreadCount = Math.max(0, unreadCount - (item.read ? 0 : 1));
      setUnreadCount(nextUnreadCount);
      window.dispatchEvent(new CustomEvent("notifications:unread-count", { detail: nextUnreadCount }));
      if (item.type === "match_challenge" && action === "accept" && item.match_id) {
        window.location.assign(`/game?match=${item.match_id}`);
      }
    } catch (requestError) {
      setError(requestError.response?.data?.error || requestError.message || "Unable to respond to this notification.");
    } finally {
      setBusyId(null);
    }
  }

  async function markRead(item) {
    if (!playerId || item.read) return;
    setBusyId(item.id);
    setError("");
    try {
      const result = await markNotificationRead(playerId, item.id);
      setItems((current) => current.map((notification) => (
        notification.id === item.id ? { ...notification, read: true } : notification
      )));
      setUnreadCount(result.unread_count);
      window.dispatchEvent(new CustomEvent("notifications:unread-count", { detail: result.unread_count }));
    } catch (requestError) {
      setError(requestError.response?.data?.error || "Unable to mark notification as read.");
    } finally {
      setBusyId(null);
    }
  }

  async function markAllRead() {
    if (!playerId || unreadCount === 0) return;
    setBusyId("all");
    setError("");
    try {
      const result = await markAllNotificationsRead(playerId);
      setItems((current) => current.map((notification) => ({ ...notification, read: true })));
      setUnreadCount(result.unread_count);
      window.dispatchEvent(new CustomEvent("notifications:unread-count", { detail: result.unread_count }));
    } catch (requestError) {
      setError(requestError.response?.data?.error || "Unable to mark notifications as read.");
    } finally {
      setBusyId(null);
    }
  }

  return <>
    <div className="notifications-toolbar">
      <span>{unreadCount} unread · latest {items.length}</span>
      <button type="button" disabled={unreadCount === 0 || busyId !== null} onClick={markAllRead}>{busyId === "all" ? "Marking..." : "Mark all as read"}</button>
    </div>
    {error && <p className="app-description" role="alert">{error}</p>}
    {isLoading
      ? <Panel><p className="app-description" role="status">Loading notifications...</p></Panel>
      : items.length
        ? <div className="app-list">{items.map((item) => {
          const actionable = item.type === "friend_request" || item.type === "match_challenge";
          return <Panel key={item.id}><div className={`list-item notification-item ${item.read ? "is-read" : "is-unread"}`}>
            <div className="list-icon"><Bell size={17} /></div>
            <div className="notification-copy"><strong>{item.message}</strong><span>{item.created_at ? new Date(item.created_at).toLocaleString() : ""} · {item.read ? "Read" : "Unread"}</span></div>
            {actionable && <div className="notification-actions">
              {!item.read && <button type="button" className="small-action" disabled={busyId !== null} onClick={() => markRead(item)}>Mark read</button>}
              <button type="button" className="small-action" disabled={busyId !== null} onClick={() => respond(item, "accept")}>Accept</button>
              <button type="button" className="small-action" disabled={busyId !== null} onClick={() => respond(item, "reject")}>Reject</button>
            </div>}
            {!actionable && !item.read && <button type="button" className="small-action" disabled={busyId !== null} onClick={() => markRead(item)}>{busyId === item.id ? "Saving..." : "Mark read"}</button>}
            {item.read && <Check size={17} aria-label="Read" />}
          </div></Panel>;
        })}</div>
        : error ? null : <Panel><p className="app-description">You’re all caught up. New friend requests and match challenges will appear here.</p></Panel>}
  </>;
}
function SettingsContent() {
  const [settings, setSettings] = useState(getGameSettings);
  const [error, setError] = useState("");

  useEffect(() => {
    if (!settings.backgroundMusicEnabled) return;
    let isCurrent = true;
    startBackgroundMusic(settings.musicVolume).catch((audioError) => {
      if (isCurrent) setError(`${audioError.message} Toggle music off and on to retry.`);
    });
    return () => { isCurrent = false; };
  }, [settings.backgroundMusicEnabled, settings.musicVolume]);

  function updateSettings(updates) {
    try {
      const nextSettings = saveGameSettings(updates);
      setSettings(nextSettings);
      setError("");
      return nextSettings;
    } catch {
      setError("Your settings could not be saved. Check browser storage permissions and try again.");
      return null;
    }
  }

  async function toggleMusic() {
    if (settings.backgroundMusicEnabled) {
      if (updateSettings({ backgroundMusicEnabled: false })) stopBackgroundMusic();
      return;
    }
    try {
      await startBackgroundMusic(settings.musicVolume);
      if (!updateSettings({ backgroundMusicEnabled: true })) stopBackgroundMusic();
    } catch (audioError) {
      setError(audioError.message || "Background music could not be started in this browser.");
    }
  }

  function updateVolume(event) {
    const volume = Number(event.target.value);
    const nextSettings = updateSettings({ musicVolume: volume });
    if (nextSettings) setBackgroundMusicVolume(volume);
  }

  function toggleSetting(key) {
    updateSettings({ [key]: !settings[key] });
  }

  return <>
    <div className="app-grid settings-grid">
      <Panel>
        <p className="app-eyebrow">AUDIO</p>
        <div className="setting-row"><span><Music2 size={16} /> Background music</span><button type="button" role="switch" aria-checked={settings.backgroundMusicEnabled} className={`toggle ${settings.backgroundMusicEnabled ? "toggle-on" : ""}`} aria-label="Background music" onClick={toggleMusic}><span /></button></div>
        <label className="settings-volume"><span><Volume2 size={16} /> Music volume <strong>{settings.musicVolume}%</strong></span><input aria-label="Music volume" type="range" min="0" max="100" value={settings.musicVolume} onChange={updateVolume} disabled={!settings.backgroundMusicEnabled} /></label>
        <div className="setting-row"><span><Volume2 size={16} /> Game sound effects</span><button type="button" role="switch" aria-checked={settings.soundEffectsEnabled} className={`toggle ${settings.soundEffectsEnabled ? "toggle-on" : ""}`} aria-label="Game sound effects" onClick={() => toggleSetting("soundEffectsEnabled")}><span /></button></div>
        <p className="settings-note">{settings.backgroundMusicEnabled ? "Ambient music is playing while this app is open." : "Turn on music to hear a calm, generated arena soundtrack."}</p>
      </Panel>
      <Panel>
        <p className="app-eyebrow"><SlidersHorizontal size={14} /> GAMEPLAY</p>
        <div className="setting-row"><span>Confirm before resigning</span><button type="button" role="switch" aria-checked={settings.confirmBeforeResigning} className={`toggle ${settings.confirmBeforeResigning ? "toggle-on" : ""}`} aria-label="Confirm before resigning" onClick={() => toggleSetting("confirmBeforeResigning")}><span /></button></div>
        <div className="setting-row"><span>Show board coordinates</span><button type="button" role="switch" aria-checked={settings.showCoordinates} className={`toggle ${settings.showCoordinates ? "toggle-on" : ""}`} aria-label="Show board coordinates" onClick={() => toggleSetting("showCoordinates")}><span /></button></div>
        <p className="settings-note">Your preferences are saved on this browser and applied to your next game.</p>
      </Panel>
    </div>
    {error && <p className="settings-error" role="alert">{error}</p>}
  </>;
}
function RankingsContent() { return <Panel className="rankings-panel"><div className="search-row"><div className="search-box"><Search size={16} /><input placeholder="Search players" /></div><span>SEASON 04</span></div>{rankings.map((player, index) => <div className="ranking-row" key={player}><strong>#{index + 1}</strong><div className="ranking-avatar">{player[0]}</div><span>{player}</span><em>{2450 - index * 38} ELO</em></div>)}</Panel>; }
function ShopContent() { return <div className="app-grid shop-grid">{["Neon crown", "Jade board", "Champion frame"].map((item, index) => <Panel className="shop-item" key={item}><div className="shop-art">{index === 0 ? "♛" : index === 1 ? "▦" : "◈"}</div><h2>{item}</h2><p>Rare arena cosmetic</p><button type="button" className="gold-action"><Coins size={15} /> {index + 1}50</button></Panel>)}</div>; }
function RewardsContent() {
  const [challenge, setChallenge] = useState({ progress: 0, target: 3, reward_coins: 500, claimed: false });
  const [claimError, setClaimError] = useState("");
  const [loadError, setLoadError] = useState("");
  const [isClaiming, setIsClaiming] = useState(false);
  const [playerId] = useState(() => {
    try {
      return JSON.parse(localStorage.getItem("battleChessUser") || "null")?.id || null;
    } catch {
      return null;
    }
  });

  useEffect(() => {
    if (playerId) getDailyChallenge(playerId).then(setChallenge).catch(() => setLoadError("Unable to load your daily challenge."));
  }, [playerId]);

  async function handleClaim() {
    if (!playerId) return;
    setClaimError("");
    setIsClaiming(true);
    try {
      setChallenge(await claimDailyChallenge(playerId));
      setLoadError("");
    } catch (error) {
      setClaimError(error.response?.data?.error || "Unable to claim the reward yet.");
    } finally {
      setIsClaiming(false);
    }
  }

  const canClaim = challenge.progress >= challenge.target && !challenge.claimed;
  return <div className="app-grid reward-grid"><Panel className="streak-panel"><p className="app-eyebrow">DAILY CHALLENGE</p><strong>{challenge.progress}/{challenge.target} WINS</strong><div className="reward-progress-track" role="progressbar" aria-label="Daily challenge progress" aria-valuemin={0} aria-valuemax={challenge.target} aria-valuenow={Math.min(challenge.progress, challenge.target)}><span style={{ width: `${Math.min((challenge.progress / challenge.target) * 100, 100)}%` }} /></div><button type="button" className="gold-action" disabled={!canClaim || isClaiming} onClick={handleClaim}><Gift size={16} /> {challenge.claimed ? "Reward claimed" : isClaiming ? "Claiming..." : `Claim ${challenge.reward_coins} coins`}</button>{loadError && <p className="app-description" role="alert">{loadError}</p>}{claimError && <p className="app-description" role="alert">{claimError}</p>}</Panel><Panel><p className="app-eyebrow">NEXT MILESTONE</p><h2>Champion's cache</h2><p className="app-description">{canClaim ? "Your reward is ready to claim." : `Win ${Math.max(challenge.target - challenge.progress, 0)} more quick matches today to unlock your reward.`}</p></Panel></div>;
}
function FriendsContent() {
  const playerId = getStoredPlayerId();
  const [friendList, setFriendList] = useState([]);
  const [query, setQuery] = useState("");
  const [results, setResults] = useState([]);
  const [error, setError] = useState("");
  const [challengeSent, setChallengeSent] = useState("");

  useEffect(() => {
    if (playerId) getFriends(playerId).then(setFriendList).catch(() => {});
  }, [playerId]);

  async function handleSearch(event) {
    event.preventDefault();
    if (!query.trim()) return setResults([]);
    setResults(await searchPlayers(query.trim()).catch(() => []));
  }

  async function handleAdd(friend) {
    if (!playerId) return;
    try {
      await addFriend(playerId, friend.id);
      setResults([]);
      setQuery("");
    } catch (requestError) {
      setError(requestError.response?.data?.error || "Unable to add this player.");
    }
  }

  async function handleChallenge(friend) {
    if (!playerId) return;
    try {
      await challengeFriend(playerId, friend.id);
      setChallengeSent(`Challenge sent to ${friend.username}.`);
    } catch (requestError) {
      setError(requestError.response?.data?.error || "Unable to send challenge.");
    }
  }

  return <>
    <form className="search-row friend-search" onSubmit={handleSearch}><div className="search-box"><Search size={16} /><input value={query} onChange={(event) => setQuery(event.target.value)} placeholder="Find a friend by username" /></div><button type="submit" className="cyan-action">Search</button></form>
    {results.length > 0 && <div className="app-list">{results.map((friend) => <Panel key={friend.id}><div className="list-item friend-row"><div className="ranking-avatar">{friend.username[0]}</div><div className="friend-details"><strong>{friend.username}</strong><span>{friend.rating} ELO</span></div><div className="friend-actions"><button type="button" className="small-action" onClick={() => handleAdd(friend)}>Add friend</button></div></div></Panel>)}</div>}
    {error && <p className="app-description" role="alert">{error}</p>}
    {challengeSent && <p className="app-description" role="status">{challengeSent}</p>}
    <div className="app-list">{friendList.length ? friendList.map((friend) => <Panel key={friend.id}><div className="list-item friend-row"><div className="ranking-avatar">{friend.username[0]}</div><div className="friend-details"><strong>{friend.username}</strong><span>{friend.rating} ELO · Connected</span></div><div className="friend-actions"><Link to={`/chat/${friend.id}`} className="small-action">Chat</Link><button type="button" className="small-action" onClick={() => handleChallenge(friend)}>Challenge</button></div></div></Panel>) : <Panel><p className="app-description">Search by username to connect with a friend.</p></Panel>}</div>
  </>;
}

function TrainingContent() {
  const [searchParams] = useSearchParams();
  const requestedLessonId = searchParams.get("lesson");
  const playerId = getStoredPlayerId();
  const [training, setTraining] = useState(null);
  const [activeLessonId, setActiveLessonId] = useState("");
  const [error, setError] = useState("");

  useEffect(() => {
    let isCurrent = true;
    if (!playerId) return undefined;
    getPlayerTraining(playerId)
      .then((data) => {
        if (!isCurrent) return;
        setTraining(data);
        const requestedLesson = data.lessons.find(
          (lesson) => lesson.id === requestedLessonId && (lesson.unlocked || lesson.completed),
        );
        setActiveLessonId(requestedLesson?.id || data.lessons.find((lesson) => lesson.unlocked && !lesson.completed)?.id || data.lessons[0]?.id || "");
        setError("");
      })
      .catch((requestError) => {
        if (isCurrent) setError(requestError.response?.data?.error || "Unable to load your training plan.");
      });
    return () => { isCurrent = false; };
  }, [playerId, requestedLessonId]);

  async function handleAttempt(attempt) {
    const result = await submitTrainingAttempt(playerId, attempt);
    if (result.correct) {
      try {
        const updated = await getPlayerTraining(playerId);
        setTraining(updated);
        setActiveLessonId(updated.lessons.find((lesson) => lesson.unlocked && !lesson.completed)?.id || attempt.lesson_id);
      } catch (requestError) {
        setError(requestError.response?.data?.error || "Your answer was saved, but progress could not be refreshed.");
      }
    }
    return result;
  }

  if (!playerId) return <Panel><p className="training-error" role="alert">Sign in to save training progress.</p></Panel>;
  if (error && !training) return <Panel><p className="training-error" role="alert">{error}</p></Panel>;
  if (!training) return <Panel><p className="training-loading" role="status">Loading your chess classes...</p></Panel>;

  const { progress, lessons } = training;
  const activeLesson = lessons.find((lesson) => lesson.id === activeLessonId)
    || lessons.find((lesson) => lesson.unlocked && !lesson.completed)
    || lessons[0];
  const completion = Math.round(progress.lessons_completed * 100 / progress.lessons_total);
  const courseComplete = progress.lessons_completed >= progress.lessons_total;
  const levels = [...new Set(lessons.map((lesson) => lesson.level))];

  return (
    <div className="training-page">
      <Panel className="training-course-summary">
        <div className="training-progress-heading">
          <div><p className="app-eyebrow">YOUR CHESS COURSE</p><h2>{progress.current_level_title} · {progress.lessons_completed} of {progress.lessons_total} lessons</h2></div>
          <span className="training-xp">{progress.training_xp} XP</span>
        </div>
        <div className="training-progress-track" role="progressbar" aria-label="Course progress" aria-valuenow={completion} aria-valuemin={0} aria-valuemax={100}>
          <span style={{ width: `${completion}%` }} />
        </div>
        <p className="training-progress-caption" role={courseComplete ? "status" : undefined}>
          {courseComplete
            ? `Course complete! You finished all ${progress.lessons_total} chess lessons.`
            : "Choose the next glowing lesson. Finish it to unlock the next class."}
        </p>
      </Panel>

      {training.game_trend && <Panel className="training-game-trend">
        <div className="training-trend-copy">
          <p className="app-eyebrow">MATCH-BY-MATCH COACH</p>
          {training.game_trend.focus
            ? <h2>{training.game_trend.focus_label}</h2>
            : <h2>Your recent game pattern</h2>}
          <p className="training-progress-caption">{training.game_trend.message}</p>
        </div>
        <div className="training-trend-detail">
          <span>{training.game_trend.matches_reviewed} recent games reviewed</span>
          {training.game_trend.focus && <span>{training.game_trend.matches_with_focus} games with this focus</span>}
          {training.game_trend.recommendation?.lesson_id && <button
            type="button"
            onClick={() => {
              setActiveLessonId(training.game_trend.recommendation.lesson_id);
              document.getElementById("training-lesson-area")?.scrollIntoView({ behavior: "smooth", block: "start" });
            }}
          >
            Practice: {training.game_trend.recommendation.lesson_title}
          </button>}
        </div>
      </Panel>}

      <div className="training-course-layout">
        <section className="training-curriculum">
          <div className="training-section-heading"><div><p className="app-eyebrow">YOUR LEARNING PATH</p><h2>Chess classes</h2></div><span>{progress.lessons_completed}/{progress.lessons_total} DONE</span></div>
          {levels.map((level) => {
            const levelLessons = lessons.filter((lesson) => lesson.level === level);
            const firstLesson = levelLessons[0];
            const levelDone = levelLessons.every((lesson) => lesson.completed);
            const levelActive = !courseComplete && level === progress.current_level;
            return <Panel className={`training-level ${levelActive ? "training-level-unlocked" : "training-level-collapsed"}`} key={level}>
              <div className="training-level-heading"><div><span className="training-level-number">{String(level).padStart(2, "0")}</span><div><p className="app-eyebrow">CLASS {level}</p><h3>{firstLesson.level_title}</h3></div></div><span className={levelDone ? "training-level-status is-complete" : ""}>{levelDone ? "COMPLETE" : levelActive ? "IN PROGRESS" : "LOCKED"}</span></div>
              {levelActive && levelLessons.map((lesson, index) => <button className={`training-lesson-row ${lesson.completed ? "is-complete" : ""} ${lesson.unlocked && !lesson.completed ? "is-next" : ""} ${activeLesson?.id === lesson.id ? "is-active" : ""}`} key={lesson.id} type="button" disabled={!lesson.unlocked} onClick={() => setActiveLessonId(lesson.id)}>
                <span className={`training-lesson-icon ${lesson.completed ? "is-complete" : ""}`}>{lesson.completed ? <Check size={16} /> : lesson.unlocked ? index + 1 : <span>•</span>}</span>
                <span className="training-lesson-copy"><strong>{lesson.title}</strong><small>{lesson.theme}</small></span>
                <span className="training-lesson-state">{lesson.completed ? "Done" : lesson.unlocked ? "Start" : "Locked"}</span>
              </button>)}
            </Panel>;
          })}
        </section>

        <aside className="training-lesson-area" id="training-lesson-area">
          {courseComplete && <Panel><p className="app-eyebrow">COURSE COMPLETE</p><h2>You finished all {progress.lessons_total} chess lessons</h2><p className="training-progress-caption">Your full learning path is complete. You can review your progress any time.</p></Panel>}
          {!courseComplete && activeLesson?.unlocked && <TrainingPuzzle key={activeLesson.id} lesson={activeLesson} onAttempt={handleAttempt} />}
          {!activeLesson?.unlocked && <Panel><p className="app-eyebrow">NEXT LESSON</p><h2>Keep going to unlock your next class</h2><p className="training-progress-caption">Complete the highlighted lesson on your learning path.</p></Panel>}
        </aside>
      </div>
      {error && <p className="training-error" role="alert">{error}</p>}
    </div>
  );
}

function TrainingPuzzle({ lesson, onAttempt }) {
  const [game, setGame] = useState(() => new Chess(lesson.fen));
  const [selected, setSelected] = useState(null);
  const [feedback, setFeedback] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [isSolved, setIsSolved] = useState(lesson.completed);
  const [hintIndex, setHintIndex] = useState(0);
  const playerColor = lesson.side_to_move === "black" ? "b" : "w";
  const rows = game.board();
  const displayedRows = playerColor === "b"
    ? rows.slice().reverse().map((row) => row.slice().reverse())
    : rows;
  const legalTargets = selected
    ? game.moves({ square: selected, verbose: true }).map((move) => move.to)
    : [];

  async function handleSquareClick(square) {
    if (isSubmitting || isSolved) return;
    const piece = game.get(square);
    if (selected && legalTargets.includes(square)) {
      const nextGame = new Chess(game.fen());
      const move = nextGame.move({ from: selected, to: square });
      if (!move) return;
      setSelected(null);
      setIsSubmitting(true);
      setGame(nextGame);
      try {
        const result = await onAttempt({
          lesson_id: lesson.id,
          from: move.from,
          to: move.to,
          ...(move.promotion ? { promotion: move.promotion } : {}),
        });
        setFeedback(result.feedback);
        setIsSolved(result.correct);
        if (!result.correct) setGame(new Chess(lesson.fen));
      } catch (requestError) {
        setGame(new Chess(lesson.fen));
        setFeedback(requestError.response?.data?.error || "Unable to save this attempt. Please try again.");
      } finally {
        setIsSubmitting(false);
      }
      return;
    }
    setSelected(piece?.color === playerColor ? square : null);
  }

  function resetPuzzle() {
    setGame(new Chess(lesson.fen));
    setSelected(null);
    setFeedback("");
    setIsSolved(lesson.completed);
    setHintIndex(0);
  }

  return <Panel className="training-puzzle-panel">
    <p className="app-eyebrow">TACTICAL CHALLENGE · LEVEL {lesson.level}</p>
    <h2>{lesson.title}</h2>
    <p className="training-puzzle-description">{lesson.objective}</p>
    <div className="training-thinking-guide">
      <p className="app-eyebrow">HOW TO THINK</p>
      <ol>{lesson.steps.map((step) => <li key={step}>{step}</li>)}</ol>
    </div>
    <div className="training-board" role="group" aria-label={`Training puzzle board: ${lesson.title}`}>
      {displayedRows.flatMap((row, rowIndex) => row.map((piece, columnIndex) => {
        const rank = playerColor === "b" ? rowIndex + 1 : 8 - rowIndex;
        const fileIndex = playerColor === "b" ? 7 - columnIndex : columnIndex;
        const square = `${String.fromCharCode(97 + fileIndex)}${rank}`;
        const dark = (fileIndex + 8 - rank) % 2 === 1;
        return <button
          className={`training-square ${dark ? "training-square-dark" : "training-square-light"} ${selected === square ? "is-selected" : ""} ${legalTargets.includes(square) ? "is-target" : ""}`}
          key={square}
          type="button"
          disabled={isSubmitting || isSolved}
          onClick={() => handleSquareClick(square)}
          aria-label={`${square}${piece ? ` ${piece.color === "w" ? "white" : "black"} ${piece.type}` : " empty"}`}
        >
          {piece && <span className={`training-piece training-piece-${piece.color}`}>{pieceGlyphs[piece.color][piece.type]}</span>}
          {columnIndex === 0 && <small className="training-coordinate">{rank}</small>}
          {rowIndex === 7 && <small className="training-coordinate training-file">{String.fromCharCode(97 + fileIndex)}</small>}
        </button>;
      }))}
    </div>
    <p className={`training-puzzle-status ${isSolved ? "is-solved" : feedback ? "has-feedback" : ""}`} role={feedback ? "status" : undefined}>
      {isSubmitting ? "Checking your move..." : feedback || `Your turn as ${lesson.side_to_move}. Find the strongest move.`}
    </p>
    {!isSolved && <div className="training-hint-box">
      {hintIndex > 0 && <p role="status"><Lightbulb size={14} /> Hint {hintIndex}: {lesson.hints[hintIndex - 1]}</p>}
      {hintIndex < lesson.hints.length && <button type="button" onClick={() => setHintIndex((current) => current + 1)}>
        <Lightbulb size={14} /> Show hint {hintIndex + 1} of {lesson.hints.length}
      </button>}
    </div>}
    <button className="training-reset" type="button" onClick={resetPuzzle}><RotateCcw size={14} /> Reset position</button>
  </Panel>;
}

function ModeContent({ type }) {
  const isAi = type === "ai";
  const label = isAi ? "Choose your AI level" : type === "multiplayer" ? "Find an opponent" : "Upcoming events";
  const choices = isAi
    ? aiDifficulties
    : (type === "multiplayer" ? ["Quick match", "Private room", "Invite a friend"] : ["Neon Blitz Cup", "Arena Masters", "Weekend Royale"])
      .map((name) => ({ id: name, label: name, detail: type === "tournament" ? "Join event" : "Play now" }));
  const destination = (choice) => isAi
    ? `/game?mode=ai&difficulty=${choice.id}`
    : type === "tournament" ? "/tournament" : "/game";

  return (
    <div className="app-grid mode-grid-page">
      <Panel>
        <p className="app-eyebrow">{label}</p>
        {choices.map((choice) => (
          <Link to={destination(choice)} className="mode-choice" key={choice.id}>
            <span>{choice.label}</span><em>{choice.detail}</em><ChevronRight size={17} />
          </Link>
        ))}
      </Panel>
      <Panel className="mode-aside">
        <Trophy size={30} />
        <h2>{isAi ? "Ready to train?" : "Ready for battle?"}</h2>
        <p>{isAi ? "Play a full chess game against a legal-move AI opponent." : "Every move shapes your arena legacy."}</p>
        <Link to={isAi ? "/game?mode=ai&difficulty=beginner" : "/game"} className="cyan-action">
          {isAi ? "Start beginner game" : "Enter arena"} <ArrowLeft size={15} className="rotate-180" />
        </Link>
      </Panel>
    </div>
  );
}

export default AppPage;