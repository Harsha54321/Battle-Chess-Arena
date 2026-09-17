import axios from "axios";

const api = axios.create({
  baseURL: import.meta.env.VITE_API_URL || "http://127.0.0.1:8000/api",
  headers: {
    "Content-Type": "application/json",
  },
});

export async function createGuestPlayer(username, avatar) {
  const response = await api.post("/players/guest/", { username, avatar });
  return response.data.player;
}

export async function createMatch(playerId, mode = "quick_match") {
  const response = await api.post("/matches/", { player_id: playerId, mode });
  return response.data.match;
}

export async function getMatch(matchId) {
  const response = await api.get(`/matches/${matchId}/`);
  return response.data.match;
}

export default api;
