import QuickMatchCard from "./QuickMatchCard";
import ModeCard from "./ModeCard";
import {
  Bot,
  UsersRound,
  Trophy
} from "lucide-react";

function GameModes() {

  const modes = [
    {
      title: "PLAY VS AI",
      theme:"border-green-500/40",
      description: "Practice & Improve",
      icon: <Bot size={42} />,
      to: "/play-vs-ai",
    },
    {
      title: "MULTIPLAYER",
      theme:"border-orange-500/40",
      description: "Challenge Friends",
      icon: <UsersRound size={42} />,
      to: "/multiplayer",
    },
    {
      title: "TOURNAMENT",
      theme:"border-yellow-500/40",
      description: "Compete for Glory",
      icon: <Trophy size={42} />,
      to: "/tournament",
    },
  ];

  return (
    <div>

      <h2 className="text-2xl text-white mb-6">
        GAME MODES
      </h2>

      <QuickMatchCard />

      <div className="grid md:grid-cols-2 gap-6 mt-6">

        {modes.map((mode) => (
          <ModeCard
            key={mode.title}
            icon={mode.icon}
            title={mode.title}
            theme={mode.theme}
            description={mode.description}
            to={mode.to}
          />
        ))}

      </div>

    </div>
  );
}

export default GameModes;