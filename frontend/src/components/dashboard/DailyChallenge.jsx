
import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { getDailyChallenge } from "../../services/api";

function DailyChallenge() {
  const [challenge, setChallenge] = useState({ progress: 0, target: 3, reward_coins: 500 });
  const [error, setError] = useState("");
  const playerId = (() => {
    try {
      return JSON.parse(localStorage.getItem("battleChessUser") || "null")?.id;
    } catch {
      return null;
    }
  })();

  useEffect(() => {
    if (playerId) {
      getDailyChallenge(playerId).then(setChallenge).catch(() => {
        setError("Daily challenge could not be loaded.");
      });
    }
  }, [playerId]);

  const progressPercent = Math.min((challenge.progress / challenge.target) * 100, 100);

  return (
    <div className="glass-card gaming-card rounded-3xl p-6">

      <div className="flex justify-between items-center">

        <h3 className="text-white font-bold text-xl">
          DAILY CHALLENGE
        </h3>

        <span className="bg-yellow-400 text-black px-3 py-1 rounded-full text-xs font-bold">
          {challenge.reward_coins} COINS
        </span>

      </div>

      <div className="mt-6">

        <div className="flex justify-between mb-2">

          <span className="text-gray-400">
            Progress
          </span>

          <span className="text-yellow-400">
            {challenge.progress}/{challenge.target}
          </span>

        </div>

        <div className="w-full bg-black rounded-full h-3">

          <div className="bg-yellow-400 h-3 rounded-full" style={{ width: `${progressPercent}%` }} />

        </div>

      </div>

      <p className="mt-6 text-gray-300 leading-relaxed">
        Win {challenge.target} quick matches today to claim your daily reward.
      </p>
      {error && <p className="mt-3 text-sm text-red-300" role="alert">{error}</p>}

      <Link to="/game" className="block w-full mt-6 py-4 rounded-2xl bg-yellow-400 text-center text-black font-bold">
        PLAY NOW
      </Link>

    </div>
  );
}

export default DailyChallenge;