import axios from "axios";

const api = axios.create({
  baseURL: import.meta.env.VITE_API_URL || "http://127.0.0.1:8000/api",
  headers: {
    "Content-Type": "application/json",
  },
});

api.interceptors.request.use((config) => {
  const token = sessionStorage.getItem("battleChessSessionToken");
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401 && sessionStorage.getItem("battleChessSessionToken")) {
      sessionStorage.removeItem("battleChessSessionToken");
      localStorage.removeItem("battleChessUser");
      window.location.assign("/auth");
    }
    return Promise.reject(error);
  }
);

export async function createGuestPlayer(username, avatar) {
  const response = await api.post("/players/guest/", { username, avatar });
  return response.data;
}

export async function logoutSession() {
  const response = await api.post("/auth/logout/");
  return response.data;
}

export function startGoogleSignIn() {
  const apiRoot = api.defaults.baseURL.replace(/\/+$/, "");
  window.location.assign(`${apiRoot}/auth/google/start/`);
}

export async function exchangeGoogleLoginTicket(ticket) {
  const response = await api.post("/auth/google/exchange/", { ticket });
  return response.data;
}

export async function getPlayer(playerId) {
  const response = await api.get(`/players/${playerId}/`);
  return response.data.player;
}

export async function getPlayerProfileSummary(playerId) {
  const response = await api.get(`/players/${playerId}/profile-summary/`);
  return response.data;
}

export async function getLeaderboard(limit = 5) {
  const response = await api.get(`/leaderboard/?limit=${limit}`);
  return response.data.players;
}

export async function getDailyChallenge(playerId) {
  const response = await api.get(`/players/${playerId}/daily-challenge/`);
  return response.data.challenge;
}

export async function claimDailyChallenge(playerId) {
  const response = await api.post(`/players/${playerId}/daily-challenge/claim/`);
  return response.data.challenge;
}

export async function getPlayerTraining(playerId) {
  const response = await api.get(`/players/${playerId}/training/`);
  return response.data;
}

export async function submitTrainingAttempt(playerId, attempt) {
  const response = await api.post(`/players/${playerId}/training/attempt/`, attempt);
  return response.data;
}

export async function getNotifications(playerId) {
  const response = await api.get(`/players/${playerId}/notifications/`);
  return response.data;
}

export async function markNotificationRead(playerId, notificationId) {
  const response = await api.post(`/players/${playerId}/notifications/${notificationId}/read/`);
  return response.data;
}

export async function markAllNotificationsRead(playerId) {
  const response = await api.post(`/players/${playerId}/notifications/read-all/`);
  return response.data;
}

export async function searchPlayers(query) {
  const response = await api.get(`/players/search/?q=${encodeURIComponent(query)}`);
  return response.data.players;
}

export async function addFriend(playerId, friendId) {
  const response = await api.post("/friends/", { player_id: playerId, friend_id: friendId });
  return response.data.friend;
}

export async function challengeFriend(playerId, friendId) {
  const response = await api.post("/friends/challenge/", { player_id: playerId, friend_id: friendId });
  return response.data;
}

export async function respondToChallenge(matchId, playerId, action) {
  const response = await api.post(`/matches/${matchId}/challenge-response/`, { player_id: playerId, action });
  return response.data;
}

export async function respondToFriendRequest(connectionId, playerId, action) {
  const response = await api.post(`/friends/${connectionId}/respond/`, { player_id: playerId, action });
  return response.data;
}

export async function getFriends(playerId) {
  const response = await api.get(`/players/${playerId}/friends/`);
  return response.data.friends;
}

export async function getFriendMessages(playerId, friendId) {
  const response = await api.get(`/players/${playerId}/friends/${friendId}/messages/`);
  return response.data.messages;
}

export async function sendFriendMessage(playerId, friendId, message) {
  const response = await api.post(`/players/${playerId}/friends/${friendId}/messages/`, { message });
  return response.data.message;
}

export async function createMatch(playerId, mode = "quick_match", difficulty = "beginner") {
  const response = await api.post("/matches/", {
    player_id: playerId,
    mode,
    ...(mode === "ai" ? { difficulty } : {}),
  });
  return response.data.match;
}

export async function cancelMatchmaking(matchId) {
  const response = await api.post("/matches/cancel-queue/", { match_id: matchId });
  return response.data;
}

export async function getMatch(matchId) {
  const response = await api.get(`/matches/${matchId}/`);
  return response.data.match;
}

export async function getMatchReview(matchId) {
  const response = await api.get(`/matches/${matchId}/review/`);
  return response.data.review;
}

export async function getMatchMessages(matchId) {
  const response = await api.get(`/matches/${matchId}/messages/`);
  return response.data.messages;
}

export async function sendMatchMessage(matchId, message) {
  const response = await api.post(`/matches/${matchId}/messages/`, { message });
  return response.data.message;
}

export function connectToMatch(matchId, onMessage, onStateChange) {
  const token = sessionStorage.getItem("battleChessSessionToken");
  if (!token) return null;

  const apiUrl = new URL(api.defaults.baseURL);
  const socketProtocol = apiUrl.protocol === "https:" ? "wss:" : "ws:";
  const socketUrl = `${socketProtocol}//${apiUrl.host}/ws/matches/${matchId}/`;
  const socket = new WebSocket(socketUrl, ["battle-chess.v1", `auth.${token}`]);
  socket.addEventListener("open", () => onStateChange(true));
  socket.addEventListener("close", () => onStateChange(false));
  socket.addEventListener("error", () => onStateChange(false));
  socket.addEventListener("message", (event) => {
    try {
      onMessage(JSON.parse(event.data));
    } catch {
      onStateChange(false);
    }
  });
  return socket;
}

export async function recordMove(matchId, move) {
  const response = await api.post(`/matches/${matchId}/moves/`, move);
  return response.data;
}

export async function surrenderMatch(matchId, playerId) {
  const response = await api.post(`/matches/${matchId}/surrender/`, { player_id: playerId });
  return response.data.match;
}

export async function claimMatchDraw(matchId) {
  const response = await api.post(`/matches/${matchId}/claim-draw/`);
  return response.data.match;
}

export async function completeMatch(matchId, playerId, result) {
  const response = await api.post(`/matches/${matchId}/complete/`, { player_id: playerId, result });
  return response.data.match;
}

export default api;
