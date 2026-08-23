import { FormEvent, useState } from "react";
import { Link } from "react-router-dom";
import { useAuth } from "../auth";

const BG = "https://images.unsplash.com/photo-1519494026892-80bbd2d6fd0d?q=80&w=2000&auto=format&fit=crop";

export default function Login() {
  const { login } = useAuth();
  const [phone, setPhone] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  const submit = async (e: FormEvent) => {
    e.preventDefault();
    setBusy(true);
    setError("");
    try {
      await login(phone, password);
    } catch (err: unknown) {
      const detail =
        (err as { response?: { data?: { detail?: string } } }).response?.data?.detail;
      setError(detail ?? "Login failed. Check your phone and password.");
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="min-h-screen relative flex items-center justify-center px-4 py-10 overflow-hidden">
      <img
        src={BG}
        alt=""
        aria-hidden
        className="absolute inset-0 w-full h-full object-cover opacity-25"
      />
      <div className="absolute inset-0 bg-gradient-to-br from-slate-950/90 via-slate-950/75 to-blue-950/85" />
      <div className="pointer-events-none absolute -top-32 right-0 h-[420px] w-[420px] rounded-full bg-teal-500/15 blur-[120px] animate-orb" />
      <div className="pointer-events-none absolute bottom-0 left-0 h-[360px] w-[360px] rounded-full bg-violet-600/15 blur-[110px] animate-orb [animation-delay:-7s]" />

      <div className="relative w-full max-w-md">
        <Link to="/" className="flex justify-center mb-8 hover:opacity-90 transition">
          <span className="h-14 w-14 grid place-items-center rounded-2xl bg-gradient-to-br from-teal-400 to-blue-600 text-2xl font-black text-slate-950 shadow-glow animate-pulseGlow">
            C
          </span>
        </Link>

        <form onSubmit={submit} className="cb-card p-8 space-y-5 animate-floaty [animation-duration:9s]">
          <div className="text-center">
            <h1 className="text-2xl font-extrabold tracking-tight">Welcome back</h1>
            <p className="mt-1 text-sm text-slate-400">Log in to your clinic&apos;s brain</p>
          </div>

          {error && (
            <p className="text-sm bg-red-500/10 border border-red-400/30 text-red-300 rounded-xl px-3.5 py-2.5">
              {error}
            </p>
          )}

          <div className="space-y-1.5">
            <label className="cb-label">Phone number</label>
            <input
              className="cb-input"
              placeholder="10-digit phone"
              value={phone}
              onChange={(e) => setPhone(e.target.value)}
              required
            />
          </div>
          <div className="space-y-1.5">
            <label className="cb-label">Password</label>
            <input
              type="password"
              className="cb-input"
              placeholder="••••••••"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
            />
          </div>

          <button disabled={busy} className="cb-btn w-full !py-3">
            {busy ? "Logging in..." : "Log in"}
          </button>

          <button
            type="button"
            onClick={() => {
              setPhone("9811111111");
              setPassword("demo1234");
            }}
            className="w-full text-xs text-slate-400 hover:text-teal-300 transition"
          >
            Use demo clinic credentials →
          </button>

          <p className="text-center text-sm text-slate-400">
            New clinic?{" "}
            <Link to="/signup" className="font-semibold text-gradient hover:opacity-80">
              Create one
            </Link>
          </p>
        </form>

        <p className="text-center mt-6 text-xs text-slate-600">
          <Link to="/" className="hover:text-slate-400 transition">← Back to home</Link>
        </p>
      </div>
    </div>
  );
}
