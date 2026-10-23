import { useEffect, useState } from "react";
import {
  Bell,
  Settings,
  LogOut
} from "lucide-react";
import { Link, useNavigate } from "react-router-dom";
import { getNotifications, getPlayer, logoutSession } from "../../services/api";

function Header() {
  const navigate = useNavigate();
  const [user, setUser] = useState(() => (() => {
    try {
      return JSON.parse(localStorage.getItem("battleChessUser") || "null");
    } catch {
      return null;
    }
  })());
  const [unreadNotifications, setUnreadNotifications] = useState(0);
  const [notificationError, setNotificationError] = useState("");
  const [logoutError, setLogoutError] = useState("");

  const playerId = user?.id;

  useEffect(() => {
    if (!playerId) return;
    getPlayer(playerId).then((player) => {
      setUser((currentUser) => {
        const nextUser = {
          ...currentUser,
          name: player.username,
          avatar: player.avatar,
          level: player.level,
          rating: player.rating,
          coins: player.coins,
        };
        localStorage.setItem("battleChessUser", JSON.stringify(nextUser));
        return nextUser;
      });
    }).catch(() => {});
  }, [playerId]);

  useEffect(() => {
    if (!playerId) return undefined;
    let isCurrent = true;
    const handleUnreadCount = (event) => setUnreadNotifications(event.detail);
    window.addEventListener("notifications:unread-count", handleUnreadCount);
    async function refreshUnreadCount() {
      try {
        const data = await getNotifications(playerId);
        if (isCurrent) {
          setUnreadNotifications(data.unread_count);
          setNotificationError("");
        }
      } catch {
        if (isCurrent) setNotificationError("Notification count could not be refreshed.");
      }
    }
    refreshUnreadCount();
    const interval = window.setInterval(refreshUnreadCount, 30_000);
    return () => {
      isCurrent = false;
      window.clearInterval(interval);
      window.removeEventListener("notifications:unread-count", handleUnreadCount);
    };
  }, [playerId]);

  async function handleLogout() {
    setLogoutError("");
    try {
      await logoutSession();
      sessionStorage.removeItem("battleChessSessionToken");
      localStorage.removeItem("battleChessUser");
      navigate("/auth");
    } catch {
      setLogoutError("Could not securely sign out. Check your connection and try again.");
    }
  }

  return (
    <header className="fixed inset-x-0 top-0 z-50 border-b border-cyan-500/10 bg-[#020617]/95 backdrop-blur-2xl py-3 shadow-[0_25px_80px_rgba(0,0,0,0.45)]">
      <div className="mx-auto flex items-center justify-between gap-4 px-6 lg:px-8 max-w-[1600px]">

        <div className="flex flex-wrap items-center gap-4">
          <h1 className="text-4xl font-black uppercase tracking-[0.35em] text-yellow-400 lg:text-4xl">
            BATTLE CHESS ARENA
          </h1>

          <span className="rounded-full border border-cyan-400/25 bg-[#0d2440]/80 px-4 py-1 text-[10px] uppercase tracking-[0.4em] text-cyan-300">
            PREMIUM EDITION
          </span>
        </div>

        <div className="flex items-center gap-3">
          <Link to="/profile" aria-label="Open profile" className="glass-card gaming-card flex items-center gap-3 rounded-[28px] border border-cyan-500/15 bg-[#06101e]/80 px-4 py-3 shadow-cyanGlow">
            <div className="relative flex h-14 w-14 items-center justify-center rounded-2xl bg-gradient-to-br from-yellow-400 to-yellow-600 text-2xl text-black">
              {user?.avatar}
            </div>

            <div className="min-w-[160px]">
              <p className="text-sm font-semibold text-white">{user?.name || 'ChessMaster'}</p>
              <p className="text-[11px] uppercase tracking-[0.25em] text-cyan-300">LVL {user?.level || 45} · {(user?.rating || 2450).toLocaleString()} ELO</p>
            </div>
          </Link>

          <Link to="/notifications" aria-label={`Notifications${unreadNotifications ? `, ${unreadNotifications} unread` : ""}`} className="relative grid h-12 w-12 place-items-center rounded-3xl border border-white/10 bg-[#06101e]/70 text-cyan-200 transition hover:bg-cyan-500/10">
            <Bell size={20} />
            {unreadNotifications > 0 && <span className="absolute -right-1 -top-1 grid h-5 min-w-5 place-items-center rounded-full bg-red-500 px-1 text-[10px] font-bold text-white">{unreadNotifications > 99 ? "99+" : unreadNotifications}</span>}
          </Link>

          <Link to="/settings" aria-label="Settings" className="grid h-12 w-12 place-items-center rounded-3xl border border-white/10 bg-[#06101e]/70 text-cyan-200 transition hover:bg-cyan-500/10">
            <Settings size={20} />
          </Link>

          <button type="button" aria-label="Log out" onClick={handleLogout} className="grid h-12 w-12 place-items-center rounded-3xl border border-white/10 bg-[#06101e]/70 text-cyan-200 transition hover:bg-red-500/10">
            <LogOut size={20} />
          </button>
        </div>
      </div>
      {notificationError && <p className="mx-auto mt-2 max-w-[1600px] px-6 text-right text-xs text-red-300" role="status">{notificationError}</p>}
      {logoutError && <p className="mx-auto mt-2 max-w-[1600px] px-6 text-right text-sm text-red-300" role="alert">{logoutError}</p>}
    </header>
  );
}

export default Header;