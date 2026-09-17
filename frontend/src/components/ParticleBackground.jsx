function ParticleBackground() {
  const particles = Array.from({ length: 40 });

  return (
    <div className="absolute inset-0 overflow-hidden">
      {particles.map((_, index) => {
        const size = Math.random() * 4 + 2;
        const left = Math.random() * 100;
        const delay = Math.random() * 5;
        const duration = Math.random() * 10 + 10;

        return (
          <div
            key={index}
            className="absolute rounded-full bg-cyan-400 opacity-30 animate-pulse"
            style={{
              width: `${size}px`,
              height: `${size}px`,
              left: `${left}%`,
              top: `${Math.random() * 100}%`,
              animationDelay: `${delay}s`,
              animationDuration: `${duration}s`,
              boxShadow: "0 0 10px rgba(0,212,255,0.8)",
            }}
          />
        );
      })}
    </div>
  );
}

export default ParticleBackground;