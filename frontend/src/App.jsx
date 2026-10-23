import { BrowserRouter, Navigate, Outlet, Route, Routes } from "react-router-dom";

import Loading from "./pages/Loading";
import Auth from "./pages/Auth";
import AuthCallback from "./pages/AuthCallback";
import Dashboard from "./pages/Dashboard";
import Game from "./pages/Game";
import GuestSetup from "./pages/GuestSetup";
import AppPage from "./pages/AppPage";
import ChatPage from "./pages/ChatPage";
import GameReview from "./pages/GameReview";
import AdminPage from "./pages/AdminPage";

function AuthenticatedRoutes() {
  const hasSession = Boolean(
    sessionStorage.getItem("battleChessSessionToken") &&
    localStorage.getItem("battleChessUser")
  );

  return hasSession ? <Outlet /> : <Navigate to="/auth" replace />;
}

function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<Loading />} />
        <Route path="/auth" element={<Auth />} />
        <Route path="/auth/callback" element={<AuthCallback />} />
        <Route path="/Admin" element={<AdminPage />} />
        <Route path="/guest-setup" element={<GuestSetup />} />
        <Route element={<AuthenticatedRoutes />}>
          <Route path="/dashboard" element={<Dashboard />} />
          <Route path="/game" element={<Game />} />
          <Route path="/review/:matchId" element={<GameReview />} />
          <Route path="/profile" element={<AppPage type="profile" />} />
          <Route path="/notifications" element={<AppPage type="notifications" />} />
          <Route path="/settings" element={<AppPage type="settings" />} />
          <Route path="/rankings" element={<AppPage type="rankings" />} />
          <Route path="/shop" element={<AppPage type="shop" />} />
          <Route path="/daily-rewards" element={<AppPage type="rewards" />} />
          <Route path="/training" element={<AppPage type="training" />} />
          <Route path="/friends" element={<AppPage type="friends" />} />
          <Route path="/chat/:friendId" element={<ChatPage />} />
          <Route path="/play-vs-ai" element={<AppPage type="ai" />} />
          <Route path="/multiplayer" element={<AppPage type="multiplayer" />} />
          <Route path="/tournament" element={<AppPage type="tournament" />} />
        </Route>
      </Routes>
    </BrowserRouter>
  );
}

export default App;