import { useEffect, useState } from "react";
import { ArrowLeft, Send, Swords } from "lucide-react";
import { Link, useParams } from "react-router-dom";
import ParticleBackground from "../components/ParticleBackground";
import GlowBackground from "../components/GlowBackground";
import { getFriendMessages, getPlayer, sendFriendMessage } from "../services/api";
import "../styles/app-page.css";

function storedPlayer() {
  try {
    return JSON.parse(localStorage.getItem("battleChessUser") || "null");
  } catch {
    return null;
  }
}

function ChatPage() {
  const { friendId } = useParams();
  const player = storedPlayer();
  const [friend, setFriend] = useState({ username: "Friend", rating: 1200 });
  const [messages, setMessages] = useState([]);
  const [draft, setDraft] = useState("");

  useEffect(() => {
    if (!player?.id || !friendId) return;
    getPlayer(friendId).then(setFriend).catch(() => {});
    getFriendMessages(player.id, friendId).then(setMessages).catch(() => {});
  }, [friendId, player?.id]);

  async function sendMessage(event) {
    event.preventDefault();
    if (!player?.id || !draft.trim()) return;
    const message = await sendFriendMessage(player.id, friendId, draft.trim());
    setMessages((current) => [...current, message]);
    setDraft("");
  }

  return (
    <main className="app-page-shell">
      <ParticleBackground /><GlowBackground />
      <header className="app-page-header"><Link to="/friends" className="app-back-link"><ArrowLeft size={17} /> Friends</Link><span className="app-brand">BATTLE CHESS ARENA</span><Link to={`/game?friend=${friendId}`} className="app-profile-link" aria-label="Challenge friend"><Swords size={17} /></Link></header>
      <section className="app-page-content">
        <div className="chat-intro"><div className="chat-avatar">{friend.username.charAt(0).toUpperCase()}</div><div><p className="app-eyebrow">PRIVATE CHAT</p><h1>{friend.username}</h1><p className="app-description"><span className="chat-online-dot" /> {friend.rating} ELO · online now</p></div></div>
        <div className="app-panel chat-page-panel"><div className="chat-message-list">{messages.length ? messages.map((message) => { const own = message.sender_id === player?.id; return <div className={`chat-bubble-row ${own ? "chat-bubble-row-own" : ""}`} key={message.id}><div className={`chat-bubble ${own ? "chat-bubble-own" : ""}`}><span>{own ? "You" : friend.username}</span><p>{message.message}</p></div></div>; }) : <div className="chat-empty"><Send size={22} /><p>Start the conversation.</p><span>Say hello and plan your next match.</span></div>}</div><form className="chat-composer" onSubmit={sendMessage}><div className="chat-input-wrap"><input value={draft} onChange={(event) => setDraft(event.target.value)} placeholder="Write a message" aria-label="Chat message" maxLength={500} /><span>{draft.length}/500</span></div><button type="submit" className="chat-send-button" aria-label="Send message"><Send size={16} /></button></form></div>
      </section>
    </main>
  );
}

export default ChatPage;
