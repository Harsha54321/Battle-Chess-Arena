import { useState } from "react";
import { Chess } from "chess.js";
import { ArrowLeft, Flag, Maximize2, MessageCircle, RotateCcw, Send, Swords, Volume2, X } from "lucide-react";
import { Link } from "react-router-dom";
import "../styles/game.css";
import "../styles/game-fixed.css";
import "../styles/game-chat.css";

const themes = [
  { id: "nebula", label: "Nebula", color: "#61dafb" },
  { id: "ember", label: "Ember", color: "#ff9b5b" },
  { id: "jade", label: "Jade", color: "#6be5a1" },
];

const pieceGlyphs = {
  w: { p: "♙", n: "♘", b: "♗", r: "♖", q: "♕", k: "♔" },
  b: { p: "♟", n: "♞", b: "♝", r: "♜", q: "♛", k: "♚" },
};

function formatMove(move, index) {
  return `${Math.floor(index / 2) + 1}${index % 2 === 0 ? "." : "..."} ${move}`;
}

function Game() {
  const [game, setGame] = useState(() => new Chess());
  const [selected, setSelected] = useState(null);
  const [theme, setTheme] = useState("nebula");
  const [muted, setMuted] = useState(false);
  const [chatOpen, setChatOpen] = useState(false);
  const [chatMessage, setChatMessage] = useState("");
  const [chatMessages, setChatMessages] = useState([
    { author: "kaiser_knight", message: "Good luck. Have fun!", own: false },
  ]);
  const board = game.board();
  const history = game.history();
  const legalTargets = selected ? game.moves({ square: selected, verbose: true }).map((move) => move.to) : [];

  function handleSquareClick(square) {
    const piece = game.get(square);
    if (selected && legalTargets.includes(square)) {
      const nextGame = new Chess(game.fen());
      nextGame.move({ from: selected, to: square, promotion: "q" });
      setGame(nextGame);
      setSelected(null);
      return;
    }
    setSelected(piece && piece.color === game.turn() ? square : null);
  }

  function resetGame() {
    setGame(new Chess());
    setSelected(null);
  }

  function sendChatMessage(event) {
    event.preventDefault();
    const message = chatMessage.trim();
    if (!message) return;
    setChatMessages((messages) => [...messages, { author: "you", message, own: true }]);
    setChatMessage("");
  }

  return (
    <main className={`game-station theme-${theme}`}>
      <div className="game-atmosphere" aria-hidden="true"><span className="atmosphere-orb orb-one" /><span className="atmosphere-orb orb-two" /><span className="star-field" /></div>
      <header className="game-header">
        <Link to="/dashboard" className="back-link"><ArrowLeft size={17} /> Arena lobby</Link>
        <div className="match-title"><span className="live-dot" /> Ranked match <strong>07:42</strong></div>
        <div className="header-actions">
          <button className="icon-button" type="button" onClick={() => setMuted(!muted)} aria-label={muted ? "Unmute game" : "Mute game"} title={muted ? "Unmute" : "Mute"}><Volume2 size={18} /></button>
          <button className="icon-button" type="button" onClick={() => setChatOpen(true)} aria-label="Open chat" aria-expanded={chatOpen} title="Chat"><MessageCircle size={18} /></button>
          <button className="icon-button" type="button" aria-label="Fullscreen" title="Fullscreen"><Maximize2 size={18} /></button>
        </div>
      </header>

      {chatOpen && <div className="chat-modal-backdrop" role="presentation" onMouseDown={(event) => { if (event.target === event.currentTarget) setChatOpen(false); }}>
        <section className="chat-modal" role="dialog" aria-modal="true" aria-labelledby="chat-modal-title">
          <div className="chat-modal-heading"><div><p className="panel-kicker">MATCH COMMUNICATION</p><h2 id="chat-modal-title">Live chat <span>● online</span></h2></div><button className="chat-close" type="button" onClick={() => setChatOpen(false)} aria-label="Close chat"><X size={18} /></button></div>
          <div className="chat-modal-messages">{chatMessages.map((item, index) => <div className={`chat-message ${item.own ? "chat-message-own" : ""}`} key={`modal-${item.message}-${index}`}><span>{item.author}</span><p>{item.message}</p></div>)}</div>
          <form className="chat-form" onSubmit={sendChatMessage}><input autoFocus value={chatMessage} onChange={(event) => setChatMessage(event.target.value)} placeholder="Send a message..." aria-label="Chat message" maxLength={160} /><button type="submit" aria-label="Send message"><Send size={15} /></button></form>
        </section>
      </div>}

      <section className="game-layout">
        <aside className="player-rail player-rail-top"><div className="player-card active-player"><div className="avatar avatar-cyan">K</div><div><strong>kaiser_knight</strong><span>rating 1,824</span></div><span className="captured-pieces">♟ ♟ ♞</span></div><div className="clock clock-light">08:31</div></aside>
        <section className="board-zone" aria-label="Chess board">
          <div className="board-frame"><div className="chess-board">
            {board.map((row, rowIndex) => row.map((piece, columnIndex) => {
              const square = `${String.fromCharCode(97 + columnIndex)}${8 - rowIndex}`;
              const isDark = (rowIndex + columnIndex) % 2 === 1;
              const isSelected = square === selected;
              const isTarget = legalTargets.includes(square);
              return <button className={`board-square ${isDark ? "square-dark" : "square-light"} ${isSelected ? "is-selected" : ""} ${isTarget ? "is-target" : ""}`} key={square} type="button" onClick={() => handleSquareClick(square)} aria-label={`${square}${piece ? ` ${piece.color === "w" ? "white" : "black"} ${piece.type}` : " empty"}`}>
                {piece && <span className={`chess-piece piece-${piece.color}`}>{pieceGlyphs[piece.color][piece.type]}</span>}
                {columnIndex === 0 && <span className="rank-label">{8 - rowIndex}</span>}{rowIndex === 7 && <span className="file-label">{String.fromCharCode(97 + columnIndex)}</span>}
              </button>;
            }))}
          </div></div>
          <div className="board-caption"><span><Swords size={14} /> LIVE BOARD</span><em>{game.isCheck() ? "Check" : "Your move is calculated locally"}</em></div>
        </section>
        <aside className="game-sidebar">
          <div className="station-panel turn-panel"><div className="panel-kicker">CURRENT TURN</div><div className="turn-value"><span className="turn-indicator" />{game.turn() === "w" ? "White" : "Black"} to move</div><div className="turn-meta">{game.isCheck() ? "King under attack" : "Choose a piece on the board"}</div></div>
          <div className="station-panel history-panel"><div className="panel-heading"><span>Battle log</span><span>{Math.ceil(history.length / 2)} / 40</span></div><div className="history-list">{history.length ? history.map((move, index) => <span key={`${move}-${index}`}>{formatMove(move, index)}</span>) : <p>No moves yet. The arena is waiting.</p>}</div></div>
          <div className="station-panel theme-panel"><div className="panel-kicker">BOARD ATMOSPHERE</div><div className="theme-options">{themes.map((item) => <button key={item.id} type="button" className={theme === item.id ? "theme-option selected-theme" : "theme-option"} onClick={() => setTheme(item.id)}><span style={{ backgroundColor: item.color }} />{item.label}</button>)}</div></div>
          <button className="reset-button" type="button" onClick={resetGame}><RotateCcw size={16} /> Reset battle</button><button className="surrender-button" type="button"><Flag size={16} /> Surrender match</button>
        </aside>
        <aside className="player-rail player-rail-bottom"><div className="player-card"><div className="avatar avatar-gold">Y</div><div><strong>you / challenger</strong><span>rating 1,790</span></div><span className="captured-pieces">♟ ♟</span></div><div className="clock clock-dark">09:04</div></aside>
      </section>
    </main>
  );
}

export default Game;