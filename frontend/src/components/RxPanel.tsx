import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { FormEvent, useEffect, useState } from "react";
import { api } from "../api";
import type { DrugRef, Patient, PrescriptionOut, RxItem, SafetyReport } from "../types";

const FREQ_OPTIONS = [1, 2, 3, 4];

export default function RxPanel({ pid }: { pid: number }) {
  const qc = useQueryClient();
  const [items, setItems] = useState<RxItem[]>([]);
  const [drugQuery, setDrugQuery] = useState("");
  const [selectedDrug, setSelectedDrug] = useState<DrugRef | null>(null);
  const [dose, setDose] = useState("");
  const [freq, setFreq] = useState(1);
  const [duration, setDuration] = useState("");
  const [notes, setNotes] = useState("");
  const [followupDate, setFollowupDate] = useState("");
  const [ack, setAck] = useState(false);
  const [toast, setToast] = useState("");
  const [report, setReport] = useState<SafetyReport | null>(null);
  const [checking, setChecking] = useState(false);

  const flash = (msg: string) => {
    setToast(msg);
    setTimeout(() => setToast(""), 3000);
  };

  const { data: patient } = useQuery<Patient>({
    queryKey: ["patient", pid],
    queryFn: async () => (await api.get<Patient>(`/patients/${pid}`)).data,
  });

  const { data: drugHits = [] } = useQuery({
    queryKey: ["drugs", drugQuery],
    queryFn: async () =>
      (await api.get<DrugRef[]>("/drugs", { params: { q: drugQuery } })).data,
    enabled: drugQuery.length >= 2 && !selectedDrug,
  });

  const { data: history = [] } = useQuery({
    queryKey: ["prescriptions", pid],
    queryFn: async () =>
      (await api.get<PrescriptionOut[]>(`/patients/${pid}/prescriptions`)).data,
  });

  useEffect(() => {
    if (items.length === 0) {
      setReport(null);
      return;
    }
    setChecking(true);
    const t = setTimeout(async () => {
      try {
        const resp = await api.post<SafetyReport>(`/patients/${pid}/check-rx`, { items });
        setReport(resp.data);
      } catch {
        setReport(null);
      } finally {
        setChecking(false);
      }
    }, 350);
    return () => clearTimeout(t);
  }, [items, pid]);

  useEffect(() => {
    if (report && report.warnings.length === 0) setAck(false);
  }, [report]);

  const saveAllergies = useMutation({
    mutationFn: async (allergies: string[]) =>
      api.put(`/patients/${pid}/allergies`, { allergies }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["patient", pid] });
      flash("Allergies saved");
    },
  });

  const saveRx = useMutation({
    mutationFn: async () =>
      api.post(`/patients/${pid}/prescriptions`, {
        items,
        notes: notes || undefined,
        followup_date: followupDate || undefined,
        acknowledged_warnings: ack,
      }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["prescriptions", pid] });
      qc.invalidateQueries({ queryKey: ["events", pid] });
      setItems([]);
      setNotes("");
      setFollowupDate("");
      setAck(false);
      setReport(null);
      flash("Prescription saved to timeline");
    },
    onError: (e: unknown) => {
      const detail = (e as { response?: { data?: { detail?: unknown } } }).response?.data?.detail;
      if (typeof detail === "object" && detail !== null) {
        setReport(detail as SafetyReport);
        flash(String((detail as { message?: string }).message ?? "Cannot save"));
      } else {
        flash("Cannot save prescription");
      }
    },
  });

  const addItem = (e: FormEvent) => {
    e.preventDefault();
    if (!selectedDrug || !dose) return;
    const doseMg = Number(dose);
    if (!Number.isFinite(doseMg) || doseMg <= 0) return;
    setItems((prev) => [
      ...prev,
      {
        drug_name: selectedDrug.name,
        dose_mg: doseMg,
        frequency_per_day: freq,
        duration_days: duration ? Number(duration) : null,
      },
    ]);
    setSelectedDrug(null);
    setDrugQuery("");
    setDose("");
    setFreq(1);
    setDuration("");
  };

  const blocked = (report?.blocks.length ?? 0) > 0;
  const warned = (report?.warnings.length ?? 0) > 0;

  const [allergen, setAllergen] = useState("");

  const submitAllergy = (e: FormEvent) => {
    e.preventDefault();
    const val = allergen.trim();
    if (!val) return;
    setAllergen("");
    if (!val) return;
    const current = patient?.allergies ?? [];
    if (current.some((a) => a.toLowerCase() === val.toLowerCase())) return;
    saveAllergies.mutate([...current, val]);
  };

  return (
    <div className="space-y-6">
      <section className="bg-white border border-slate-200 rounded-lg p-4">
        <h3 className="text-sm font-semibold text-slate-700 mb-2">Allergies</h3>
        <div className="flex flex-wrap gap-2 mb-3">
          {(patient?.allergies ?? []).length === 0 && (
            <span className="text-sm text-slate-400">None recorded — add known drug allergies.</span>
          )}
          {(patient?.allergies ?? []).map((a) => (
            <span
              key={a}
              className="inline-flex items-center gap-1 bg-red-50 text-red-700 border border-red-200 rounded-full px-3 py-1 text-sm"
            >
              {a}
              <button
                onClick={() =>
                  saveAllergies.mutate(
                    (patient?.allergies ?? []).filter((x) => x !== a)
                  )
                }
                className="text-red-400 hover:text-red-700"
              >
                ×
              </button>
            </span>
          ))}
        </div>
        <form onSubmit={submitAllergy} className="flex gap-2">
          <input
            className="border border-slate-200 rounded-lg px-3 py-1.5 text-sm flex-1"
            placeholder="e.g. penicillin, sulfa, nsaid..."
            value={allergen}
            onChange={(e) => setAllergen(e.target.value)}
          />
          <button className="text-sm border border-slate-300 rounded-lg px-3 py-1.5 hover:bg-slate-50">
            Add allergy
          </button>
        </form>
      </section>

      <section className="bg-white border border-slate-200 rounded-lg p-4">
        <h3 className="text-sm font-semibold text-slate-700 mb-3">New prescription</h3>
        <form onSubmit={addItem} className="grid grid-cols-12 gap-2 items-start">
          <div className="col-span-5 relative">
            <input
              className="w-full border border-slate-200 rounded-lg px-3 py-2"
              placeholder="Search drug..."
              value={selectedDrug ? selectedDrug.name : drugQuery}
              onChange={(e) => {
                setSelectedDrug(null);
                setDrugQuery(e.target.value);
              }}
            />
            {drugHits.length > 0 && (
              <ul className="absolute z-10 w-full bg-white border border-slate-200 rounded-lg mt-1 max-h-56 overflow-auto shadow">
                {drugHits.map((d) => (
                  <li key={d.id}>
                    <button
                      type="button"
                      onClick={() => {
                        setSelectedDrug(d);
                        setDrugQuery(d.name);
                      }}
                      className="w-full text-left px-3 py-2 hover:bg-slate-50"
                    >
                      <span className="text-sm font-medium">{d.name}</span>{" "}
                      <span className="text-xs text-slate-400">
                        {d.generic_name} · max {d.max_daily_dose_mg}mg/day
                      </span>
                    </button>
                  </li>
                ))}
              </ul>
            )}
          </div>
          <input
            type="number"
            min="0.1"
            step="any"
            className="col-span-2 border border-slate-200 rounded-lg px-3 py-2"
            placeholder="Dose mg"
            value={dose}
            onChange={(e) => setDose(e.target.value)}
          />
          <select
            className="col-span-2 border border-slate-200 rounded-lg px-2 py-2"
            value={freq}
            onChange={(e) => setFreq(Number(e.target.value))}
          >
            {FREQ_OPTIONS.map((f) => (
              <option key={f} value={f}>
                ×{f}/day
              </option>
            ))}
          </select>
          <input
            type="number"
            min="1"
            className="col-span-2 border border-slate-200 rounded-lg px-3 py-2"
            placeholder="Days"
            value={duration}
            onChange={(e) => setDuration(e.target.value)}
          />
          <button
            className="col-span-1 bg-blue-600 text-white rounded-lg py-2 font-medium hover:bg-blue-700 disabled:opacity-40"
            disabled={!selectedDrug || !dose}
          >
            +
          </button>
        </form>

        {items.length > 0 && (
          <ul className="mt-3 divide-y divide-slate-100 border border-slate-100 rounded-lg">
            {items.map((it, i) => (
              <li key={`${it.drug_name}-${i}`} className="flex items-center justify-between px-3 py-2">
                <span className="text-sm">
                  <span className="font-medium">{it.drug_name}</span> · {it.dose_mg}mg ×{it.frequency_per_day}/day
                  {it.duration_days ? ` · ${it.duration_days} days` : ""}
                </span>
                <button
                  onClick={() => setItems(items.filter((_, j) => j !== i))}
                  className="text-slate-400 hover:text-red-600 text-sm"
                >
                  remove
                </button>
              </li>
            ))}
          </ul>
        )}

        {checking && <p className="mt-3 text-xs text-slate-400">Checking safety...</p>}
        {report && !checking && (
          <div className="mt-3 space-y-2">
            {report.blocks.map((b) => (
              <p key={b} className="text-sm bg-red-50 border border-red-200 text-red-700 rounded-lg px-3 py-2">
                ⛔ {b}
              </p>
            ))}
            {report.warnings.map((w) => (
              <p key={w} className="text-sm bg-amber-50 border border-amber-200 text-amber-800 rounded-lg px-3 py-2">
                ⚠️ {w}
              </p>
            ))}
          </div>
        )}

        {items.length > 0 && (
          <div className="mt-4 space-y-3">
            <textarea
              className="w-full border border-slate-200 rounded-lg px-3 py-2"
              rows={2}
              placeholder="Notes / instructions (optional)"
              value={notes}
              onChange={(e) => setNotes(e.target.value)}
            />
            <div className="flex items-center gap-3 flex-wrap">
              <label className="text-sm text-slate-600">
                Follow-up date:
                <input
                  type="date"
                  className="ml-2 border border-slate-200 rounded-lg px-2 py-1 text-sm"
                  value={followupDate}
                  onChange={(e) => setFollowupDate(e.target.value)}
                />
              </label>
            </div>
            {warned && (
              <label className="flex items-center gap-2 text-sm text-amber-800">
                <input type="checkbox" checked={ack} onChange={(e) => setAck(e.target.checked)} />
                I have reviewed the warnings and confirm this prescription is intentional.
              </label>
            )}
            <button
              onClick={() => saveRx.mutate()}
              disabled={blocked || saveRx.isPending || (warned && !ack)}
              className="bg-green-600 text-white rounded-lg px-4 py-2 text-sm font-medium hover:bg-green-700 disabled:opacity-40"
            >
              {blocked ? "Blocked by allergy" : warned && !ack ? "Acknowledge warnings to save" : "Save prescription"}
            </button>
          </div>
        )}
      </section>

      <section>
        <h3 className="text-sm font-semibold text-slate-700 mb-2">Past prescriptions</h3>
        {history.length === 0 ? (
          <p className="text-slate-500 text-sm">No prescriptions yet.</p>
        ) : (
          <div className="space-y-2">
            {history.map((rx) => (
              <div key={rx.id} className="bg-white border border-slate-200 rounded-lg px-4 py-3">
                <div className="flex justify-between text-xs text-slate-400 mb-1">
                  <span>#{rx.id}</span>
                  <span>{rx.created_at?.slice(0, 10)}</span>
                </div>
                <ul className="text-sm space-y-0.5">
                  {rx.items.map((it, i) => (
                    <li key={i}>
                      <span className="font-medium">{it.drug_name}</span> · {it.dose_mg}mg ×{it.frequency_per_day}/day
                    </li>
                  ))}
                </ul>
                {rx.notes && <p className="text-xs text-slate-500 mt-1">{rx.notes}</p>}
              </div>
            ))}
          </div>
        )}
      </section>

      {toast && (
        <div className="fixed bottom-6 right-6 bg-slate-900 text-white px-4 py-2 rounded-lg shadow z-50 text-sm">
          {toast}
        </div>
      )}
    </div>
  );
}
