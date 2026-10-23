import { useEffect, useRef, useState } from "react";
import { Link, useNavigate, useSearchParams } from "react-router-dom";
import { exchangeGoogleLoginTicket } from "../services/api";

const callbackErrors = {
  google_not_configured: "Google sign-in is not configured on the server yet.",
  google_sign_in_cancelled: "Google sign-in was cancelled.",
  invalid_oauth_state: "The sign-in request could not be verified. Please try again.",
  missing_authorization_code: "Google did not return an authorization code.",
  google_token_exchange_failed: "Google rejected the login code. Check that the Client ID and newly rotated Client Secret in backend/.env belong to the same OAuth client, then restart the backend.",
  google_id_token_rejected: "Google rejected the ID token. In Google Cloud, check that the client is enabled and the authorized redirect URI exactly matches the backend callback URL.",
  google_provider_unavailable: "The backend could not reach Google to verify sign-in. Check your internet connection and retry.",
  google_verification_failed: "Google could not verify this sign-in. Please try again.",
};

function AuthCallback() {
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const hasStarted = useRef(false);
  const errorCode = searchParams.get("error");
  const [ticket] = useState(() => new URLSearchParams(window.location.hash.slice(1)).get("ticket"));
  const [failureMessage, setFailureMessage] = useState("");
  const isError = Boolean(errorCode || failureMessage || (!ticket && !errorCode));
  const message = failureMessage
    || (errorCode && (callbackErrors[errorCode] || "Google sign-in could not be completed."))
    || (ticket ? "Verifying your Google account..." : "The sign-in ticket is missing or invalid. Please try again.");

  useEffect(() => {
    if (hasStarted.current) return;
    hasStarted.current = true;

    if (errorCode) {
      return;
    }

    window.history.replaceState(null, "", window.location.pathname);
    if (!ticket) {
      return;
    }

    exchangeGoogleLoginTicket(ticket)
      .then(({ player, session_token: sessionToken }) => {
        sessionStorage.setItem("battleChessSessionToken", sessionToken);
        localStorage.setItem("battleChessUser", JSON.stringify({
          id: player.id,
          name: player.username,
          avatar: player.avatar,
          rating: player.rating,
          level: player.level,
          coins: player.coins,
        }));
        navigate("/dashboard", { replace: true });
      })
      .catch(() => {
        setFailureMessage("Google sign-in could not be completed. Please return and try again.");
      });
  }, [errorCode, navigate, ticket]);

  return (
    <main className="relative flex min-h-screen items-center justify-center overflow-hidden bg-gaming-darker px-4 text-center">
      <section className="glass-card relative z-10 w-full max-w-md rounded-[32px] p-8 sm:p-10">
        <p className="text-xs uppercase tracking-[0.3em] text-cyan-300">Google authentication</p>
        <h1 className="mt-4 text-2xl font-bold text-white">
          {isError ? "Sign-in unsuccessful" : "Signing you in"}
        </h1>
        <p className="mt-4 text-sm leading-6 text-slate-400" role={isError ? "alert" : "status"}>
          {message}
        </p>
        {isError && (
          <Link to="/auth" className="mt-8 inline-flex rounded-2xl bg-cyan-400 px-6 py-3 font-semibold text-black transition hover:bg-cyan-300">
            Return to sign in
          </Link>
        )}
      </section>
    </main>
  );
}

export default AuthCallback;
