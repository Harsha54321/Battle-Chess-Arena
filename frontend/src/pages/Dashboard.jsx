import ParticleBackground from "../components/ParticleBackground";
import GlowBackground from "../components/GlowBackground";

import Header from "../components/dashboard/Header";
import GameModes from "../components/dashboard/GameModes";
import DailyChallenge from "../components/dashboard/DailyChallenge";
import Leaderboard from "../components/dashboard/Leaderboard";
import QuickAccess from "../components/dashboard/QuickAccess";

function Dashboard() {
  return (
    <div className="relative min-h-screen overflow-x-hidden bg-gaming-darker text-white font-gaming">

      <ParticleBackground />
      <div className="fixed inset-0 pointer-events-none">

        <div
          className="absolute top-20 left-20 w-96 h-96 bg-cyan-500/10 blur-[150px] rounded-full animate-pulse"
        />

        <div
          className="absolute bottom-20 right-20 w-[500px] h-[500px] bg-yellow-400/10 blur-[180px] rounded-full animate-pulse"
        />

      </div>
      <GlowBackground />

      <Header />

      <div className="relative z-10 mx-auto mt-24 max-w-[1600px] px-6 pb-12 lg:px-8">

        <div className="grid gap-8 lg:grid-cols-[3fr_1fr] pt-8">

          <GameModes />

          <div className="space-y-6">
            <DailyChallenge />
            <Leaderboard />
          </div>

        </div>

        <QuickAccess />

      </div>

    </div>
  );
}

export default Dashboard;