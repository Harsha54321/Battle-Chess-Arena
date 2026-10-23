import { useEffect, useState } from "react";
import { ArrowLeft, ChevronLeft, ChevronRight, RotateCcw } from "lucide-react";
import { Link, useParams } from "react-router-dom";
import { Chess } from "chess.js";
import { getMatchReview } from "../services/api";
import "../styles/game-review.css";

const pieceGlyphs = {
  w: { p: "♙", n: "♘", b: "♗", r: "♖", q: "♕", k: "♔" },
  b: { p: "♟", n: "♞", b: "♝", r: "♜", q: "♛", k: "♚" },
};

const qualityLabels = {
  checkmate: "Checkmate",
  blunder: "Blunder",
  mistake: "Mistake",
  missed_win: "Missed checkmate",
  missed_tactic: "Missed tactic",
  no_tactic: "No immediate tactic",
};

function GameReview() {
  const { matchId } = useParams();
  const [review, setReview] = useState(null);
  const [selectedPly, setSelectedPly] = useState(0);
  const [showAlternative, setShowAlternative] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    let isCurrent = true;
    getMatchReview(matchId)
      .then((data) => {
        if (!isCurrent) return;
        setReview(data);
        setSelectedPly(data.moves.length);
        setShowAlternative(false);
      })
      .catch((requestError) => {
        if (isCurrent) {
          setError(requestError.response?.data?.error || "Unable to load this game review.");
        }
      });
    return () => {
      isCurrent = false;
    };
  }, [matchId]);

  const selectedMove = selectedPly > 0 ? review?.moves[selectedPly - 1] : null;
  const isShowingAlternative = Boolean(showAlternative && selectedMove?.alternative_fen);
  const board = isShowingAlternative
    ? new Chess(selectedMove.alternative_fen).board()
    : selectedMove ? new Chess(selectedMove.fen).board() : new Chess().board();
  const highlightedSquares = isShowingAlternative
    ? [selectedMove.alternative_from, selectedMove.alternative_to]
    : selectedMove ? [selectedMove.from, selectedMove.to] : [];
  const summary = review?.summary;
  const opponentName = review?.match.mode === "ai"
    ? `Arena AI · ${review.match.ai_difficulty}`
    : review?.match.black_player || "Opponent";

  return (
    <main className="review-shell">
      <header className="review-header">
        <Link to="/dashboard" className="review-back"><ArrowLeft size={17} /> Arena lobby</Link>
        <span className="review-brand">BATTLE CHESS ARENA</span>
        <span />
      </header>

      <section className="review-content">
        <div className="review-title">
          <div>
            <p className="review-eyebrow">POST-GAME ANALYSIS</p>
            <h1>Review your match</h1>
            <p className="review-subtitle">
              {review
                ? `${review.match.white_player} vs ${opponentName} · ${review.match.result.replace("_", " ")}`
                : "Replay the game and learn from the key moments."}
            </p>
          </div>
          <div className="review-summary">
            <span><strong>{summary?.plies_reviewed ?? "—"}</strong> plies</span>
            <span><strong>{summary?.blunders ?? "—"}</strong> your blunders</span>
            <span><strong>{summary?.mistakes ?? "—"}</strong> your mistakes</span>
            <span><strong>{summary?.missed_tactics ?? "—"}</strong> your missed tactics</span>
          </div>
        </div>

        {error && <div className="review-error" role="alert">{error}<Link to="/dashboard"> Return to lobby</Link></div>}
        {!review && !error && <div className="review-loading" role="status">Loading your match review...</div>}

        {review && <div className="review-layout">
          <section className="review-board-panel" aria-label="Replay board">
            <div className="review-board">
              {board.flatMap((row, rowIndex) => row.map((piece, columnIndex) => {
                const square = `${String.fromCharCode(97 + columnIndex)}${8 - rowIndex}`;
                const lastMoveSquare = highlightedSquares.includes(square);
                const dark = (rowIndex + columnIndex) % 2 === 1;
                return <div
                  className={`review-square ${dark ? "review-square-dark" : "review-square-light"} ${lastMoveSquare ? "review-square-last" : ""}`}
                  key={square}
                  aria-label={`${square}${piece ? ` ${piece.color === "w" ? "white" : "black"} ${piece.type}` : " empty"}`}
                >
                  {piece && <span className={`review-piece review-piece-${piece.color}`}>{pieceGlyphs[piece.color][piece.type]}</span>}
                  {columnIndex === 0 && <span className="review-coordinate">{8 - rowIndex}</span>}
                  {rowIndex === 7 && <span className="review-coordinate review-file">{String.fromCharCode(97 + columnIndex)}</span>}
                </div>;
              }))}
            </div>
            <div className="review-board-controls">
              <button type="button" aria-label="Go to start" onClick={() => { setSelectedPly(0); setShowAlternative(false); }}><RotateCcw size={16} /></button>
              <button type="button" aria-label="Previous move" disabled={selectedPly === 0} onClick={() => { setSelectedPly((ply) => Math.max(0, ply - 1)); setShowAlternative(false); }}><ChevronLeft size={18} /></button>
              <span>{selectedPly} / {review.moves.length} ply</span>
              <button type="button" aria-label="Next move" disabled={selectedPly >= review.moves.length} onClick={() => { setSelectedPly((ply) => Math.min(review.moves.length, ply + 1)); setShowAlternative(false); }}><ChevronRight size={18} /></button>
            </div>
            {selectedMove && <div className={`review-callout review-callout-${selectedMove.quality}`}>
              <strong>{qualityLabels[selectedMove.quality]}</strong>
              <span>{selectedMove.player} · {selectedMove.notation}</span>
              <p>{selectedMove.explanation}</p>
              {selectedMove.suggestion && <em>Try: {selectedMove.suggestion}</em>}
              {selectedMove.alternative && <div className="review-alternative">
                <strong>{isShowingAlternative ? `Alternative position · ${selectedMove.alternative}` : `Alternative to explore: ${selectedMove.alternative}`}</strong>
                <p>{selectedMove.alternative_explanation}</p>
                <button type="button" aria-pressed={isShowingAlternative} onClick={() => setShowAlternative((visible) => !visible)}>
                  {isShowingAlternative ? "Show played position" : "Explore alternative"}
                </button>
              </div>}
            </div>}
          </section>

          <section className="review-moves-panel">
            <div className="review-panel-heading"><div><p className="review-eyebrow">MOVE-BY-MOVE</p><h2>Game timeline</h2></div><span>{review.moves.length} plies</span></div>
            <div className="review-move-list">
              {review.moves.map((move) => <button
                className={`review-move-row ${selectedPly === move.ply ? "review-move-selected" : ""} review-move-${move.quality}`}
                key={move.ply}
                type="button"
                onClick={() => { setSelectedPly(move.ply); setShowAlternative(false); }}
              >
                <span className="review-move-number">{Math.ceil(move.ply / 2)}{move.color === "black" ? "..." : "."}</span>
                <span className="review-move-san">{move.notation}</span>
                <span className="review-move-quality">{qualityLabels[move.quality]}</span>
              </button>)}
            </div>
          </section>
        </div>}

        {review?.training_recommendation && <section className="review-training-recommendation" aria-label="Recommended training">
          <div>
            <p className="review-eyebrow">YOUR NEXT PRACTICE</p>
            <h2>{review.training_recommendation.focus_label}</h2>
            <p>{review.training_recommendation.lesson_title
              ? `${review.training_recommendation.lesson_title} · ${review.training_recommendation.lesson_theme}`
              : review.training_recommendation.message}</p>
            <small>{review.training_recommendation.message}</small>
          </div>
          {review.training_recommendation.lesson_id && <Link to={`/training?lesson=${encodeURIComponent(review.training_recommendation.lesson_id)}`}>
            {review.training_recommendation.available_now ? "Practice this lesson" : "Open training"}
          </Link>}
        </section>}

        {review && <p className="review-disclaimer">{review.scope}</p>}
      </section>
    </main>
  );
}

export default GameReview;
