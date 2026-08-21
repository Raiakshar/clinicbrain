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
