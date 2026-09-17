
import { Link } from "react-router-dom";

function DailyChallenge() {
  return (
    <div className="glass-card gaming-card rounded-3xl p-6">

      <div className="flex justify-between items-center">

        <h3 className="text-white font-bold text-xl">
          DAILY CHALLENGE
        </h3>

        <span className="bg-yellow-400 text-black px-3 py-1 rounded-full text-xs font-bold">
          500 COINS
        </span>

      </div>

      <div className="mt-6">

        <div className="flex justify-between mb-2">

          <span className="text-gray-400">
            Progress
          </span>

          <span className="text-yellow-400">
            2/3
          </span>

        </div>

        <div className="w-full bg-black rounded-full h-3">

          <div className="bg-yellow-400 h-3 rounded-full w-2/3" />

        </div>

      </div>

      <p className="mt-6 text-gray-300 leading-relaxed">
        Win 3 ranked matches today to claim your daily reward.
      </p>

      <Link to="/game" className="block w-full mt-6 py-4 rounded-2xl bg-yellow-400 text-center text-black font-bold">
        PLAY NOW
      </Link>

    </div>
  );
}

export default DailyChallenge;