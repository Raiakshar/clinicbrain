import { useQuery, useQueryClient } from "@tanstack/react-query";
import { FormEvent, useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { api } from "../api";
import AppShell from "../components/AppShell";
import type { Patient } from "../types";

function Avatar({ name }: { name: string }) {
  const hues = ["from-teal-400/40 to-blue-500/40", "from-violet-400/40 to-fuchsia-500/40", "from-sky-400/40 to-indigo-500/40", "from-emerald-400/40 to-teal-500/40"];
  const hue = hues[name.length % hues.length];
  return (
    <span className={`grid place-items-center h-11 w-11 shrink-0 rounded-full bg-gradient-to-br ${hue} border border-white/15 text-sm font-bold text-white`}>
      {name.slice(0, 2).toUpperCase()}
    </span>
  );
}

export default function Patients() {
  const navigate = useNavigate();
  const qc = useQueryClient();
  const [q, setQ] = useState("");
  const [debouncedQ, setDebouncedQ] = useState("");
  const [showForm, setShowForm] = useState(false);
  const [form, setForm] = useState({ name: "", phone: "", dob: "", gender: "" });

  useEffect(() => {
    const t = setTimeout(() => setDebouncedQ(q), 250);
    return () => clearTimeout(t);
  }, [q]);

  const { data: patients = [], isLoading } = useQuery({
    queryKey: ["patients", debouncedQ],
    queryFn: async () =>
      (await api.get<Patient[]>("/patients", { params: { q: debouncedQ || undefined } })).data,
  });

  const create = async (e: FormEvent) => {
    e.preventDefault();
    await api.post("/patients", {
      name: form.name,
      phone: form.phone || null,
      dob: form.dob || null,
      gender: form.gender || null,
    });
    setForm({ name: "", phone: "", dob: "", gender: "" });
    setShowForm(false);
    qc.invalidateQueries({ queryKey: ["patients"] });
  };

  return (
    <AppShell>
      <div className="flex flex-wrap items-center justify-between gap-4 mb-8">
        <div>
          <p className="cb-label">Directory</p>
          <h1 className="mt-1 text-3xl font-extrabold tracking-tight">
            Patients
          </h1>
        </div>
        <button onClick={() => setShowForm((s) => !s)} className={showForm ? "cb-btn-ghost" : "cb-btn"}>
          {showForm ? "Cancel" : "+ Add patient"}
        </button>
      </div>

      {showForm && (
        <form onSubmit={create} className="cb-card p-5 mb-6 grid sm:grid-cols-2 lg:grid-cols-4 gap-3 animate-floaty [animation-duration:1s]">
          <input className="cb-input" placeholder="Full name *" value={form.name} onChange={(e) => setForm((f) => ({ ...f, name: e.target.value }))} required />
          <input className="cb-input" placeholder="Phone" value={form.phone} onChange={(e) => setForm((f) => ({ ...f, phone: e.target.value }))} />
          <input type="date" className="cb-input" value={form.dob} onChange={(e) => setForm((f) => ({ ...f, dob: e.target.value }))} />
          <div className="flex gap-2">
            <select className="cb-input flex-1" value={form.gender} onChange={(e) => setForm((f) => ({ ...f, gender: e.target.value }))}>
              <option value="">Gender</option>
              <option value="male">Male</option>
              <option value="female">Female</option>
              <option value="other">Other</option>
            </select>
            <button className="cb-btn px-4">Save</button>
          </div>
        </form>
      )}

      <div className="relative mb-6">
        <span className="absolute left-4 top-1/2 -translate-y-1/2 text-slate-500">⌕</span>
        <input
          className="cb-input !pl-10 !py-3"
          placeholder="Search by name or phone..."
          value={q}
          onChange={(e) => setQ(e.target.value)}
        />
      </div>

      {isLoading ? (
        <p className="text-slate-400">Loading...</p>
      ) : patients.length === 0 ? (
        <div className="cb-card p-12 text-center">
          <p className="text-lg font-semibold">No patients found</p>
          <p className="text-sm text-slate-400 mt-1">Add your first patient to get started.</p>
        </div>
      ) : (
        <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-4">
          {patients.map((p) => (
            <button
              key={p.id}
              onClick={() => navigate(`/patients/${p.id}`)}
              className="cb-card cb-card-hover p-4 flex items-center gap-4 text-left w-full group"
            >
              <Avatar name={p.name} />
              <div className="min-w-0 flex-1">
                <p className="font-semibold truncate group-hover:text-teal-300 transition">{p.name}</p>
                <p className="text-sm text-slate-400 truncate">{[p.phone, p.gender].filter(Boolean).join(" · ")}</p>
              </div>
              <span className="text-slate-600 group-hover:text-teal-300 transition">→</span>
            </button>
          ))}
        </div>
      )}
    </AppShell>
  );
}
