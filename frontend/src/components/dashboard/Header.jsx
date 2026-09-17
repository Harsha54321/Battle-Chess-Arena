import {
  Bell,
  Settings,
  LogOut
} from "lucide-react";

function Header() {
  const user = JSON.parse(localStorage.getItem("battleChessUser"));

  return (
    <header className="fixed inset-x-0 top-0 z-50 border-b border-cyan-500/10 bg-[#020617]/95 backdrop-blur-2xl py-3 shadow-[0_25px_80px_rgba(0,0,0,0.45)]">
      <div className="mx-auto flex items-center justify-between gap-4 px-6 lg:px-8 max-w-[1600px]">

        <div className="flex flex-wrap items-center gap-4">
          <h1 className="text-4xl font-black uppercase tracking-[0.35em] text-yellow-400 lg:text-5xl">
            BATTLE CHESS ARENA
          </h1>

          <span className="rounded-full border border-cyan-400/25 bg-[#0d2440]/80 px-4 py-1 text-[10px] uppercase tracking-[0.4em] text-cyan-300">
            PREMIUM EDITION
          </span>
        </div>

        <div className="flex items-center gap-3">
          <div className="glass-card gaming-card flex items-center gap-3 rounded-[28px] border border-cyan-500/15 bg-[#06101e]/80 px-4 py-3 shadow-cyanGlow">
            <div className="relative flex h-14 w-14 items-center justify-center rounded-2xl bg-gradient-to-br from-yellow-400 to-yellow-600 text-2xl text-black">
              {user?.avatar}
              <span className="absolute -top-1 -right-1 h-2.5 w-2.5 rounded-full bg-green-400 animate-pulse" />
            </div>

            <div className="min-w-[160px]">
              <p className="text-sm font-semibold text-white">{user?.name || 'ChessMaster'}</p>
              <p className="text-[11px] uppercase tracking-[0.25em] text-cyan-300">LVL 45 · 2450 ELO</p>
            </div>
          </div>

          <button className="grid h-12 w-12 place-items-center rounded-3xl border border-white/10 bg-[#06101e]/70 text-cyan-200 transition hover:bg-cyan-500/10">
            <Bell size={20} />
          </button>

          <button className="grid h-12 w-12 place-items-center rounded-3xl border border-white/10 bg-[#06101e]/70 text-cyan-200 transition hover:bg-cyan-500/10">
            <Settings size={20} />
          </button>

          <button className="grid h-12 w-12 place-items-center rounded-3xl border border-white/10 bg-[#06101e]/70 text-cyan-200 transition hover:bg-red-500/10">
            <LogOut size={20} />
          </button>
        </div>
      </div>
    </header>
  );
}

export default Header;