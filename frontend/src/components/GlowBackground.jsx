function GlowBackground() {
  return (
    <div className="absolute inset-0 overflow-hidden">

      <div className="absolute left-[10%] top-[15%] h-[300px] w-[300px] rounded-full bg-cyan-500/20 blur-[120px]" />

      <div className="absolute right-[10%] top-[20%] h-[350px] w-[350px] rounded-full bg-yellow-400/10 blur-[140px]" />

      <div className="absolute bottom-[10%] left-[35%] h-[400px] w-[400px] rounded-full bg-blue-600/10 blur-[160px]" />

    </div>
  );
}

export default GlowBackground;