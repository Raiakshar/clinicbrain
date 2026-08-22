import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { FormEvent, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { api } from "../api";
import TrendChart from "../components/TrendChart";
import type { Doc, Patient, PatientLab, TimelineEvent, EventType, TrendPoint } from "../types";

const BADGE: Record<EventType, string> = {
  visit: "bg-blue-100 text-blue-700",
  prescription: "bg-green-100 text-green-700",
  lab: "bg-amber-100 text-amber-700",
  document: "bg-slate-200 text-slate-700",
  note: "bg-violet-100 text-violet-700",
};

const STATUS_PILL: Record<string, string> = {
  pending: "bg-slate-100 text-slate-600",
  processing: "bg-blue-100 text-blue-700",
  needs_review: "bg-amber-100 text-amber-700",
  processed: "bg-green-100 text-green-700",
  failed: "bg-red-100 text-red-700",
};

const FLAG_PILL: Record<string, string> = {
  normal: "bg-green-100 text-green-700",
  high: "bg-red-100 text-red-700",
  low: "bg-amber-100 text-amber-700",
  review: "bg-yellow-100 text-yellow-700",
};

function eventText(e: TimelineEvent): string {
  const p = e.payload ?? {};
  if (typeof p.summary === "string" && p.summary) return p.summary;
  if (typeof p.text === "string" && p.text) return p.text;
  return JSON.stringify(p).slice(0, 120);
}

export default function PatientDetail() {
  const { id } = useParams();
  const pid = Number(id);
  const qc = useQueryClient();
  const [tab, setTab] = useState<"timeline" | "documents" | "labs">("timeline");
  const [noteText, setNoteText] = useState("");
  const [noteDate, setNoteDate] = useState("");
  const [uploading, setUploading] = useState(0);
  const [openTest, setOpenTest] = useState<string | null>(null);

  const { data: patient } = useQuery({
    queryKey: ["patient", pid],
    queryFn: async () => (await api.get<Patient>(`/patients/${pid}`)).data,
  });

  const { data: events = [] } = useQuery({
    queryKey: ["events", pid],
    queryFn: async () =>
      (await api.get<TimelineEvent[]>(`/patients/${pid}/events`)).data,
  });

  const { data: docs = [] } = useQuery({
    queryKey: ["docs", pid],
    queryFn: async () =>
      (await api.get<Doc[]>("/documents", { params: { patient_id: pid } })).data,
    refetchInterval: (query) =>
      query.state.data?.some((d) => d.status === "pending" || d.status === "processing")
        ? 2000
        : false,
  });

  const { data: labs = [] } = useQuery({
    queryKey: ["labs", pid],
    queryFn: async () => (await api.get<PatientLab[]>(`/patients/${pid}/labs`)).data,
  });

  const { data: trend = [] } = useQuery({
    queryKey: ["trend", pid, openTest],
    queryFn: async () =>
      (
        await api.get<TrendPoint[]>(`/patients/${pid}/labs/trend`, {
          params: { test_name: openTest },
        })
      ).data,
    enabled: openTest != null,
  });

  const addNote = useMutation({
    mutationFn: async () => {
      await api.post(`/patients/${pid}/events`, {
        type: "note",
        event_date: noteDate || null,
        payload: { text: noteText },
      });
    },
    onSuccess: () => {
      setNoteText("");
      setNoteDate("");
      qc.invalidateQueries({ queryKey: ["events", pid] });
    },
  });

  const retry = useMutation({
    mutationFn: async (docId: number) => api.post(`/documents/${docId}/retry`),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["docs", pid] }),
  });

  const onFiles = async (files: FileList | null) => {
    if (!files) return;
    setUploading(files.length);
    for (const file of Array.from(files)) {
      const fd = new FormData();
      fd.append("file", file);
      await api.post(`/patients/${pid}/documents`, fd);
      setUploading((n) => n - 1);
    }
    qc.invalidateQueries({ queryKey: ["docs", pid] });
  };

  const submitNote = (e: FormEvent) => {
    e.preventDefault();
    if (noteText.trim()) addNote.mutate();
  };

  return (
    <div className="min-h-screen">
      <nav className="bg-white border-b border-slate-200">
        <div className="max-w-5xl mx-auto px-4 py-3 flex items-center justify-between">
          <Link to="/patients" className="font-bold text-slate-900">
            ClinicBrain
          </Link>
          <div className="flex items-center gap-6 text-sm">
            <Link to="/review" className="text-slate-600 hover:text-slate-900">
              Review Queue
            </Link>
          </div>
        </div>
      </nav>

      <main className="max-w-5xl mx-auto px-4 py-8">
        <h1 className="text-xl font-bold">{patient?.name ?? "..."}</h1>
        <p className="text-sm text-slate-500 mb-6">
          {[patient?.phone, patient?.dob, patient?.gender].filter(Boolean).join(" · ")}
        </p>

        <div className="flex gap-2 mb-6 border-b border-slate-200">
          {(["timeline", "documents", "labs"] as const).map((t) => (
            <button
              key={t}
              onClick={() => setTab(t)}
              className={`px-4 py-2 text-sm font-medium capitalize border-b-2 -mb-px ${
                tab === t
                  ? "border-blue-600 text-blue-600"
                  : "border-transparent text-slate-500 hover:text-slate-900"
              }`}
            >
              {t}
            </button>
          ))}
        </div>

        {tab === "timeline" && (
          <div className="space-y-4">
            <form onSubmit={submitNote} className="bg-white border border-slate-200 rounded-lg p-4 space-y-3">
              <textarea
                className="w-full border border-slate-200 rounded-lg px-3 py-2"
                rows={2}
                placeholder="Add a note to the timeline..."
                value={noteText}
                onChange={(e) => setNoteText(e.target.value)}
              />
              <div className="flex gap-3 items-center">
                <input
                  type="date"
                  className="border border-slate-200 rounded-lg px-3 py-1.5 text-sm"
                  value={noteDate}
                  onChange={(e) => setNoteDate(e.target.value)}
                />
                <button
                  disabled={addNote.isPending}
                  className="bg-blue-600 text-white rounded-lg px-4 py-1.5 text-sm font-medium hover:bg-blue-700 disabled:opacity-50"
                >
                  Add note
                </button>
              </div>
            </form>

            {events.length === 0 ? (
              <p className="text-slate-500">No history yet.</p>
            ) : (
              events.map((e) => (
                <div key={e.id} className="bg-white border border-slate-200 rounded-lg p-4">
                  <div className="flex items-center gap-3 mb-1">
                    <span className={`text-xs font-medium px-2 py-0.5 rounded-full ${BADGE[e.type]}`}>
                      {e.type}
                    </span>
                    <span className="text-xs text-slate-400">{e.event_date ?? ""}</span>
                  </div>
                  <p className="text-sm whitespace-pre-wrap">{eventText(e)}</p>
                </div>
              ))
            )}
          </div>
        )}

        {tab === "labs" && (
          <div className="space-y-3">
            {labs.length === 0 ? (
              <p className="text-slate-500">
                No lab results yet. Confirm a lab report from the Documents tab.
              </p>
            ) : (
              labs.map((l) => (
                <div key={l.test_name} className="bg-white border border-slate-200 rounded-lg">
                  <button
                    onClick={() => setOpenTest(openTest === l.test_name ? null : l.test_name)}
                    className="w-full flex items-center justify-between px-4 py-3 text-left hover:bg-slate-50"
                  >
                    <div className="flex items-center gap-3">
                      <span className="font-medium">{l.test_name}</span>
                      <span className={`text-xs font-medium px-2 py-0.5 rounded-full ${FLAG_PILL[l.flag]}`}>
                        {l.flag}
                      </span>
                    </div>
                    <div className="flex items-center gap-3 text-sm">
                      <span className="font-semibold">
                        {l.value} {l.unit ?? ""}
                      </span>
                      <span className="text-slate-400">{l.taken_at}</span>
                      {l.count > 1 && (
                        <span className="text-xs text-blue-600">{l.count} readings ▾</span>
                      )}
                    </div>
                  </button>
                  {openTest === l.test_name && (
                    <div className="px-4 pb-4">
                      <TrendChart points={trend} />
                    </div>
                  )}
                </div>
              ))
            )}
          </div>
        )}

        {tab === "documents" && (
          <div className="space-y-4">
            <label className="block bg-white border-2 border-dashed border-slate-300 rounded-lg p-8 text-center cursor-pointer hover:border-blue-500">
              <span className="text-sm text-slate-600">
                {uploading > 0 ? `Uploading ${uploading} file(s)...` : "Tap to scan or photograph documents"}
              </span>
              <input
                type="file"
                accept="image/*"
                multiple
                capture="environment"
                className="hidden"
                onChange={(e) => {
                  onFiles(e.target.files);
                  e.target.value = "";
                }}
              />
            </label>

            {docs.map((d) => (
              <div key={d.id} className="bg-white border border-slate-200 rounded-lg p-4 flex items-center gap-4">
                {d.status !== "pending" && (
                  <img
                    src={`/api/documents/${d.id}/file`}
                    alt=""
                    className="w-16 h-16 object-cover rounded-lg bg-slate-50"
                  />
                )}
                <div className="flex-1 min-w-0">
                  <span className={`text-xs font-medium px-2 py-0.5 rounded-full ${STATUS_PILL[d.status]}`}>
                    {d.status.replace("_", " ")}
                  </span>
                  {d.error && <p className="text-xs text-red-600 mt-1">{d.error}</p>}
                </div>
                {d.status === "failed" && (
                  <button
                    onClick={() => retry.mutate(d.id)}
                    className="text-sm border border-slate-300 rounded-lg px-3 py-1.5 hover:bg-slate-50"
                  >
                    Retry
                  </button>
                )}
                {d.status === "needs_review" && (
                  <Link
                    to={`/review?doc=${d.id}`}
                    className="text-sm bg-blue-600 text-white rounded-lg px-3 py-1.5 font-medium hover:bg-blue-700"
                  >
                    Review
                  </Link>
                )}
              </div>
            ))}
          </div>
        )}
      </main>
    </div>
  );
}
