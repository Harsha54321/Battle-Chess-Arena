export const DEFAULT_GAME_SETTINGS = {
  backgroundMusicEnabled: false,
  soundEffectsEnabled: true,
  confirmBeforeResigning: true,
  showCoordinates: true,
  musicVolume: 30,
};

const SETTINGS_STORAGE_KEY = "battleChessSettings";
const SETTINGS_EVENT = "battle-chess-settings-changed";

export function getGameSettings() {
  const storedSettings = localStorage.getItem(SETTINGS_STORAGE_KEY);
  if (!storedSettings) return { ...DEFAULT_GAME_SETTINGS };

  let parsedSettings;
  try {
    parsedSettings = JSON.parse(storedSettings);
  } catch (error) {
    if (error instanceof SyntaxError) return { ...DEFAULT_GAME_SETTINGS };
    throw error;
  }

  if (!parsedSettings || typeof parsedSettings !== "object" || Array.isArray(parsedSettings)) {
    return { ...DEFAULT_GAME_SETTINGS };
  }

  return {
    backgroundMusicEnabled: typeof parsedSettings.backgroundMusicEnabled === "boolean"
      ? parsedSettings.backgroundMusicEnabled
      : DEFAULT_GAME_SETTINGS.backgroundMusicEnabled,
    soundEffectsEnabled: typeof parsedSettings.soundEffectsEnabled === "boolean"
      ? parsedSettings.soundEffectsEnabled
      : DEFAULT_GAME_SETTINGS.soundEffectsEnabled,
    confirmBeforeResigning: typeof parsedSettings.confirmBeforeResigning === "boolean"
      ? parsedSettings.confirmBeforeResigning
      : DEFAULT_GAME_SETTINGS.confirmBeforeResigning,
    showCoordinates: typeof parsedSettings.showCoordinates === "boolean"
      ? parsedSettings.showCoordinates
      : DEFAULT_GAME_SETTINGS.showCoordinates,
    musicVolume: Number.isFinite(parsedSettings.musicVolume)
      ? Math.min(100, Math.max(0, parsedSettings.musicVolume))
      : DEFAULT_GAME_SETTINGS.musicVolume,
  };
}

export function saveGameSettings(updates) {
  const settings = { ...getGameSettings(), ...updates };
  localStorage.setItem(SETTINGS_STORAGE_KEY, JSON.stringify(settings));
  window.dispatchEvent(new CustomEvent(SETTINGS_EVENT, { detail: settings }));
  return settings;
}

export function subscribeToGameSettings(onChange) {
  const handleChange = (event) => onChange(event.detail);
  window.addEventListener(SETTINGS_EVENT, handleChange);
  return () => window.removeEventListener(SETTINGS_EVENT, handleChange);
}
