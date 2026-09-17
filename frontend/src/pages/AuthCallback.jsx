import { Link, useSearchParams } from "react-router-dom";

function AuthCallback() {
  const [searchParams] = useSearchParams();
  const error = searchParams.get("error");
  const hasCode = Boolean(searchParams.get("code"));

  return (
    <main className="relative flex min-h-screen items-center justify-center overflow-hidden bg-gaming-darker px-4 text-center">
      <section className="glass-card relative z-10 w-full max-w-md rounded-[32px] p-8 sm:p-10">
        <p className="text-xs uppercase tracking-[0.3em] text-cyan-300">Google authentication</p>
        <h1 className="mt-4 text-2xl font-bold text-white">
          {error ? "Authentication cancelled" : hasCode ? "Google account received" : "Invalid authentication response"}
        </h1>
        <p className="mt-4 text-sm leading-6 text-slate-400">
          {error ? "You can return to the sign-in screen and try again." : "Secure account verification will be connected when the backend authentication service is added."}
        </p>
        <Link to="/auth" className="mt-8 inline-flex rounded-2xl bg-cyan-400 px-6 py-3 font-semibold text-black transition hover:bg-cyan-300">
          Return to sign in
        </Link>
      </section>
    </main>
  );
}

export default AuthCallback;