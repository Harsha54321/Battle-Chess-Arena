import { Link } from "react-router-dom";

function Leaderboard() {

  const players = [
    { rank: 1, name: "Player1", elo: 2450 },
    { rank: 2, name: "Player2", elo: 2400 },
    { rank: 3, name: "Player3", elo: 2350 },
    { rank: 4, name: "Player4", elo: 2300 },
    { rank: 5, name: "Player5", elo: 2250 },
  ];

  return (
    <div className="glass-card gaming-card rounded-3xl p-6 mt-6">

      <div className="flex justify-between">

        <h3 className="text-xl font-bold text-white">
          LEADERBOARD
        </h3>

        <span className="text-gray-400 text-sm">
          GLOBAL
        </span>

      </div>

      <div className="mt-6 space-y-4">

        {players.map((player) => (

          <div
            key={player.rank}
            className="flex items-center justify-between bg-white/5 rounded-xl p-4"
          >

            <div className="flex items-center gap-4">

              <div className="w-10 h-10 rounded-xl bg-yellow-400 text-black flex items-center justify-center font-bold">
                {player.rank}
              </div>

              <div>

                <h4 className="text-white">
                  {player.name}
                </h4>

                <p className="text-gray-400 text-sm">
                  {player.elo} ELO
                </p>

              </div>

            </div>

          </div>

        ))}

      </div>

      <Link to="/rankings" className="block w-full mt-6 py-3 rounded-xl bg-cyan-500/20 text-center text-cyan-400">
        VIEW FULL RANKINGS
      </Link>

    </div>
  );
}

export default Leaderboard;