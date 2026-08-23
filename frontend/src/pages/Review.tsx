import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import AppShell from "../components/AppShell";
import { FormEvent, useEffect, useState } from "react";
import { useSearchParams } from "react-router-dom";
import { api } from "../api";
import type { Doc, LabDraftRow } from "../types";

const TYPES = ["visit", "prescription", "lab", "letter", "report"] as const;

function rowsFromDoc(doc: Doc | null): LabDraftRow[] {
  return doc?.extracted?.labs?.length ? doc.extracted.labs : [];
}

export default function Review() {
  const [params, setParams] = useSearchParams();
  const qc = useQueryClient();
  const [toast, setToast] = useState("");

  const { data: queue = [] } = useQuery({
    queryKey: ["reviewQueue"],
    queryFn: async () =>
      (await api.get<Doc[]>("/documents", { params: { status: "needs_review" } })).data,
    refetchInterval: 5000,
  });

  const { data: failed = [] } = useQuery({
    queryKey: ["failedQueue"],
    queryFn: async () =>
      (await api.get<Doc[]>("/documents", { params: { status: "failed" } })).data,
    refetchInterval: 5000,
  });

  const docId = Number(params.get("doc") ?? queue[0]?.id ?? 0);
  const doc = queue.find((d) => d.id === docId) ?? null;
  const isLabDoc = doc?.extracted?.labs != null || doc?.extracted?.lab_error != null;

  const [form, setForm] = useState({
    document_type: "report",
    event_date: "",
    summary: "",
    content_text: "",
  });
  const [labRows, setLabRows] = useState<LabDraftRow[]>([]);
  const [labDate, setLabDate] = useState("");

  useEffect(() => {
    if (doc?.extracted) {
      setForm({
        document_type: doc.extracted.document_type ?? "report",
        event_date: doc.extracted.event_date ?? "",
        summary: doc.extracted.summary ?? "",
        content_text: doc.extracted.content_text ?? "",
      });
      setLabRows(rowsFromDoc(doc));
      setLabDate(doc.extracted.event_date ?? "");
    }
  }, [docId]);

  const invalidate = () => {
    qc.invalidateQueries({ queryKey: ["reviewQueue"] });
    qc.invalidateQueries({ queryKey: ["failedQueue"] });
    qc.invalidateQueries({ queryKey: ["events"] });
  };

  const flash = (msg: string) => {
    setToast(msg);
    setTimeout(() => setToast(""), 2500);
  };

  const advance = () => {
    const rest = queue.filter((d) => d.id !== docId);
    if (rest.length > 0) setParams({ doc: String(rest[0].id) });
    else setParams({});
  };

  const confirm = useMutation({
    mutationFn: async () =>
      api.post(`/documents/${docId}/confirm`, {
        document_type: form.document_type,
        event_date: form.event_date || null,
        summary: form.summary,
        content_text: form.content_text,
      }),
    onSuccess: () => {
      invalidate();
      flash("Added to timeline");
      advance();
    },
  });

  const reject = useMutation({
    mutationFn: async () => api.post(`/documents/${docId}/reject`),
    onSuccess: () => {
      invalidate();
      flash("Document rejected");
      advance();
    },
  });

  const confirmLabs = useMutation({
    mutationFn: async () =>
      api.post(`/documents/${docId}/confirm-labs`, {
        rows: labRows.map((r) => ({ ...r, taken_at: r.taken_at || labDate || null })),
      }),
    onSuccess: () => {
      invalidate();
      flash("Labs added to timeline");
      advance();
    },
  });

  const retry = useMutation({
    mutationFn: async (id: number) => api.post(`/documents/${id}/retry`),
    onSuccess: invalidate,
  });

  const updateRow = (i: number, key: keyof LabDraftRow, value: string) =>
    setLabRows((rows) => rows.map((r, j) => (j === i ? { ...r, [key]: value } : r)));

  const onSubmit = (e: FormEvent) => {
    e.preventDefault();
    if (isLabDoc) confirmLabs.mutate();
    else confirm.mutate();
  };

  return (
    <AppShell>
      

      {toast && (
        <div className="fixed top-16 right-6 bg-green-600 text-white px-4 py-2 rounded-lg shadow z-50 text-sm">
          {toast}
        </div>
      )}

      <main className="max-w-6xl mx-auto px-4 py-8 grid grid-cols-1 lg:grid-cols-4 gap-6">
        <aside className="space-y-2">
          <h2 className="text-sm font-semibold text-slate-500 uppercase mb-2">Queue</h2>
          {queue.length === 0 && <p className="text-sm text-slate-400">Nothing to review.</p>}
          {queue.map((d) => (
            <button
              key={d.id}
              onClick={() => setParams({ doc: String(d.id) })}
              className={`w-full text-left text-sm px-3 py-2 rounded-lg border ${
                d.id === docId
                  ? "border-blue-600 bg-blue-50"
                  : "border-slate-200 bg-white hover:bg-slate-50"
              }`}
            >
              #{d.id} · patient {d.patient_id}
            </button>
          ))}

          {failed.length > 0 && (
            <>
              <h2 className="text-sm font-semibold text-red-600 uppercase mt-6 mb-2">Failed</h2>
              {failed.map((d) => (
                <div
                  key={d.id}
                  className="text-sm border border-red-200 bg-red-50 rounded-lg px-3 py-2"
                >
                  <p>#{d.id}</p>
                  <p className="text-xs text-red-600 truncate">{d.error}</p>
                  <button
                    onClick={() => retry.mutate(d.id)}
                    className="mt-1 text-xs border border-red-300 rounded px-2 py-0.5 hover:bg-white"
                  >
                    Retry
                  </button>
                </div>
              ))}
            </>
          )}
        </aside>

        {doc ? (
          <section className="lg:col-span-3 grid grid-cols-1 md:grid-cols-2 gap-6">
            <img
              src={`/api/documents/${doc.id}/file`}
              alt="document"
              className="max-h-[70vh] w-full object-contain bg-slate-100 rounded-lg border border-slate-200"
            />
            <form onSubmit={onSubmit} className="space-y-3">
              {isLabDoc ? (
                <>
                  <div className="flex items-center justify-between">
                    <h3 className="text-sm font-semibold text-slate-700">Lab results draft</h3>
                    <button
                      type="button"
                      onClick={() =>
                        setLabRows((r) => [
                          ...r,
                          { test_name: "", value: "", unit: "", ref_low: "", ref_high: "" },
                        ])
                      }
                      className="text-xs border border-slate-300 rounded-lg px-2 py-1 hover:bg-slate-50"
                    >
                      + Add row
                    </button>
                  </div>
                  <div className="space-y-2 max-h-[52vh] overflow-y-auto pr-1">
                    {labRows.map((row, i) => (
                      <div key={i} className="border border-slate-200 rounded-lg p-2 grid grid-cols-10 gap-1.5 items-center">
                        <input
                          className="col-span-3 border border-slate-200 rounded px-2 py-1 text-sm"
                          placeholder="Test name"
                          value={String(row.test_name ?? "")}
                          onChange={(e) => updateRow(i, "test_name", e.target.value)}
                        />
                        <input
                          className="col-span-2 border border-slate-200 rounded px-2 py-1 text-sm"
                          placeholder="Value"
                          value={String(row.value ?? "")}
                          onChange={(e) => updateRow(i, "value", e.target.value)}
                        />
                        <input
                          className="col-span-2 border border-slate-200 rounded px-2 py-1 text-sm"
                          placeholder="Unit"
                          value={String(row.unit ?? "")}
                          onChange={(e) => updateRow(i, "unit", e.target.value)}
                        />
                        <input
                          className="col-span-1 border border-slate-200 rounded px-2 py-1 text-sm"
                          placeholder="Low"
                          value={String(row.ref_low ?? "")}
                          onChange={(e) => updateRow(i, "ref_low", e.target.value)}
                        />
                        <input
                          className="col-span-1 border border-slate-200 rounded px-2 py-1 text-sm"
                          placeholder="High"
                          value={String(row.ref_high ?? "")}
                          onChange={(e) => updateRow(i, "ref_high", e.target.value)}
                        />
                        <button
                          type="button"
                          onClick={() => setLabRows((rows) => rows.filter((_, j) => j !== i))}
                          className="col-span-1 text-red-500 hover:text-red-700 text-sm"
                          title="Remove row"
                        >
                          ✕
                        </button>
                      </div>
                    ))}
                    {labRows.length === 0 && (
                      <p className="text-sm text-slate-400">
                        No rows extracted{doc?.extracted?.lab_error ? ` — ${doc.extracted.lab_error}` : ""}. Add rows manually or re-run extraction from the queue.
                      </p>
                    )}
                  </div>
                  <label className="block text-sm">
                    <span className="text-slate-400">Date on report</span>
                    <input
                      type="date"
                      className="mt-1 w-full border border-slate-200 rounded-lg px-3 py-2"
                      value={labDate}
                      onChange={(e) => setLabDate(e.target.value)}
                    />
                  </label>
                </>
              ) : (
                <>
                  <label className="block text-sm">
                    <span className="text-slate-400">Document type</span>
                    <select
                      className="mt-1 w-full border border-slate-200 rounded-lg px-3 py-2"
                      value={form.document_type}
                      onChange={(e) => setForm((f) => ({ ...f, document_type: e.target.value }))}
                    >
                      {TYPES.map((t) => (
                        <option key={t} value={t}>
                          {t}
                        </option>
                      ))}
                    </select>
                  </label>
                  <label className="block text-sm">
                    <span className="text-slate-400">Date on document</span>
                    <input
                      type="date"
                      className="mt-1 w-full border border-slate-200 rounded-lg px-3 py-2"
                      value={form.event_date}
                      onChange={(e) => setForm((f) => ({ ...f, event_date: e.target.value }))}
                    />
                  </label>
                  <label className="block text-sm">
                    <span className="text-slate-400">Summary</span>
                    <input
                      className="mt-1 w-full border border-slate-200 rounded-lg px-3 py-2"
                      value={form.summary}
                      onChange={(e) => setForm((f) => ({ ...f, summary: e.target.value }))}
                    />
                  </label>
                  <label className="block text-sm">
                    <span className="text-slate-400">Extracted text</span>
                    <textarea
                      rows={12}
                      className="mt-1 w-full border border-slate-200 rounded-lg px-3 py-2 font-mono text-xs"
                      value={form.content_text}
                      onChange={(e) => setForm((f) => ({ ...f, content_text: e.target.value }))}
                    />
                  </label>
                </>
              )}
              <div className="flex gap-3 pt-2">
                <button
                  disabled={(isLabDoc ? confirmLabs.isPending : confirm.isPending) || labRows.length === 0}
                  className="flex-1 bg-blue-600 text-white rounded-lg py-2 text-sm font-medium hover:bg-blue-700 disabled:opacity-50"
                >
                  {isLabDoc ? `Confirm ${labRows.length} labs → Timeline` : "Confirm → Timeline"}
                </button>
                <button
                  type="button"
                  onClick={() => reject.mutate()}
                  disabled={reject.isPending}
                  className="border border-red-300 text-red-600 rounded-lg px-4 py-2 text-sm font-medium hover:bg-red-50 disabled:opacity-50"
                >
                  Reject
                </button>
              </div>
            </form>
          </section>
        ) : (
          <section className="lg:col-span-3 flex items-center justify-center bg-white border border-slate-200 rounded-lg p-16">
            <p className="text-slate-400">All caught up. Nothing needs review.</p>
          </section>
        )}
      </main>
    </AppShell>
  );
}
