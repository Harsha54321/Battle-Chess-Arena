import { ArrowRight, Crown } from "lucide-react";

function QuickMatchCard() {
  return (
    <div className="glass-card gaming-card rounded-[36px] p-8 min-h-[220px] bg-[rgba(10,22,35,0.76)] border border-cyan-400/15 shadow-[0_0_40px_rgba(0,212,255,0.08)]">

      <div className="flex flex-col justify-between gap-8 lg:flex-row lg:items-center">

        <div className="flex items-center gap-5 rounded-3xl bg-cyan-500/10 p-5">
          <div className="flex h-20 w-20 items-center justify-center rounded-3xl bg-cyan-500/20 text-cyan-300">
            <Crown size={36} />
          </div>
          <div>
            <p className="text-xs uppercase tracking-[0.3em] text-cyan-300/70">
              Quick Match
            </p>
            <h3 className="text-4xl font-bold text-white">
              Instant competitive play
            </h3>
          </div>
        </div>

        <div className="flex flex-col gap-4 lg:items-end">
          <div className="flex flex-wrap gap-3">
            <span className="rounded-full bg-green-500/15 px-4 py-2 text-sm text-green-300">
              1,247 ONLINE
            </span>
            <span className="rounded-full bg-yellow-500/15 px-4 py-2 text-sm text-yellow-300">
              AVG 2:30 WAIT
            </span>
          </div>

          <button className="inline-flex items-center gap-3 rounded-3xl bg-yellow-400 px-6 py-3 text-sm font-semibold text-black transition hover:shadow-goldGlow">
            Play Now
            <ArrowRight size={18} />
          </button>
        </div>

      </div>

    </div>
  );
}

export default QuickMatchCard;