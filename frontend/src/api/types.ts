// Khớp các schema Pydantic ở product/apps/api/*/schemas.py

export type UUID = string;
export type Gender = "male" | "female" | "other";
export type MemberType = "self" | "spouse" | "child" | "parent" | "sibling" | "other_relative";
export type RecordKind = "condition" | "medication" | "allergy" | "lab_result";
export type EventType = "appointment" | "medication_reminder" | "follow_up";
export type EventSource = "manual" | "agent";

export interface User {
  id: UUID;
  email: string;
  display_name: string;
  last_name: string | null;
  first_name: string | null;
  date_of_birth: string | null;
  gender: Gender | null;
  phone: string | null;
}

export interface RegisterIn {
  email: string;
  password: string;
  last_name: string;
  first_name: string;
  date_of_birth?: string | null;
  gender?: Gender | null;
  phone?: string | null;
}

export interface FamilyMember {
  id: UUID;
  family_id: UUID;
  member_type: MemberType;
  display_name: string;
  dob: string | null;
  linked_user_id: UUID | null;
}

export interface Family {
  id: UUID;
  name: string;
}

export interface ChatMessage {
  id: UUID;
  role: "user" | "assistant";
  content: string;
  attachments: UUID[] | null;
}

export interface DocumentOut {
  id: UUID;
  mime_type: string;
  created_at: string;
  extracted_json: Record<string, unknown> | null;
}

export interface MedicalRecord {
  id: UUID;
  kind: RecordKind;
  payload: Record<string, unknown>;
  source_document_id: UUID | null;
  confirmed_at: string | null;
  created_at: string;
}

export interface CalendarEvent {
  id: UUID;
  type: EventType;
  title: string;
  starts_at: string;
  recurrence_rule: string | null;
  source: EventSource;
  confirmed_at: string | null;
  created_at: string;
}

export interface Occurrence {
  event_id: UUID;
  occurs_at: string;
  type: EventType;
  title: string;
  recurrence_rule: string | null;
  source: EventSource;
  confirmed: boolean;
}

export interface Dashboard {
  summary: {
    consultations_this_month: number;
    documents_total: number;
    upcoming_7d: number;
    pending_confirmations: number;
  };
  members: {
    id: UUID;
    display_name: string;
    member_type: MemberType;
    age: number | null;
    health_visible: boolean;
    confirmed_records: number | null;
    allergies: string[] | null;
    conditions: string[] | null;
  }[];
  timeline: { at: string; member_id: UUID; member_name: string; kind: "document_uploaded" | "record_confirmed"; label: string }[];
  upcoming: { at: string; member_id: UUID; member_name: string; title: string; type: EventType }[];
}
