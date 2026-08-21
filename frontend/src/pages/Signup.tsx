import { FormEvent, useState } from "react";
import { Link } from "react-router-dom";
import { useAuth } from "../auth";

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
    <div className="min-h-screen flex items-center justify-center p-4">
      <form
        onSubmit={submit}
        className="bg-white rounded-lg border border-slate-200 shadow-sm w-full max-w-sm p-8 space-y-4"
      >
        <h1 className="text-2xl font-bold text-slate-900">Create your clinic</h1>
        <input
          className="w-full border border-slate-200 rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-600"
          placeholder="Clinic name"
          value={form.clinic_name}
          onChange={set("clinic_name")}
          required
        />
        <input
          className="w-full border border-slate-200 rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-600"
          placeholder="Your name"
          value={form.name}
          onChange={set("name")}
          required
        />
        <input
          className="w-full border border-slate-200 rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-600"
          placeholder="Phone"
          value={form.phone}
          onChange={set("phone")}
          required
        />
        <input
          type="password"
          className="w-full border border-slate-200 rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-600"
          placeholder="Password (min 6 chars)"
          value={form.password}
          onChange={set("password")}
          required
        />
        {error && <p className="text-sm text-red-600">{error}</p>}
        <button
          disabled={busy}
          className="w-full bg-blue-600 text-white rounded-lg py-2 font-medium hover:bg-blue-700 disabled:opacity-50"
        >
          {busy ? "Creating..." : "Create clinic"}
        </button>
        <p className="text-sm text-slate-500">
          Already registered?{" "}
          <Link to="/login" className="text-blue-600 hover:underline">
            Sign in
          </Link>
        </p>
      </form>
    </div>
  );
}
