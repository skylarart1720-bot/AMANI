export type SupportPillar =
  | 'protest-rights'
  | 'activism'
  | 'mental-health'
  | 'climate'
  | 'digital-rights'
  | 'governance'
  | 'defenders-safety'
  | 'gender-rights'
  | 'mens-circle';

export type Channel = 'web' | 'whatsapp';

export interface ChatRequest {
  message: string;
  channel: Channel;
  region?: string;
  sessionId?: string;
}

export interface ChatResponse {
  reply: string;
  pillar: SupportPillar | 'emergency';
  triage: 'routine' | 'urgent' | 'priority-handoff';
  escalationNeeded: boolean;
  suggestions: string[];
}

export const SUPPORT_PILLARS = [
  { id: 'protest-rights', label: 'Protest Rights & Civic Freedom' },
  { id: 'activism', label: 'Activism & Youth-Led Movements' },
  { id: 'mental-health', label: 'Suicide Prevention & Youth Mental Health' },
  { id: 'climate', label: 'Climate Justice & Environmental Rights' },
  { id: 'digital-rights', label: 'Digital Rights, Online Safety & Freedom of Expression' },
  { id: 'governance', label: 'Youth Participation in Governance' },
  { id: 'defenders-safety', label: 'Human Rights Defenders Safety & Security' },
  { id: 'gender-rights', label: 'Gender, Intersectionality & Feminist Activism' },
  { id: 'mens-circle', label: 'Men’s Circle (Positive Masculinity Support)' },
] as const;
