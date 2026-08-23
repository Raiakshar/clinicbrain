import { FormEvent, useState } from "react";
import { Link } from "react-router-dom";
import { useAuth } from "../auth";

const BG = "https://images.unsplash.com/photo-1551076805-e1869033e561?q=80&w=2000&auto=format&fit=crop";

export default function Signup() {
  const { signup } = useAuth();
  const [form, setForm] = useState({
    clinic_name: "",
    name: "",
    phone: "",
    password: "",
  });
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  const set = (k: keyof typeof form) => (e: { target: { value: string } }) =>
    setForm((f) => ({ ...f, [k]: e.target.value }));

  const submit = async (e: FormEvent) => {
    e.preventDefault();
    setBusy(true);
    setError("");
    try {
      await signup(form);
    } catch (err: unknown) {
      const msg =
        (err as { response?: { data?: { detail?: string } } }).response?.data?.detail ??
        "Signup failed";
      setError(msg);
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
      <div className="absolute inset-0 bg-gradient-to-bl from-slate-950/90 via-slate-950/75 to-teal-950/85" />
      <div className="pointer-events-none absolute -bottom-24 right-10 h-[400px] w-[400px] rounded-full bg-blue-500/15 blur-[120px] animate-orb" />

      <form onSubmit={submit} className="relative cb-card p-8 w-full max-w-md space-y-4">
        <div className="text-center mb-2">
          <span className="inline-grid place-items-center h-12 w-12 rounded-2xl bg-gradient-to-br from-teal-400 to-blue-600 text-xl font-black text-slate-950 shadow-glow">
            C
          </span>
          <h1 className="mt-4 text-2xl font-extrabold tracking-tight">Create your clinic</h1>
          <p className="mt-1 text-sm text-slate-400">Give your clinic a brain in two minutes</p>
        </div>

        <div className="space-y-1.5">
          <label className="cb-label">Clinic name</label>
          <input className="cb-input" placeholder="Sunrise Clinic" value={form.clinic_name} onChange={set("clinic_name")} required />
        </div>
        <div className="space-y-1.5">
          <label className="cb-label">Your name</label>
          <input className="cb-input" placeholder="Dr Sharma" value={form.name} onChange={set("name")} required />
        </div>
        <div className="space-y-1.5">
          <label className="cb-label">Phone number</label>
          <input className="cb-input" placeholder="10-digit phone" value={form.phone} onChange={set("phone")} required />
        </div>
        <div className="space-y-1.5">
          <label className="cb-label">Password</label>
          <input type="password" className="cb-input" placeholder="Min 6 characters" value={form.password} onChange={set("password")} required />
        </div>

        {error && (
          <p className="text-sm bg-red-500/10 border border-red-400/30 text-red-300 rounded-xl px-3.5 py-2.5">
            {error}
          </p>
        )}

        <button disabled={busy} className="cb-btn w-full !py-3">
          {busy ? "Creating..." : "Create clinic"}
        </button>

        <p className="text-center text-sm text-slate-400">
          Already registered?{" "}
          <Link to="/login" className="font-semibold text-gradient hover:opacity-80">
            Sign in
          </Link>
        </p>
      </form>
    </div>
  );
}
