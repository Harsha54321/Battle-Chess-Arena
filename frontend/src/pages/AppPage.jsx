import { Link } from "react-router-dom";
import { ArrowLeft, Bell, Check, ChevronRight, Coins, Crown, Gift, Search, Settings, Shield, ShoppingBag, Swords, Trophy, UserRound, Users } from "lucide-react";
import ParticleBackground from "../components/ParticleBackground";
import GlowBackground from "../components/GlowBackground";
import "../styles/app-page.css";

const pageContent = {
  profile: { eyebrow: "PLAYER PROFILE", title: "Your battle identity", description: "Track your progress, ratings, and arena achievements.", icon: UserRound },
  notifications: { eyebrow: "INBOX", title: "Notifications", description: "Stay up to date with your matches, friends, and rewards.", icon: Bell },
  settings: { eyebrow: "CONTROL ROOM", title: "Game settings", description: "Tune your arena experience to your preference.", icon: Settings },
  rankings: { eyebrow: "GLOBAL ARENA", title: "Full rankings", description: "See the players shaping this season's leaderboard.", icon: Trophy },
  shop: { eyebrow: "ARENA SHOP", title: "Upgrade your loadout", description: "Use your coins to personalize your battle station.", icon: ShoppingBag },
  rewards: { eyebrow: "DAILY REWARDS", title: "Claim your streak", description: "Come back each day to unlock bigger rewards.", icon: Gift },
  friends: { eyebrow: "SOCIAL ARENA", title: "Your friends", description: "Challenge your squad or find a new rival.", icon: Users },
  ai: { eyebrow: "SOLO ARENA", title: "Play vs AI", description: "Choose your difficulty and sharpen your tactics.", icon: Shield },
  multiplayer: { eyebrow: "LIVE ARENA", title: "Multiplayer", description: "Invite a friend or jump into a competitive match.", icon: Swords },
  tournament: { eyebrow: "TOURNAMENT HALL", title: "Compete for glory", description: "Enter an event and climb the bracket.", icon: Crown },
};

const rankings = ["kaiser_knight", "NovaBishop", "QueenVoltage", "RookRunner", "PixelPawn", "Checkmate42"];
const friends = ["Maya Knight", "Rook Runner", "Bishop Zero"];

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
        {isMode && <ModeContent type={type} />}
      </section>
    </main>
  );
}

function Panel({ children, className = "" }) { return <div className={`app-panel ${className}`}>{children}</div>; }
function ProfileContent() { return <div className="app-grid profile-grid"><Panel className="profile-hero"><div className="large-avatar">K</div><div><h2>kaiser_knight</h2><p>Level 45 · 2,450 ELO</p><span className="online-badge">ONLINE NOW</span></div></Panel><Panel><p className="app-eyebrow">SEASON RECORD</p><div className="stat-row"><strong>128</strong><span>Matches played</span><strong>74%</strong><span>Win rate</span></div></Panel><Panel><p className="app-eyebrow">ACHIEVEMENTS</p><div className="achievement-row"><span>♛</span><span>First blood</span><Check size={16} /></div><div className="achievement-row"><span>⚡</span><span>Ten win streak</span><Check size={16} /></div></Panel></div>; }
function NotificationsContent() { return <div className="app-list">{["Maya Knight challenged you to a match", "Your daily reward is ready to claim", "You moved up to rank #142 globally"].map((item, index) => <Panel key={item}><div className="list-item"><div className="list-icon"><Bell size={17} /></div><div><strong>{item}</strong><span>{index + 2} hours ago</span></div><ChevronRight size={17} /></div></Panel>)}</div>; }
function SettingsContent() { return <div className="app-grid settings-grid"><Panel>{["Sound effects", "Move confirmations", "Show coordinates"].map((item) => <div className="setting-row" key={item}><span>{item}</span><button type="button" className="toggle toggle-on" aria-label={`Toggle ${item}`}><span /></button></div>)}</Panel><Panel><p className="app-eyebrow">ACCOUNT</p><div className="setting-row"><span>Connected account</span><strong>Guest profile</strong></div><div className="setting-row"><span>Privacy</span><strong>Friends only</strong></div></Panel></div>; }
function RankingsContent() { return <Panel className="rankings-panel"><div className="search-row"><div className="search-box"><Search size={16} /><input placeholder="Search players" /></div><span>SEASON 04</span></div>{rankings.map((player, index) => <div className="ranking-row" key={player}><strong>#{index + 1}</strong><div className="ranking-avatar">{player[0]}</div><span>{player}</span><em>{2450 - index * 38} ELO</em></div>)}</Panel>; }
function ShopContent() { return <div className="app-grid shop-grid">{["Neon crown", "Jade board", "Champion frame"].map((item, index) => <Panel className="shop-item" key={item}><div className="shop-art">{index === 0 ? "♛" : index === 1 ? "▦" : "◈"}</div><h2>{item}</h2><p>Rare arena cosmetic</p><button type="button" className="gold-action"><Coins size={15} /> {index + 1}50</button></Panel>)}</div>; }
function RewardsContent() { return <div className="app-grid reward-grid"><Panel className="streak-panel"><p className="app-eyebrow">CURRENT STREAK</p><strong>4 DAYS</strong><div className="reward-days">{["M", "T", "W", "T", "F", "S", "S"].map((day, index) => <span className={index < 4 ? "claimed" : ""} key={`${day}-${index}`}>{index < 4 ? <Check size={14} /> : day}</span>)}</div><button type="button" className="gold-action"><Gift size={16} /> Claim 250 coins</button></Panel><Panel><p className="app-eyebrow">NEXT MILESTONE</p><h2>Champion's cache</h2><p className="app-description">Return for 3 more days to unlock an exclusive board effect.</p></Panel></div>; }
function FriendsContent() { return <><div className="search-row friend-search"><div className="search-box"><Search size={16} /><input placeholder="Find a friend by username" /></div><button type="button" className="cyan-action">Add friend</button></div><div className="app-list">{friends.map((friend) => <Panel key={friend}><div className="list-item"><div className="ranking-avatar">{friend[0]}</div><div><strong>{friend}</strong><span>Online · 1,830 ELO</span></div><button type="button" className="small-action">Challenge</button></div></Panel>)}</div></>; }
function ModeContent({ type }) { const label = type === "ai" ? "Choose difficulty" : type === "multiplayer" ? "Find an opponent" : "Upcoming events"; return <div className="app-grid mode-grid-page"><Panel><p className="app-eyebrow">{label}</p>{(type === "ai" ? ["Rookie", "Veteran", "Grandmaster"] : type === "multiplayer" ? ["Quick match", "Private room", "Invite a friend"] : ["Neon Blitz Cup", "Arena Masters", "Weekend Royale"]).map((item, index) => <Link to={type === "tournament" ? "/tournament" : "/game"} className="mode-choice" key={item}><span>{item}</span><em>{type === "ai" ? `${index + 1} / 3` : type === "tournament" ? "Join event" : "Play now"}</em><ChevronRight size={17} /></Link>)}</Panel><Panel className="mode-aside"><Trophy size={30} /><h2>Ready for battle?</h2><p>Every move shapes your arena legacy.</p><Link to="/game" className="cyan-action">Enter arena <ArrowLeft size={15} className="rotate-180" /></Link></Panel></div>; }

export default AppPage;