import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { motion } from "framer-motion";

import ParticleBackground from "../components/ParticleBackground";
import GlowBackground from "../components/GlowBackground";

function Loading() {
  const [progress, setProgress] = useState(0);

  const navigate = useNavigate();

  useEffect(() => {
    const interval = setInterval(() => {
      setProgress((prev) => {
        if (prev >= 100) {
          clearInterval(interval);

          setTimeout(() => {
            navigate("/auth");
          }, 500);

          return 100;
        }

        return prev + 2;
      });
    }, 50);

    return () => clearInterval(interval);
  }, [navigate]);

  return (
    <div className="relative flex min-h-screen items-center justify-center overflow-hidden bg-gaming-darker">

      <ParticleBackground />
      <GlowBackground />

      <div className="relative z-10 flex flex-col items-center gap-10">

        <motion.div
          initial={{ opacity: 0, y: -80 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 1 }}
          className="text-center"
        >
          <h1 className="gaming-heading text-metallic-gold text-7xl md:text-8xl">
            BATTLE CHESS
          </h1>

          <h2 className="gaming-subheading text-metallic-blue mt-3 text-4xl md:text-5xl">
            ARENA
          </h2>
        </motion.div>

        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 0.5 }}
          className="w-[380px]"
        >
          <div className="glass-card rounded-full p-2">

            <div
              className="h-3 rounded-full bg-gradient-to-r from-cyan-400 to-yellow-400 transition-all duration-300"
              style={{ width: `${progress}%` }}
            />
          </div>

          <p className="mt-4 text-center text-cyan-400">
            Loading... {progress}%
          </p>
        </motion.div>

      </div>
    </div>
  );
}

export default Loading;