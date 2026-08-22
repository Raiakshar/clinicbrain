export interface User {
  id: number;
  name: string;
  role: string;
  clinic_id: number;
}

export interface Patient {
  id: number;
  name: string;
  phone: string | null;
  dob: string | null;
  gender: string | null;
}

export type EventType = "visit" | "prescription" | "lab" | "document" | "note";

export interface TimelineEvent {
  id: number;
  type: EventType;
  event_date: string | null;
  payload: Record<string, unknown>;
  created_at: string;
}

export type DocStatus =
  | "pending"
  | "processing"
  | "needs_review"
  | "processed"
  | "failed";

export interface Extracted {
  document_type: string;
  event_date?: string | null;
  summary?: string;
  content_text?: string;
  labs?: LabDraftRow[] | null;
  lab_error?: string | null;
}

export interface LabDraftRow {
  test_name: string;
  value: string | number | null;
  unit?: string | null;
  ref_low?: string | number | null;
  ref_high?: string | number | null;
  taken_at?: string | null;
}

export interface Doc {
  id: number;
  patient_id: number;
  status: DocStatus;
  mime: string;
  error: string | null;
  ocr_text?: string | null;
  extracted: Extracted | null;
  created_at: string | null;
}

export interface SearchItem {
  source: string;
  id: number;
  patient_id: number;
  title: string;
}

export type LabFlag = "normal" | "high" | "low" | "review";

export interface PatientLab {
  test_name: string;
  value: number;
  unit: string | null;
  flag: LabFlag;
  taken_at: string | null;
  count: number;
}

export interface TrendPoint {
  value: number;
  flag: LabFlag;
  unit: string | null;
  ref_low: number | null;
  ref_high: number | null;
  taken_at: string;
}
