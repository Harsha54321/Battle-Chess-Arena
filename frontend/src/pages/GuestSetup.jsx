import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { motion } from "framer-motion";

import ParticleBackground from "../components/ParticleBackground";
import GlowBackground from "../components/GlowBackground";

import { avatars } from "../data/avatars";
import { createGuestPlayer } from "../services/api";

function GuestSetup() {
    const navigate = useNavigate();

    const [name, setName] = useState("");
    const [selectedAvatar, setSelectedAvatar] = useState("♔");
    const [error, setError] = useState("");
    const [isSubmitting, setIsSubmitting] = useState(false);

    const handleContinue = async () => {

        if (!name.trim()) {
            setError("Player name is required");
            return;
        }

        setError("");
        setIsSubmitting(true);

        try {
            const player = await createGuestPlayer(name.trim(), selectedAvatar);
            localStorage.setItem(
                "battleChessUser",
                JSON.stringify({
                    id: player.id,
                    name: player.username,
                    avatar: player.avatar,
                    rating: player.rating,
                    level: player.level,
                    coins: player.coins,
                })
            );
            navigate("/dashboard");
        } catch (requestError) {
            setError(requestError.response?.data?.error || "Unable to create your profile. Start the backend and try again.");
        } finally {
            setIsSubmitting(false);
        }
    };

    return (
        <div className="relative flex min-h-screen items-center justify-center overflow-hidden bg-gaming-darker">

            <ParticleBackground />
            <GlowBackground />

            <motion.div
                initial={{ opacity: 0, y: 60 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.7 }}
                className="glass-card relative z-10 w-[min(520px,calc(100%-32px))] rounded-[32px] p-6 sm:p-10"
            >

                <div className="mb-10 text-center">

                    <h1 className="gaming-heading text-metallic-gold text-5xl">
                        CREATE PROFILE
                    </h1>

                    <p className="mt-4 text-slate-400">
                        Choose your battle identity
                    </p>

                </div>

                <div className="mb-8">

                    <label className="mb-3 block text-sm text-cyan-400">
                        PLAYER NAME
                    </label>

                    <input
                        type="text"
                        placeholder="Enter your gamer name"
                        value={name}
                        onChange={(e) => {
                            setName(e.target.value);

                            if (error) {
                                setError("");
                            }
                        }}
                        className={`w-full rounded-2xl border bg-slate-900/60 px-5 py-4 text-white outline-none transition-all

${error
                                ? "border-red-500 shadow-[0_0_20px_rgba(239,68,68,0.4)]"
                                : "border-cyan-400/20 focus:border-cyan-400 focus:shadow-cyanGlow"
                            }
`}
                    />
                    {error && (
                        <p className="mt-3 text-sm text-red-400">
                            {error}
                        </p>
                    )}

                </div>

                <div>

                    <label className="mb-4 block text-sm text-cyan-400">
                        SELECT AVATAR
                    </label>

                    <div className="grid grid-cols-3 gap-5">

                        {avatars.map((avatar) => (

                            <button
                                key={avatar}
                                onClick={() => setSelectedAvatar(avatar)}
                                className={`flex h-24 items-center justify-center rounded-2xl border text-5xl transition-all duration-300
                  
                  ${selectedAvatar === avatar
                                        ? "border-cyan-400 bg-cyan-400/20 shadow-cyanGlow scale-105"
                                        : "border-white/10 bg-white/5 hover:border-cyan-400/40 hover:bg-cyan-400/10"
                                    }
                `}
                            >
                                {avatar}
                            </button>

                        ))}

                    </div>

                </div>

                <button
                    onClick={handleContinue}
                    disabled={isSubmitting}
                    className="mt-10 w-full rounded-2xl bg-gradient-to-r from-cyan-400 to-blue-500 py-4 text-lg font-bold text-black transition-all duration-300 hover:scale-[1.02] hover:shadow-cyanGlow"
                >
                    {isSubmitting ? "CREATING PROFILE..." : "ENTER ARENA"}
                </button>

            </motion.div>
        </div>
    );
}

export default GuestSetup;