import { useQuery, useQueryClient } from "@tanstack/react-query";
import { FormEvent, useEffect, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { api } from "../api";
import { useAuth } from "../auth";
import type { Patient } from "../types";

export default function Patients() {
  const { user, logout } = useAuth();
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
    <div className="min-h-screen">
      <nav className="bg-white border-b border-slate-200">
        <div className="max-w-5xl mx-auto px-4 py-3 flex items-center justify-between">
          <span className="font-bold text-slate-900">ClinicBrain</span>
          <div className="flex items-center gap-6 text-sm">
            <Link to="/patients" className="text-blue-600 font-medium">
              Patients
            </Link>
            <Link to="/review" className="text-slate-600 hover:text-slate-900">
              Review Queue
            </Link>
            <span className="text-slate-500">{user?.name}</span>
            <button onClick={logout} className="text-slate-500 hover:text-red-600">
              Logout
            </button>
          </div>
        </div>
      </nav>

      <main className="max-w-5xl mx-auto px-4 py-8">
        <div className="flex items-center justify-between mb-6">
          <h1 className="text-xl font-bold">Patients</h1>
          <button
            onClick={() => setShowForm((s) => !s)}
            className="bg-blue-600 text-white rounded-lg px-4 py-2 text-sm font-medium hover:bg-blue-700"
          >
            {showForm ? "Cancel" : "Add patient"}
          </button>
        </div>

        {showForm && (
          <form
            onSubmit={create}
            className="bg-white border border-slate-200 rounded-lg p-4 mb-6 grid grid-cols-2 gap-3"
          >
            <input
              className="border border-slate-200 rounded-lg px-3 py-2"
              placeholder="Full name *"
              value={form.name}
              onChange={(e) => setForm((f) => ({ ...f, name: e.target.value }))}
              required
            />
            <input
              className="border border-slate-200 rounded-lg px-3 py-2"
              placeholder="Phone"
              value={form.phone}
              onChange={(e) => setForm((f) => ({ ...f, phone: e.target.value }))}
            />
            <input
              type="date"
              className="border border-slate-200 rounded-lg px-3 py-2"
              value={form.dob}
              onChange={(e) => setForm((f) => ({ ...f, dob: e.target.value }))}
            />
            <select
              className="border border-slate-200 rounded-lg px-3 py-2"
              value={form.gender}
              onChange={(e) => setForm((f) => ({ ...f, gender: e.target.value }))}
            >
              <option value="">Gender</option>
              <option value="male">Male</option>
              <option value="female">Female</option>
              <option value="other">Other</option>
            </select>
            <button className="col-span-2 bg-blue-600 text-white rounded-lg py-2 text-sm font-medium hover:bg-blue-700">
              Save patient
            </button>
          </form>
        )}

        <input
          className="w-full border border-slate-200 rounded-lg px-4 py-2 mb-4"
          placeholder="Search by name or phone..."
          value={q}
          onChange={(e) => setQ(e.target.value)}
        />

        {isLoading ? (
          <p className="text-slate-500">Loading...</p>
        ) : patients.length === 0 ? (
          <p className="text-slate-500">No patients yet.</p>
        ) : (
          <div className="bg-white border border-slate-200 rounded-lg divide-y divide-slate-100">
            {patients.map((p) => (
              <button
                key={p.id}
                onClick={() => navigate(`/patients/${p.id}`)}
                className="w-full flex items-center justify-between px-4 py-3 hover:bg-slate-50 text-left"
              >
                <span className="font-medium">{p.name}</span>
                <span className="text-sm text-slate-500">{p.phone ?? ""}</span>
              </button>
            ))}
          </div>
        )}
      </main>
    </div>
  );
}
