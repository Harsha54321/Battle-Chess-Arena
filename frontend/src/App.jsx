import { BrowserRouter, Routes, Route } from "react-router-dom";

import Loading from "./pages/Loading";
import Auth from "./pages/Auth";
import AuthCallback from "./pages/AuthCallback";
import Dashboard from "./pages/Dashboard";
import Game from "./pages/Game";
import GuestSetup from "./pages/GuestSetup";
import AppPage from "./pages/AppPage";

function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<Loading />} />
        <Route path="/auth" element={<Auth />} />
        <Route path="/auth/callback" element={<AuthCallback />} />
        <Route path="/guest-setup" element={<GuestSetup />} />
        <Route path="/dashboard" element={<Dashboard />} />
        <Route path="/game" element={<Game />} />
        <Route path="/profile" element={<AppPage type="profile" />} />
        <Route path="/notifications" element={<AppPage type="notifications" />} />
        <Route path="/settings" element={<AppPage type="settings" />} />
        <Route path="/rankings" element={<AppPage type="rankings" />} />
        <Route path="/shop" element={<AppPage type="shop" />} />
        <Route path="/daily-rewards" element={<AppPage type="rewards" />} />
        <Route path="/friends" element={<AppPage type="friends" />} />
        <Route path="/play-vs-ai" element={<AppPage type="ai" />} />
        <Route path="/multiplayer" element={<AppPage type="multiplayer" />} />
        <Route path="/tournament" element={<AppPage type="tournament" />} />
      </Routes>
    </BrowserRouter>
  );
}

export default App;