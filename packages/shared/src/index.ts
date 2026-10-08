export type SupportPillar =
  | 'protest-rights'
  | 'activism'
  | 'mental-health'
  | 'climate'
  | 'digital-rights'
  | 'governance'
  | 'defenders'
  | 'gender-rights'
  | 'mens-circle'
  | 'emergency';

export type Channel = 'web' | 'whatsapp';
export type Language = 'en' | 'fr';
export type ReplyMode = 'directory' | 'ai' | 'urgent' | 'human';
export type Triage = 'routine' | 'urgent';
export type CaseStatus = 'queued' | 'in_progress' | 'resolved';
export type CasePriority = 'normal' | 'critical';
export type KnowledgeStatus = 'pending' | 'published' | 'rejected';
export type Verification = 'verified' | 'stale' | 'unverified';
export type ReferralTrust = 'official' | 'community' | 'unverified';
export type ReferralChannel = 'phone' | 'website' | 'email' | 'in-person' | 'sms';

export interface ChatRequest {
  message: string;
  topic?: SupportPillar;
  region?: string;
  ai_consent: boolean;
  language?: Language;
}

export interface ChatResponse {
  reply: string;
  mode: ReplyMode;
  triage: Triage;
  referrals: Referral[];
  sources: KnowledgeEntry[];
  case_id: string | null;
}

export interface Referral {
  id: string;
  title: string;
  organisation: string;
  category: SupportPillar;
  region: string;
  regions: string[];
  phone: string | null;
  website: string;
  notes: string;
  hours: string;
  languages: string[];
  channels: ReferralChannel[];
  trust: ReferralTrust;
  verified_at: string | null;
  review_due: string | null;
  evidence: string | null;
  verification: Verification;
}

export interface KnowledgeEntry {
  id?: string;
  title: string;
  summary: string;
  category: SupportPillar;
  source: string;
  source_url: string;
  verified_at: string;
  status?: KnowledgeStatus;
}

export interface Message {
  id: number;
  role: 'user' | 'assistant' | 'human';
  content: string;
  created: number;
}

export interface Case {
  id: string;
  priority: CasePriority;
  status: CaseStatus;
  assignee: string | null;
  created: number;
  messages: Message[];
}

export interface AuditEntry {
  id: number;
  action: string;
  actor: string;
  resource: string | null;
  outcome: 'success' | 'denied' | 'not_found';
  detail: string | null;
  created: number;
}

export const SUPPORT_PILLARS = [
  { id: 'protest-rights', label: 'Protest Rights & Civic Freedom' },
  { id: 'activism', label: 'Activism & Youth-Led Movements' },
  { id: 'mental-health', label: 'Mental Health & Wellbeing' },
  { id: 'climate', label: 'Climate Justice & Environmental Rights' },
  { id: 'digital-rights', label: 'Digital Rights & Online Safety' },
  { id: 'governance', label: 'Youth Participation in Governance' },
  { id: 'defenders', label: 'Human Rights Defenders' },
  { id: 'gender-rights', label: 'Gender & Intersectional Justice' },
  { id: 'mens-circle', label: 'Men’s Circle' },
] as const;

export const REFERRAL_CHANNELS: ReferralChannel[] = [
  'phone',
  'website',
  'email',
  'in-person',
  'sms',
];

export const AUDIT_RETENTION_DAYS = 90;
export const SESSION_RETENTION_DAYS = 7;