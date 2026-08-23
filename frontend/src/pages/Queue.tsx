import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import AppShell from "../components/AppShell";
import { FormEvent, useState } from "react";
import { api } from "../api";
import type { Patient } from "../types";

interface QueueEntry {
  id: number;
  number: number;
  status: string;
  patient_id: number;
  patient_name: string;
  checked_in_at: string | null;
}

interface WaLog {
  id: number;
  patient_name: string;
  template: string;
  body: string | null;
  status: string;
  retries: number;
  error: string | null;
}

const TOKEN_STATUS: Record<string, string> = {
  waiting: "bg-blue-100 text-blue-700",
  in_consult: "bg-amber-100 text-amber-700",
  done: "bg-green-100 text-green-700",
};

const WA_STATUS: Record<string, string> = {
  sent: "bg-green-100 text-green-700",
  retrying: "bg-amber-100 text-amber-700",
  failed: "bg-red-100 text-red-700",
};

export default function Queue() {
  const qc = useQueryClient();
  const [search, setSearch] = useState("");
  const [toast, setToast] = useState("");
  const [showNew, setShowNew] = useState(false);
  const [newName, setNewName] = useState("");
  const [newPhone, setNewPhone] = useState("");

  const flash = (msg: string) => {
    setToast(msg);
    setTimeout(() => setToast(""), 2500);
  };

  const { data: queue = [] } = useQuery({
    queryKey: ["queue"],
    queryFn: async () => (await api.get<QueueEntry[]>("/queue/today")).data,
    refetchInterval: 5000,
  });

  const { data: patients = [] } = useQuery({
    queryKey: ["patients", search],
    queryFn: async () =>
      (await api.get<Patient[]>("/patients", { params: { q: search || undefined } })).data,
    enabled: search.length >= 2,
  });

  const { data: waLog = [] } = useQuery({
    queryKey: ["waLog"],
    queryFn: async () => (await api.get<WaLog[]>("/queue/whatsapp-log")).data,
    refetchInterval: 5000,
  });

  const invalidate = () => {
    qc.invalidateQueries({ queryKey: ["queue"] });
    qc.invalidateQueries({ queryKey: ["waLog"] });
  };

  const checkIn = useMutation({
    mutationFn: async (patientId: number) =>
      (await api.post("/queue/check-in", { patient_id: patientId })).data,
    onSuccess: (t) => {
      invalidate();
      flash(`Token #${t.number} issued`);
      setSearch("");
    },
    onError: () => flash("Check-in failed"),
  });

  const walkIn = useMutation({
    mutationFn: async () =>
      (await api.post("/queue/check-in", { new_patient: { name: newName, phone: newPhone || null } })).data,
    onSuccess: (t) => {
      invalidate();
      qc.invalidateQueries({ queryKey: ["patients"] });
      flash(`Token #${t.number} issued for new patient`);
      setNewName("");
      setNewPhone("");
      setShowNew(false);
    },
    onError: () => flash("Could not add patient"),
  });

  const call = useMutation({
    mutationFn: async (id: number) => api.post(`/queue/${id}/call`),
    onSuccess: invalidate,
    onError: (e: unknown) =>
      flash(
        ((e as { response?: { data?: { detail?: string } } }).response?.data?.detail as string) ??
          "Cannot call now"
      ),
  });

  const complete = useMutation({
    mutationFn: async (id: number) => api.post(`/queue/${id}/complete`),
    onSuccess: invalidate,
  });

  const submitSearch = (e: FormEvent) => {
    e.preventDefault();
  };

  return (
    <AppShell>
      

      {toast && (
        <div className="fixed top-16 right-6 bg-slate-900 text-white px-4 py-2 rounded-lg shadow z-50 text-sm">
          {toast}
        </div>
      )}

      <main className="max-w-5xl mx-auto px-4 py-8 space-y-8">
        <section>
          <h1 className="text-2xl font-extrabold tracking-tight mb-5">Today&apos;s queue</h1>
          {queue.length === 0 ? (
            <p className="text-slate-400">Nobody checked in yet.</p>
          ) : (
            <div className="cb-card divide-y divide-white/[0.08]">
              {queue.map((q) => (
                <div key={q.id} className="flex items-center gap-4 px-4 py-3">
                  <span className="text-2xl font-bold text-slate-300 w-10">#{q.number}</span>
                  <span className="font-medium flex-1">{q.patient_name}</span>
                  <span className={`text-xs font-medium px-2 py-0.5 rounded-full ${TOKEN_STATUS[q.status]}`}>
                    {q.status.replace("_", " ")}
                  </span>
                  {q.status === "waiting" && (
                    <button
                      onClick={() => call.mutate(q.id)}
                      className="text-sm cb-btn !px-3 !py-1.5"
                    >
                      Call
                    </button>
                  )}
                  {q.status === "in_consult" && (
                    <button
                      onClick={() => complete.mutate(q.id)}
                      className="text-sm cb-btn !px-3 !py-1.5"
                    >
                      Complete
                    </button>
                  )}
                  {q.status === "done" && <span className="w-[72px]" />}
                </div>
              ))}
            </div>
          )}
        </section>

        <section>
          <div className="flex items-center justify-between mb-3">
            <h2 className="text-base font-bold mb-0 text-gradient">Check in a patient</h2>
            <button onClick={() => setShowNew((s) => !s)} className={showNew ? "cb-btn-ghost !py-1.5" : "cb-btn !py-1.5"}>
              {showNew ? "Cancel" : "+ New patient"}
            </button>
          </div>
          {showNew && (
            <form
              onSubmit={(e) => {
                e.preventDefault();
                if (newName.trim()) walkIn.mutate();
              }}
              className="cb-card p-4 mb-4 flex flex-wrap gap-3 items-end"
            >
              <div className="flex-1 min-w-[180px] space-y-1">
                <label className="cb-label">Name *</label>
                <input className="cb-input" placeholder="Patient full name" value={newName} onChange={(e) => setNewName(e.target.value)} required />
              </div>
              <div className="w-44 space-y-1">
                <label className="cb-label">Phone (unique ID)</label>
                <input className="cb-input" placeholder="10-digit phone" value={newPhone} onChange={(e) => setNewPhone(e.target.value)} />
              </div>
              <button disabled={!newName.trim() || walkIn.isPending} className="cb-btn">
                Add &amp; give token
              </button>
            </form>
          )}
          <form onSubmit={submitSearch}>
            <input
              className="cb-input"
              placeholder="Type at least 2 characters to search patients..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
            />
          </form>
          {search.length >= 2 && (
            <div className="mt-2 bg-white border border-slate-200 rounded-lg divide-y divide-slate-100">
              {patients.length === 0 && (
                <p className="px-4 py-2 text-sm text-slate-400">
                  No matches — use “+ New patient” to register and get a token in one step.
                </p>
              )}
              {patients.map((p) => (
                <div key={p.id} className="flex items-center justify-between px-4 py-2">
                  <span className="text-sm">
                    {p.name} <span className="text-slate-400">{p.phone}</span>
                  </span>
                  <button
                    onClick={() => checkIn.mutate(p.id)}
                    className="text-sm cb-btn-ghost !px-3 !py-1 !border-teal-300/40 !text-teal-300 hover:!bg-teal-400/10"
                  >
                    Check in
                  </button>
                </div>
              ))}
            </div>
          )}
        </section>

        <section>
          <h2 className="text-base font-bold mb-3 text-gradient">WhatsApp messages</h2>
          {waLog.length === 0 ? (
            <p className="text-slate-400">No messages yet.</p>
          ) : (
            <div className="cb-card divide-y divide-white/[0.08]">
              {waLog.map((w) => (
                <div key={w.id} className="px-4 py-3 flex items-start gap-3">
                  <span className={`text-xs font-medium px-2 py-0.5 rounded-full mt-0.5 ${WA_STATUS[w.status]}`}>
                    {w.status}
                    {w.retries > 0 && w.status !== "sent" ? ` ×${w.retries}` : ""}
                  </span>
                  <div className="flex-1 min-w-0">
                    <p className="text-sm">
                      <span className="font-medium">{w.patient_name}</span>{" "}
                      <span className="text-slate-400">· {w.template}</span>
                    </p>
                    <p className="text-sm text-slate-500 truncate">{w.body}</p>
                    {w.error && <p className="text-xs text-red-600 mt-0.5">{w.error}</p>}
                  </div>
                </div>
              ))}
            </div>
          )}
        </section>
      </main>
    </AppShell>
  );
}
