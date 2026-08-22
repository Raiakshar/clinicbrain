import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { FormEvent, useState } from "react";
import { Link } from "react-router-dom";
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
    <div className="min-h-screen">
      <nav className="bg-white border-b border-slate-200">
        <div className="max-w-5xl mx-auto px-4 py-3 flex items-center justify-between">
          <Link to="/patients" className="font-bold text-slate-900">
            ClinicBrain
          </Link>
          <div className="flex items-center gap-6 text-sm">
            <Link to="/patients" className="text-slate-600 hover:text-slate-900">
              Patients
            </Link>
            <span className="text-blue-600 font-medium">Queue</span>
            <Link to="/review" className="text-slate-600 hover:text-slate-900">
              Review
            </Link>
          </div>
        </div>
      </nav>

      {toast && (
        <div className="fixed top-16 right-6 bg-slate-900 text-white px-4 py-2 rounded-lg shadow z-50 text-sm">
          {toast}
        </div>
      )}

      <main className="max-w-5xl mx-auto px-4 py-8 space-y-8">
        <section>
          <h1 className="text-xl font-bold mb-4">Today&apos;s queue</h1>
          {queue.length === 0 ? (
            <p className="text-slate-500">Nobody checked in yet.</p>
          ) : (
            <div className="bg-white border border-slate-200 rounded-lg divide-y divide-slate-100">
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
                      className="text-sm bg-blue-600 text-white rounded-lg px-3 py-1.5 font-medium hover:bg-blue-700"
                    >
                      Call
                    </button>
                  )}
                  {q.status === "in_consult" && (
                    <button
                      onClick={() => complete.mutate(q.id)}
                      className="text-sm bg-green-600 text-white rounded-lg px-3 py-1.5 font-medium hover:bg-green-700"
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
          <h2 className="text-lg font-bold mb-3">Check in a patient</h2>
          <form onSubmit={submitSearch}>
            <input
              className="w-full border border-slate-200 rounded-lg px-4 py-2"
              placeholder="Type at least 2 characters to search patients..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
            />
          </form>
          {search.length >= 2 && (
            <div className="mt-2 bg-white border border-slate-200 rounded-lg divide-y divide-slate-100">
              {patients.length === 0 && <p className="px-4 py-2 text-sm text-slate-400">No matches.</p>}
              {patients.map((p) => (
                <div key={p.id} className="flex items-center justify-between px-4 py-2">
                  <span className="text-sm">
                    {p.name} <span className="text-slate-400">{p.phone}</span>
                  </span>
                  <button
                    onClick={() => checkIn.mutate(p.id)}
                    className="text-sm border border-blue-600 text-blue-600 rounded-lg px-3 py-1 hover:bg-blue-50"
                  >
                    Check in
                  </button>
                </div>
              ))}
            </div>
          )}
        </section>

        <section>
          <h2 className="text-lg font-bold mb-3">WhatsApp messages</h2>
          {waLog.length === 0 ? (
            <p className="text-slate-500">No messages yet.</p>
          ) : (
            <div className="bg-white border border-slate-200 rounded-lg divide-y divide-slate-100">
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
    </div>
  );
}
