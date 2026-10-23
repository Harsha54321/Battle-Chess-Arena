import { useEffect, useRef, useState } from "react";
import { Chess } from "chess.js";
import { AlertTriangle, ArrowLeft, BookOpen, Flag, Handshake, LoaderCircle, Maximize2, MessageCircle, RotateCcw, Send, Swords, Trophy, Volume2, X } from "lucide-react";
import { Link, useSearchParams } from "react-router-dom";
import { cancelMatchmaking, claimMatchDraw, connectToMatch, createMatch, getMatch, getMatchMessages, recordMove, sendMatchMessage, surrenderMatch } from "../services/api";
import { playMoveSound } from "../services/gameAudio";
import { getGameSettings, saveGameSettings, subscribeToGameSettings } from "../services/gameSettings";
import "../styles/game.css";
import "../styles/game-fixed.css";
import "../styles/game-chat.css";
import "../styles/game-overlays.css";

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

function getStoredPlayer() {
  try {
    return JSON.parse(localStorage.getItem("battleChessUser") || "null");
  } catch {
    return null;
  }
}

function getTerminationLabel(termination) {
  return {
    checkmate: "Checkmate",
    stalemate: "Stalemate",
    insufficient_material: "Insufficient material",
    seventyfive_moves: "75-move rule",
    fivefold_repetition: "Fivefold repetition",
    resignation: "Resignation",
    threefold_repetition: "Threefold repetition claimed",
    fifty_moves: "50-move rule claimed",
  }[termination] || "Game over";
}

function Game() {
  const [searchParams] = useSearchParams();
  const requestedMatchId = searchParams.get("match");
  const requestedMode = searchParams.get("mode") === "ai" ? "ai" : "quick_match";
  const requestedDifficulty = ["beginner", "intermediate", "advanced"].includes(searchParams.get("difficulty"))
    ? searchParams.get("difficulty")
    : "beginner";
  const [game, setGame] = useState(() => new Chess());
  const [selected, setSelected] = useState(null);
  const [theme, setTheme] = useState("nebula");
  const [settings, setSettings] = useState(getGameSettings);
  const [chatOpen, setChatOpen] = useState(false);
  const [chatMessage, setChatMessage] = useState("");
  const [chatMessages, setChatMessages] = useState([]);
  const [chatError, setChatError] = useState("");
  const [matchId, setMatchId] = useState(null);
  const [matchStatus, setMatchStatus] = useState(() => getStoredPlayer()?.id ? "starting" : "local");
  const [matchInfo, setMatchInfo] = useState(null);
  const [playerColor, setPlayerColor] = useState("w");
  const [pendingPromotion, setPendingPromotion] = useState(null);
  const [claimingDraw, setClaimingDraw] = useState(false);
  const [localTermination, setLocalTermination] = useState("");
  const [localResult, setLocalResult] = useState("");
  const [syncError, setSyncError] = useState("");
  const [realtimeConnected, setRealtimeConnected] = useState(false);
  const [isSubmittingMove, setIsSubmittingMove] = useState(false);
  const [savedMoveCount, setSavedMoveCount] = useState(0);
  const hasCreatedMatch = useRef(false);
  const moveInFlight = useRef(false);
  const board = game.board();
  const checkedKingRow = game.isCheck()
    ? board.findIndex((row) => row.some((piece) => piece?.type === "k" && piece.color === game.turn()))
    : -1;
  const checkedKingColumn = checkedKingRow >= 0
    ? board[checkedKingRow].findIndex((piece) => piece?.type === "k" && piece.color === game.turn())
    : -1;
  const checkedKingSquare = checkedKingColumn >= 0
    ? `${String.fromCharCode(97 + checkedKingColumn)}${8 - checkedKingRow}`
    : null;
  const displayedBoard = playerColor === "b"
    ? board.slice().reverse().map((row) => row.slice().reverse())
    : board;
  const history = matchId
    ? matchInfo?.moves?.map((move) => move.notation) || []
    : game.history();
  const legalTargets = selected ? game.moves({ square: selected, verbose: true }).map((move) => move.to) : [];
  const currentPlayer = getStoredPlayer();
  const yourPlayer = matchInfo
    ? playerColor === "w" ? matchInfo.white_player : matchInfo.black_player
    : currentPlayer;
  const isAiGame = matchInfo?.mode === "ai" || requestedMode === "ai";
  const aiDifficultyLabel = ({
    beginner: "Beginner",
    intermediate: "Intermediate",
    advanced: "Advanced",
  })[matchInfo?.ai_difficulty || requestedDifficulty];
  const opponent = matchInfo?.mode === "ai"
    ? { username: "Arena AI" }
    : matchInfo
      ? playerColor === "w" ? matchInfo.black_player : matchInfo.white_player
      : null;
  const isSearching = matchStatus === "waiting";
  const hasFinalResult = Boolean(matchInfo?.result || localResult);
  const isLocalGameOver = matchStatus === "local" && (game.isGameOver() || Boolean(localTermination));
  const showFinalDialog = matchStatus === "completed"
    || (matchStatus === "abandoned" && hasFinalResult)
    || isLocalGameOver;
  const finalResult = matchInfo?.result || localResult || (
    game.isCheckmate()
      ? game.turn() === "w" ? "black_wins" : "white_wins"
      : game.isDraw() ? "draw" : ""
  );
  const finalTermination = matchInfo?.termination || localTermination || (
    game.isCheckmate() ? "checkmate"
      : game.isStalemate() ? "stalemate"
        : game.isInsufficientMaterial() ? "insufficient_material"
          : game.isThreefoldRepetition() ? "threefold_repetition"
            : game.isDrawByFiftyMoves() ? "fifty_moves" : ""
  );
  const drawClaimAvailable = matchStatus === "synced"
    ? Boolean(matchInfo?.can_claim_draw)
    : matchStatus === "local" && (game.isThreefoldRepetition() || game.isDrawByFiftyMoves());
  const winnerColor = finalResult === "white_wins" ? "w" : finalResult === "black_wins" ? "b" : null;
  const outcomeText = finalResult === "draw"
    ? "Draw"
    : winnerColor === playerColor ? "You won" : winnerColor ? "You lost" : "Game ended";

  function appendChatMessages(incomingMessages) {
    const playerId = getStoredPlayer()?.id;
    setChatMessages((currentMessages) => {
      const messagesById = new Map(currentMessages.map((message) => [message.id, message]));
      incomingMessages.forEach((message) => {
        messagesById.set(message.id, {
          ...message,
          author: message.username,
          own: message.player_id === playerId,
        });
      });
      return [...messagesById.values()].sort((left, right) => (
        new Date(left.created_at) - new Date(right.created_at) || left.id - right.id
      ));
    });
  }

  useEffect(() => {
    if (hasCreatedMatch.current) return;
    hasCreatedMatch.current = true;

    const player = getStoredPlayer();

    if (!player?.id) {
      return;
    }

    const matchRequest = requestedMatchId
      ? getMatch(requestedMatchId)
      : createMatch(player.id, requestedMode, requestedDifficulty);
    matchRequest
      .then((match) => {
        applyMatchState(match, player.id);
        setMatchId(match.id);
        setSavedMoveCount(match.moves?.length || 0);
        if (match.fen && match.fen !== "startpos") setGame(new Chess(match.fen));
      })
      .catch((error) => {
        setMatchStatus("error");
        setSyncError(error.response?.data?.error || (
          requestedMatchId ? "This match is no longer available." : "Unable to create a match. Please try again."
        ));
      });
  }, [requestedMatchId, requestedMode, requestedDifficulty]);

  useEffect(() => subscribeToGameSettings(setSettings), []);

  function applyMatchState(match, playerId) {
    setMatchInfo(match);
    setPlayerColor(match.black_player?.id === playerId ? "b" : "w");
    setMatchStatus(match.status === "waiting" ? "waiting" : match.status === "active" ? "synced" : match.status);
  }

  useEffect(() => {
    if (!matchId || !["waiting", "synced"].includes(matchStatus) || (matchStatus === "synced" && realtimeConnected)) return undefined;
    const pollMatch = async () => {
      try {
        const match = await getMatch(matchId);
        if (moveInFlight.current) return;
        const player = getStoredPlayer();
        if (player?.id) applyMatchState(match, player.id);
        setSavedMoveCount(match.moves?.length || 0);
        if (match.fen && match.fen !== "startpos") {
          setGame((currentGame) => currentGame.fen() === match.fen ? currentGame : new Chess(match.fen));
        }
      } catch {
        setSyncError("Live match sync is temporarily unavailable. Reconnecting...");
      }
    };
    const intervalId = window.setInterval(pollMatch, 2000);
    return () => window.clearInterval(intervalId);
  }, [matchId, matchStatus, realtimeConnected]);

  useEffect(() => {
    if (!matchId || !chatOpen) return undefined;
    let isCurrent = true;
    getMatchMessages(matchId)
      .then((messages) => {
        if (!isCurrent) return;
        appendChatMessages(messages);
        setChatError("");
      })
      .catch((error) => {
        if (isCurrent) setChatError(error.response?.data?.error || "Unable to load match chat.");
      });
    return () => {
      isCurrent = false;
    };
  }, [matchId, chatOpen]);

  useEffect(() => {
    if (!matchId || !chatOpen) return undefined;
    const intervalId = window.setInterval(async () => {
      try {
        appendChatMessages(await getMatchMessages(matchId));
      } catch (error) {
        setChatError(error.response?.data?.error || "Match chat sync is unavailable.");
      }
    }, 3000);
    return () => window.clearInterval(intervalId);
  }, [matchId, chatOpen]);

  useEffect(() => {
    if (!matchId || matchStatus !== "synced" || matchInfo?.mode === "ai") return undefined;
    const socket = connectToMatch(
      matchId,
      (event) => {
        if (event.type === "chat_message") {
          appendChatMessages([event.message]);
          return;
        }
        if (event.type !== "match_snapshot" && event.type !== "match_update") return;
        const player = getStoredPlayer();
        if (player?.id) applyMatchState(event.match, player.id);
        setSavedMoveCount(event.match.moves?.length || 0);
        setGame((currentGame) => currentGame.fen() === event.match.fen
          ? currentGame
          : new Chess(event.match.fen));
        setSyncError("");
      },
      setRealtimeConnected,
    );
    return () => {
      socket?.close();
      setRealtimeConnected(false);
    };
  }, [matchId, matchStatus, matchInfo?.mode]);

  async function handleCancelSearch() {
    try {
      const response = await cancelMatchmaking(matchId);
      if (response.status === "already_matched") {
        const player = getStoredPlayer();
        if (player?.id) {
          applyMatchState(response.match, player.id);
          setGame(new Chess(response.match.fen));
        }
        return;
      }
      setMatchStatus("abandoned");
      setMatchId(null);
      setMatchInfo(null);
      setSyncError("");
    } catch (error) {
      setSyncError(error.response?.data?.error || "Unable to cancel matchmaking. Please try again.");
    }
  }

  async function commitMove(from, to, promotion) {
    const nextGame = new Chess(game.fen());
    let move;
    try {
      move = nextGame.move({ from, to, promotion });
    } catch {
      setSelected(null);
      setPendingPromotion(null);
      return;
    }
    setSelected(null);
    setPendingPromotion(null);

    const player = getStoredPlayer();
    if (matchId && player?.id) {
      moveInFlight.current = true;
      setIsSubmittingMove(true);
      setGame(nextGame);
      setMatchInfo((currentMatch) => currentMatch ? {
        ...currentMatch,
        moves: [...(currentMatch.moves || []), {
          move_number: savedMoveCount + 1,
          notation: move.san,
          from: move.from,
          to: move.to,
        }],
      } : currentMatch);
      try {
        const response = await recordMove(matchId, {
          move_number: savedMoveCount + 1,
          from: move.from,
          to: move.to,
          ...(move.promotion ? { promotion: move.promotion } : {}),
        });
        applyMatchState(response.match, player.id);
        setGame(new Chess(response.match.fen));
        setSavedMoveCount(response.match.moves.length);
        setSyncError("");
        playConfiguredMoveSound();
      } catch (error) {
        setSyncError(error.response?.data?.error || "Move could not be accepted by the server.");
        try {
          const latestMatch = await getMatch(matchId);
          applyMatchState(latestMatch, player.id);
          setGame(new Chess(latestMatch.fen));
          setSavedMoveCount(latestMatch.moves.length);
        } catch {
          setGame(game);
          setMatchInfo(matchInfo);
          setSyncError("Move could not be accepted, and the server state could not be refreshed.");
        }
      } finally {
        moveInFlight.current = false;
        setIsSubmittingMove(false);
      }
      return;
    }

    setGame(nextGame);
    playConfiguredMoveSound();
  }

  function playConfiguredMoveSound() {
    if (!settings.soundEffectsEnabled) return;
    playMoveSound().catch((error) => {
      setSyncError(error.message || "Game sound effects are unavailable.");
    });
  }

  async function handleSquareClick(square) {
    const piece = game.get(square);
    if ((matchStatus !== "local" && matchStatus !== "synced") || game.isGameOver() || pendingPromotion) return;
    if (moveInFlight.current) return;
    if (game.turn() !== playerColor) return;
    if (selected && legalTargets.includes(square)) {
      const matchingMoves = game.moves({ square: selected, verbose: true })
        .filter((move) => move.to === square);
      if (matchingMoves.some((move) => move.promotion)) {
        setPendingPromotion({ from: selected, to: square });
        setSelected(null);
      } else {
        await commitMove(selected, square, undefined);
      }
      return;
    }
    setSelected(piece && piece.color === game.turn() ? square : null);
  }

  function resetGame() {
    setGame(new Chess());
    setSelected(null);
    setPendingPromotion(null);
    setLocalTermination("");
    setLocalResult("");
  }

  async function handleClaimDraw() {
    if (!matchId || !drawClaimAvailable || claimingDraw) {
      if (!matchId && drawClaimAvailable) {
        setLocalTermination(game.isThreefoldRepetition() ? "threefold_repetition" : "fifty_moves");
        setLocalResult("draw");
      }
      return;
    }
    setClaimingDraw(true);
    try {
      const match = await claimMatchDraw(matchId);
      const player = getStoredPlayer();
      if (player?.id) applyMatchState(match, player.id);
      setGame(new Chess(match.fen));
      setSyncError("");
    } catch (error) {
      setSyncError(error.response?.data?.error || "The draw claim could not be accepted.");
    } finally {
      setClaimingDraw(false);
    }
  }

  async function sendChatMessage(event) {
    event.preventDefault();
    const message = chatMessage.trim();
    if (!message || !matchId || matchStatus !== "synced") return;
    setChatError("");
    try {
      const sent = await sendMatchMessage(matchId, message);
      appendChatMessages([sent]);
      setChatMessage("");
    } catch (error) {
      setChatError(error.response?.data?.error || "Message could not be sent. Please try again.");
    }
  }

  async function handleSurrender() {
    if (settings.confirmBeforeResigning && !window.confirm("Resign this game? This will count as a loss.")) return;
    const player = getStoredPlayer();
    if (!matchId || !player?.id) {
      setLocalTermination("resignation");
      setLocalResult(playerColor === "w" ? "black_wins" : "white_wins");
      return;
    }
    try {
      const match = await surrenderMatch(matchId, player.id);
      applyMatchState(match, player.id);
    } catch (error) {
      setSyncError(error.response?.data?.error || "Unable to surrender this match. Please try again.");
    }
  }

  return (
    <main className={`game-station theme-${theme} ${isSearching ? "is-searching" : ""}`}>
      <div className="game-atmosphere" aria-hidden="true"><span className="atmosphere-orb orb-one" /><span className="atmosphere-orb orb-two" /><span className="star-field" /></div>
      <header className="game-header">
        <Link to="/dashboard" className="back-link"><ArrowLeft size={17} /> Arena lobby</Link>
        <div className="match-title"><span className={`live-dot ${matchStatus === "synced" ? "live-dot-active" : ""}`} /> {isAiGame ? "AI match" : matchStatus === "local" ? "Local game" : "Quick match"}</div>
        <div className="header-actions">
          <button className="icon-button" type="button" onClick={() => {
            try {
              setSettings(saveGameSettings({ soundEffectsEnabled: !settings.soundEffectsEnabled }));
              setSyncError("");
            } catch {
              setSyncError("Game sound settings could not be saved.");
            }
          }} aria-label={settings.soundEffectsEnabled ? "Mute game" : "Unmute game"} title={settings.soundEffectsEnabled ? "Mute" : "Unmute"}><Volume2 size={18} /></button>
          {!isAiGame && <button className="icon-button" type="button" onClick={() => setChatOpen(true)} aria-label="Open chat" aria-expanded={chatOpen} title="Chat" disabled={!matchId || isSearching}><MessageCircle size={18} /></button>}
          <button className="icon-button" type="button" aria-label="Fullscreen" title="Fullscreen"><Maximize2 size={18} /></button>
        </div>
      </header>

      {chatOpen && <div className="chat-modal-backdrop" role="presentation" onMouseDown={(event) => { if (event.target === event.currentTarget) setChatOpen(false); }}>
        <section className="chat-modal" role="dialog" aria-modal="true" aria-labelledby="chat-modal-title">
          <div className="chat-modal-heading"><div><p className="panel-kicker">MATCH COMMUNICATION</p><h2 id="chat-modal-title">Live chat <span>● online</span></h2></div><button className="chat-close" type="button" onClick={() => setChatOpen(false)} aria-label="Close chat"><X size={18} /></button></div>
          <div className="chat-modal-messages">{chatMessages.length ? chatMessages.map((item, index) => <div className={`chat-message ${item.own ? "chat-message-own" : ""}`} key={item.id || `modal-${item.message}-${index}`}><span>{item.author || item.username}</span><p>{item.message}</p></div>) : <p className="chat-empty-state">No messages yet. Say hello to your opponent.</p>}</div>
          {chatError && <p className="chat-error" role="alert">{chatError}</p>}
          <form className="chat-form" onSubmit={sendChatMessage}><input autoFocus value={chatMessage} onChange={(event) => setChatMessage(event.target.value)} placeholder={matchStatus === "synced" ? "Send a message..." : "Match chat is read-only"} aria-label="Chat message" maxLength={500} disabled={matchStatus !== "synced"} /><button type="submit" aria-label="Send message" disabled={!chatMessage.trim() || matchStatus !== "synced"}><Send size={15} /></button></form>
        </section>
      </div>}

      <section className="game-layout">
        <aside className="player-rail player-rail-top">
          <div className="player-card">
            <div className="avatar avatar-cyan">{opponent?.username?.[0]?.toUpperCase() || "?"}</div>
            <div><strong>{opponent?.username || (isSearching ? "Searching..." : "Opponent")}</strong><span>{opponent ? isAiGame ? `${aiDifficultyLabel} · Black` : `${playerColor === "w" ? "Black" : "White"} · ${opponent.rating} ELO` : "Waiting to be paired"}</span></div>
          </div>
        </aside>
        <section className="board-zone" aria-label="Chess board">
          <div className="board-frame"><div className="chess-board">
            {displayedBoard.map((row, rowIndex) => row.map((piece, columnIndex) => {
              const rank = playerColor === "b" ? rowIndex + 1 : 8 - rowIndex;
              const fileIndex = playerColor === "b" ? 7 - columnIndex : columnIndex;
              const square = `${String.fromCharCode(97 + fileIndex)}${rank}`;
              const isDark = (fileIndex + 8 - rank) % 2 === 1;
              const isSelected = square === selected;
              const isTarget = legalTargets.includes(square);
              const inputDisabled = (matchStatus !== "local" && matchStatus !== "synced")
                || game.isGameOver()
                || showFinalDialog
                || isSubmittingMove
                || (matchStatus === "synced" && game.turn() !== playerColor)
                || Boolean(pendingPromotion);
              return <button className={`board-square ${isDark ? "square-dark" : "square-light"} ${isSelected ? "is-selected" : ""} ${isTarget ? "is-target" : ""} ${square === checkedKingSquare ? "is-in-check" : ""}`} key={square} type="button" onClick={() => handleSquareClick(square)} disabled={inputDisabled} aria-label={`${square}${piece ? ` ${piece.color === "w" ? "white" : "black"} ${piece.type}` : " empty"}${square === checkedKingSquare ? ", king in check" : ""}`}>
                {piece && <span className={`chess-piece piece-${piece.color}`}>{pieceGlyphs[piece.color][piece.type]}</span>}
                {settings.showCoordinates && columnIndex === 0 && <span className="rank-label">{rank}</span>}{settings.showCoordinates && rowIndex === 7 && <span className="file-label">{String.fromCharCode(97 + fileIndex)}</span>}
              </button>;
            }))}
          </div></div>
          <div className="board-caption">
            <span><Swords size={14} /> {isAiGame ? "AI BOARD" : matchStatus === "local" ? "LOCAL BOARD" : "LIVE BOARD"}</span>
            <em className={game.isCheck() ? "board-check-warning" : ""}>{game.isCheck() ? `CHECK! ${game.turn() === playerColor ? "Your" : "Opponent's"} king is under attack` : isSubmittingMove ? isAiGame ? "AI is thinking..." : "Saving move..." : matchStatus === "waiting" ? "Searching for an opponent" : matchStatus === "synced" ? `${game.turn() === playerColor ? "Your move" : isAiGame ? "AI to move" : "Opponent's move"} · ${realtimeConnected ? "live" : "syncing"}` : matchStatus === "starting" ? "Connecting to arena..." : showFinalDialog ? "Game over" : "Choose a piece"}</em>
          </div>
        </section>
        <aside className="game-sidebar">
          {syncError && <div className="station-panel sync-error" role="status">{syncError}</div>}
          {matchStatus === "abandoned" && !hasFinalResult && <div className="station-panel turn-panel"><div className="panel-kicker">SEARCH ENDED</div><div className="turn-value">Your queue has closed</div><div className="turn-meta">Start another match from the arena lobby.</div><Link to="/dashboard" className="surrender-button">Return to lobby</Link></div>}
          {matchStatus === "error" && <div className="station-panel turn-panel"><div className="panel-kicker">MATCH UNAVAILABLE</div><div className="turn-meta">Return to the lobby and try again.</div><Link to="/dashboard" className="surrender-button">Return to lobby</Link></div>}
          {!showFinalDialog && <div className={`station-panel turn-panel ${game.isCheck() ? "is-in-check" : ""}`}><div className="panel-kicker">CURRENT TURN</div><div className="turn-value"><span className="turn-indicator" />{isSubmittingMove && isAiGame ? "AI is thinking..." : matchStatus === "synced" ? game.turn() === playerColor ? "Your move" : isAiGame ? "AI to move" : "Opponent's move" : `${game.turn() === "w" ? "White" : "Black"} to move`}</div>{game.isCheck() ? <div className="check-warning" role="alert"><AlertTriangle size={16} /><span>CHECK! {game.turn() === playerColor ? "Your" : "Opponent's"} king is under attack.</span></div> : <div className="turn-meta">Only legal moves can be played</div>}</div>}
          {drawClaimAvailable && <button className="draw-claim-button" type="button" onClick={handleClaimDraw} disabled={claimingDraw}><Handshake size={16} />{claimingDraw ? "Claiming draw..." : "Claim a draw"}</button>}
          <div className="station-panel history-panel"><div className="panel-heading"><span>Battle log</span><span>{Math.ceil(history.length / 2)} / 40</span></div><div className="history-list">{history.length ? history.map((move, index) => <span key={`${move}-${index}`}>{formatMove(move, index)}</span>) : <p>No moves yet. The arena is waiting.</p>}</div></div>
          <div className="station-panel theme-panel"><div className="panel-kicker">BOARD ATMOSPHERE</div><div className="theme-options">{themes.map((item) => <button key={item.id} type="button" className={theme === item.id ? "theme-option selected-theme" : "theme-option"} onClick={() => setTheme(item.id)}><span style={{ backgroundColor: item.color }} />{item.label}</button>)}</div></div>
          {!matchId && <button className="reset-button" type="button" onClick={resetGame}><RotateCcw size={16} /> Reset battle</button>}
          {matchStatus === "synced" && <button className="surrender-button" type="button" onClick={handleSurrender}><Flag size={16} /> Resign game</button>}
        </aside>
        <aside className="player-rail player-rail-bottom">
          <div className="player-card active-player">
            <div className="avatar avatar-gold">{yourPlayer?.username?.[0]?.toUpperCase() || "Y"}</div>
            <div><strong>{yourPlayer?.username || "You"}</strong><span>{playerColor === "w" ? "White" : "Black"} · {yourPlayer?.rating ? `${yourPlayer.rating} ELO` : "Local player"}</span></div>
          </div>
        </aside>
      </section>

      {isSearching && <div className="matchmaking-overlay" role="dialog" aria-modal="true" aria-labelledby="matchmaking-title">
        <section className="matchmaking-card">
          <div className="matchmaking-spinner"><LoaderCircle size={28} /></div>
          <p className="panel-kicker">QUICK MATCH</p>
          <h1 id="matchmaking-title">Searching for opponent</h1>
          <p className="matchmaking-description">Your game will start automatically as soon as another player is paired.</p>
          <div className="matchmaking-pair">
            <div><span className="matchmaking-player-avatar">{yourPlayer?.username?.[0]?.toUpperCase() || "Y"}</span><strong>{yourPlayer?.username || "You"}</strong><small>{playerColor === "w" ? "White" : "Black"}</small></div>
            <span className="matchmaking-vs">VS</span>
            <div><span className="matchmaking-player-avatar matchmaking-opponent">?</span><strong>Opponent</strong><small>Waiting to join</small></div>
          </div>
          <div className="matchmaking-live"><span /> Queue is active · this board is locked until the match is ready</div>
          <button className="matchmaking-cancel" type="button" onClick={handleCancelSearch}>Cancel search</button>
        </section>
      </div>}

      {pendingPromotion && <div className="game-dialog-backdrop">
        <section className="game-dialog promotion-dialog" role="dialog" aria-modal="true" aria-labelledby="promotion-title">
          <p className="panel-kicker">PROMOTION</p>
          <h2 id="promotion-title">Choose a piece</h2>
          <div className="promotion-choices">
            {["q", "r", "b", "n"].map((piece) => <button key={piece} type="button" onClick={() => commitMove(pendingPromotion.from, pendingPromotion.to, piece)} aria-label={`Promote to ${({ q: "queen", r: "rook", b: "bishop", n: "knight" })[piece]}`}>
              <span className={`chess-piece piece-${playerColor}`}>{pieceGlyphs[playerColor][piece]}</span>
              <small>{({ q: "Queen", r: "Rook", b: "Bishop", n: "Knight" })[piece]}</small>
            </button>)}
          </div>
          <button className="game-dialog-secondary" type="button" onClick={() => setPendingPromotion(null)}>Cancel promotion</button>
        </section>
      </div>}

      {showFinalDialog && <div className="game-dialog-backdrop game-over-backdrop">
        <section className="game-dialog game-over-dialog" role="alertdialog" aria-modal="true" aria-labelledby="game-over-title" aria-describedby="game-over-description">
          <div className={`game-over-icon ${finalResult === "draw" ? "game-over-draw" : winnerColor === playerColor ? "game-over-win" : "game-over-loss"}`}>
            {finalResult === "draw" ? <Handshake size={26} /> : winnerColor === playerColor ? <Trophy size={26} /> : <Flag size={24} />}
          </div>
          <p className="panel-kicker">{getTerminationLabel(finalTermination)}</p>
          <h2 id="game-over-title">{outcomeText}</h2>
          <p id="game-over-description">{finalTermination === "checkmate" ? "Checkmate. All legal moves are now disabled." : finalTermination === "resignation" ? "The match ended when a player resigned." : finalResult === "draw" ? "The game has ended as a draw." : "The match has ended."}</p>
          <div className="game-over-actions">
            {matchId && savedMoveCount > 0 && <Link to={`/review/${matchId}`} className="game-dialog-primary"><BookOpen size={16} /> Review game</Link>}
            {!matchId && <button className="game-dialog-primary" type="button" onClick={resetGame}><RotateCcw size={16} /> New local game</button>}
            {isAiGame && <Link to="/play-vs-ai" className="game-dialog-primary"><RotateCcw size={16} /> Play AI again</Link>}
            <Link to="/dashboard" className="game-dialog-secondary">Return to lobby</Link>
          </div>
        </section>
      </div>}
    </main>
  );
}

export default Game;