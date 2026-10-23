let audioContext;
let musicGain;
let musicTimer;
let chordIndex = 0;
const musicVoices = new Set();
const chordProgression = [
  [130.81, 196, 261.63, 329.63],
  [110, 164.81, 220, 261.63],
  [87.31, 130.81, 174.61, 220],
  [98, 146.83, 196, 246.94],
];

function getAudioContext() {
  const AudioContextType = window.AudioContext || window.webkitAudioContext;
  if (!AudioContextType) throw new Error("Audio playback is not supported in this browser.");
  audioContext ||= new AudioContextType();
  return audioContext;
}

function playNextChord() {
  const context = getAudioContext();
  const now = context.currentTime;
  const chord = chordProgression[chordIndex % chordProgression.length];
  chordIndex += 1;

  chord.forEach((frequency, index) => {
    const oscillator = context.createOscillator();
    const voiceGain = context.createGain();
    oscillator.type = index === 0 ? "sine" : "triangle";
    oscillator.frequency.value = frequency;
    voiceGain.gain.setValueAtTime(0, now);
    voiceGain.gain.linearRampToValueAtTime(index === 0 ? 0.22 : 0.11, now + 1.1);
    voiceGain.gain.setValueAtTime(index === 0 ? 0.22 : 0.11, now + 4.2);
    voiceGain.gain.linearRampToValueAtTime(0, now + 5.2);
    oscillator.connect(voiceGain);
    voiceGain.connect(musicGain);
    oscillator.onended = () => {
      musicVoices.delete(oscillator);
      oscillator.disconnect();
      voiceGain.disconnect();
    };
    musicVoices.add(oscillator);
    oscillator.start(now);
    oscillator.stop(now + 5.25);
  });
}

export async function startBackgroundMusic(volume) {
  const context = getAudioContext();
  if (context.state === "suspended") await context.resume();
  if (musicTimer) {
    setBackgroundMusicVolume(volume);
    return;
  }

  musicGain = context.createGain();
  musicGain.gain.value = (volume / 100) * 0.3;
  musicGain.connect(context.destination);
  playNextChord();
  musicTimer = window.setInterval(playNextChord, 5000);
}

export function setBackgroundMusicVolume(volume) {
  if (!musicGain || !audioContext) return;
  musicGain.gain.setTargetAtTime((volume / 100) * 0.3, audioContext.currentTime, 0.08);
}

export function stopBackgroundMusic() {
  if (musicTimer) {
    window.clearInterval(musicTimer);
    musicTimer = undefined;
  }
  for (const oscillator of musicVoices) oscillator.stop();
  musicVoices.clear();
  musicGain?.disconnect();
  musicGain = undefined;
}

export async function playMoveSound() {
  const context = getAudioContext();
  if (context.state === "suspended") await context.resume();

  const oscillator = context.createOscillator();
  const gain = context.createGain();
  const now = context.currentTime;
  oscillator.type = "sine";
  oscillator.frequency.setValueAtTime(540, now);
  oscillator.frequency.exponentialRampToValueAtTime(390, now + 0.11);
  gain.gain.setValueAtTime(0.045, now);
  gain.gain.exponentialRampToValueAtTime(0.001, now + 0.12);
  oscillator.connect(gain);
  gain.connect(context.destination);
  oscillator.onended = () => {
    oscillator.disconnect();
    gain.disconnect();
  };
  oscillator.start(now);
  oscillator.stop(now + 0.13);
}
