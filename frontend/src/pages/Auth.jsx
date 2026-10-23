import { useState } from "react";
import { motion } from "framer-motion";
import { FcGoogle } from "react-icons/fc";
import { FaChessKnight } from "react-icons/fa";

import ParticleBackground from "../components/ParticleBackground";
import GlowBackground from "../components/GlowBackground";
import { useNavigate } from "react-router-dom";
import { startGoogleSignIn } from "../services/api";

function Auth() {
    const navigate = useNavigate();
    const [googleError, setGoogleError] = useState("");

    const handleGoogleSignIn = () => {
        setGoogleError("");
        startGoogleSignIn();
    };

    return (
        <div className="relative flex min-h-screen items-center justify-center overflow-hidden bg-gaming-darker">

            <ParticleBackground />
            <GlowBackground />

            <motion.div
                initial={{ opacity: 0, scale: 0.9, y: 40 }}
                animate={{ opacity: 1, scale: 1, y: 0 }}
                transition={{ duration: 0.7 }}
                className="glass-card relative z-10 w-[min(420px,calc(100%-32px))] rounded-[32px] p-6 sm:p-10"
            >

                <div className="mb-10 text-center">

                    <h1 className="gaming-heading text-metallic-gold text-5xl">
                        BATTLE
                    </h1>

                    <h2 className="gaming-subheading text-metallic-blue mt-2 text-3xl">
                        CHESS ARENA
                    </h2>

                    <p className="mt-5 text-sm text-slate-400">
                        Enter the futuristic chess battleground
                    </p>

                </div>

                <div className="flex flex-col gap-5">

                    <button
                        onClick={() => navigate("/guest-setup")}
                        className="group flex items-center justify-center gap-3 rounded-2xl border border-cyan-400/20 bg-cyan-400/10 px-6 py-4 text-lg text-cyan-300 transition-all duration-300 hover:scale-[1.03] hover:border-cyan-400 hover:bg-cyan-400/20 hover:shadow-cyanGlow"
                    >

                        <FaChessKnight className="text-2xl" />

                        <span>Play as Guest</span>

                    </button>

                    <button onClick={handleGoogleSignIn} className="group flex items-center justify-center gap-3 rounded-2xl border border-white/10 bg-white/5 px-6 py-4 text-lg text-white transition-all duration-300 hover:scale-[1.03] hover:bg-white/10 hover:shadow-goldGlow">

                        <FcGoogle className="text-2xl" />

                        <span>Continue with Google</span>

                    </button>

                    {googleError && (
                        <p role="alert" className="text-center text-sm text-red-400">
                            {googleError}
                        </p>
                    )}

                </div>

            </motion.div>
        </div>
    );
}

export default Auth;