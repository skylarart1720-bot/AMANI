"use client";

import { FormEvent, useCallback, useEffect, useRef, useState } from "react";
import Link from "next/link";
import { Language, languageOptions, localize, translate, useLanguage } from "./localization";
import {
  ArrowRight,
  ArrowUpRight,
  Check,
  ChevronRight,
  ExternalLink,
  HeartHandshake,
  LifeBuoy,
  Link2,
  LockKeyhole,
  LogOut,
  Menu,
  MessageCircle,
  Phone,
  Search,
  Send,
  ShieldCheck,
  Sparkles,
  Trash2,
  Users,
  X,
} from "lucide-react";

type Topic = {
  id: string;
  title: string;
  description: string;
  source: string;
  url: string;
};
type Referral = {
  id: string;
  title: string;
  organisation: string;
  category: string;
  region: string;
  regions: string[];
  phone?: string | null;
  website: string;
  notes: string;
  hours: string;
  languages: string[];
  channels: string[];
  trust: "official" | "community" | "unverified";
  verified_at?: string | null;
  review_due?: string | null;
  evidence?: string | null;
  verification: "verified" | "stale" | "unverified";
};
type Message = { id: number; role: string; content: string; created: number };
type Status = { ai_configured: boolean; scanner_configured: boolean; whatsapp_configured: boolean; whatsapp_url: string | null };
type OnlineStaff = {id: string; label: string; role: string; online: boolean};
type Verdict = {
  verdict: string;
  reasons: string[];
  providers: { provider: string; status: string }[];
  checked_at: string;
};
const tabs = [
  { id: "chat", label: "Get support", icon: MessageCircle },
  { id: "topics", label: "Support topics", icon: HeartHandshake },
  { id: "directory", label: "Find help", icon: Users },
  { id: "links", label: "Check a link", icon: ShieldCheck },
  { id: "whatsapp", label: "WhatsApp", icon: MessageCircle },
  { id: 'reviews', label: 'Reviews', icon: HeartHandshake },
];

export default function Page() {
  const {language, setLanguage, coverage} = useLanguage();
  const [translations, setTranslations] = useState<Record<number, {language: string; text: string}>>({});
  const [translating, setTranslating] = useState<number | null>(null);
  useEffect(() => setTranslations({}), [language]);
  const [sessionToken, setSessionToken] = useState("");
  useEffect(() => setTranslations({}), [sessionToken]);
  const [tab, setTab] = useState("chat");
  const [menu, setMenu] = useState(false);
  const [topics, setTopics] = useState<Topic[]>([]);
  const [referrals, setReferrals] = useState<Referral[]>([]);
  const [status, setStatus] = useState<Status | null>(null);
  const [online, setOnline] = useState(false);
  const [onlineStaff, setOnlineStaff] = useState<OnlineStaff[]>([]);
  const [choosingStaff, setChoosingStaff] = useState(false);
  const [staffLoading, setStaffLoading] = useState(false);
  const [staffError, setStaffError] = useState("");
  const [topic, setTopic] = useState("");
  const [query, setQuery] = useState("");
  const [region, setRegion] = useState("all");
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [service, setService] = useState({hours:'Support hours have not yet been published.',response:'Response times are not guaranteed.'});
  const [rating, setRating] = useState('5');
  const [feedbackComment, setFeedbackComment] = useState('');
  const [feedbackConsent, setFeedbackConsent] = useState(false);
  const [publicConsent, setPublicConsent] = useState(false);
  const [reviews, setReviews] = useState<{total:number;average_rating:number|null;reviews:{rating:number;comment:string;published_at:number}[]}>({total:0,average_rating:null,reviews:[]});
  const [reviewsLoading,setReviewsLoading] = useState(false);
  const [reviewsError,setReviewsError] = useState('');
  const [aiConsent, setAiConsent] = useState(false);
  const [caseInfo, setCaseInfo] = useState<{
    id: string;
    status: string;
    assignee?: string | null;
    feedback_submitted?: boolean;
    events?: {id:number; kind:string; target:string|null; created:number}[];
  } | null>(null);
  const [related, setRelated] = useState<Referral[]>([]);
  const [url, setUrl] = useState("");
  const [urlConsent, setUrlConsent] = useState(false);
  const [checking, setChecking] = useState(false);
  const [verdict, setVerdict] = useState<Verdict | null>(null);
  const [privacy, setPrivacy] = useState(false);
  const [confirmDelete, setConfirmDelete] = useState(false);
  const token = useRef("");
  const end = useRef<HTMLDivElement>(null);
  const generation = useRef(0);

  const api = useCallback(
    async (path: string, method = "GET", body?: unknown) => {
      const response = await fetch(`/api/support/${path}`, {
        method,
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token.current}`,
        },
        body: body === undefined ? undefined : JSON.stringify(body),
        signal: AbortSignal.timeout(40000),
      });
      const data = await response.json();
      if (response.status === 401) {
        token.current = '';
        setSessionToken('');
        sessionStorage.removeItem('amani-session');
        setMessages([]);
        setCaseInfo(null);
        if (path === 'sessions' && method === 'DELETE') return { deleted: true };
      }
      if (!response.ok)
        throw new Error(
          typeof data.detail === "string"
            ? data.detail
            : "The request could not be completed.",
        );
      return data;
    },
    [],
  );

  const refreshMessages = useCallback(async () => {
    if (!token.current) return;
    const current = generation.current;
    const data = await api("messages");
    if (current === generation.current) {
      setMessages(data.messages);
      setCaseInfo(data.case);
    }
  }, [api]);

  useEffect(() => {
    token.current = sessionStorage.getItem("amani-session") || "";
    setSessionToken(token.current);
    const load = async () => {
      try {
        const data = await api("directory");
        setTopics(data.topics);
        setReferrals(data.referrals);
      } catch {
        setError("The directory could not be loaded. Please refresh to retry.");
      }
    };
    const ping = async () => {
      try {
        setStatus(await api("status"));
        setOnline(true);
      } catch {
        setOnline(false);
      }
    };
    void load();
    void ping();
    void refreshMessages().catch(() => {
      token.current = "";
      sessionStorage.removeItem("amani-session");
    });
    const timer = setInterval(() => {
      void ping();
      if (!document.hidden) void refreshMessages().catch(() => {});
    }, 10000);
    return () => clearInterval(timer);
  }, [api, refreshMessages]);
  useEffect(() => {
    let active = true;
    const loadStaff = async () => {
      try {
        const result = await api("staff");
        if (active) { setOnlineStaff(result.staff); setStaffError(""); }
      } catch {
        if (active) { setOnlineStaff([]); setStaffError("Online availability could not be checked. Please retry."); }
      }
    };
    void loadStaff();
    const timer = setInterval(() => void loadStaff(), 10000);
    return () => { active = false; clearInterval(timer); };
  }, [api]);
  useEffect(() => {void api('service-settings').then(setService).catch(() => {});},[api]);
  useEffect(() => {setFeedbackComment(''); setFeedbackConsent(false);setPublicConsent(false);},[caseInfo?.id,sessionToken]);
  useEffect(() => {
    if(tab!=='reviews') return;
    let current=true;setReviewsLoading(true);setReviewsError('');
    void api('reviews').then((data) => {if(current)setReviews(data);}).catch((e) => {if(current)setReviewsError(e.message);}).finally(() => {if(current)setReviewsLoading(false);});
    return () => {current=false;};
  },[tab,api]);
  useEffect(() => {
    if (!sessionToken) return;
    const controller = new AbortController();
    const current = generation.current;
    const listen = async () => {
      while (!controller.signal.aborted) {
        try {
          const response = await fetch("/api/support/events", {
            headers: { Authorization: `Bearer ${sessionToken}` },
            signal: controller.signal,
          });
          if (!response.ok || !response.body) return;
          const reader = response.body.getReader();
          const decoder = new TextDecoder();
          let buffer = "";
          while (true) {
            const { done, value } = await reader.read();
            if (done) break;
            buffer += decoder.decode(value, { stream: true });
            let split;
            while ((split = buffer.indexOf("\n\n")) !== -1) {
              const event = buffer.slice(0, split);
              buffer = buffer.slice(split + 2);
              if (event.startsWith("event: expired")) return;
              const line = event
                .split("\n")
                .find((item) => item.startsWith("data: "));
              if (line && current === generation.current) {
                const data = JSON.parse(line.slice(6));
                setMessages(data.messages);
                setCaseInfo(data.case);
              }
            }
          }
        } catch {
          /* Reconnect after transient network failures. */
        }
        if (!controller.signal.aborted)
          await new Promise((resolve) => setTimeout(resolve, 3000));
      }
    };
    void listen();
    return () => controller.abort();
  }, [sessionToken]);
  useEffect(() => {
    if (!privacy && !confirmDelete) return;
    const previous = document.activeElement as HTMLElement | null;
    const trap = (event: KeyboardEvent) => {
      if (event.key === "Escape") {
        setPrivacy(false);
        setConfirmDelete(false);
      }
      if (event.key !== "Tab") return;
      const controls = Array.from(
        document.querySelectorAll<HTMLElement>(
          ".modal button, .modal a, .modal input",
        ),
      );
      const first = controls[0],
        last = controls[controls.length - 1];
      if (event.shiftKey && document.activeElement === first) {
        event.preventDefault();
        last?.focus();
      } else if (!event.shiftKey && document.activeElement === last) {
        event.preventDefault();
        first?.focus();
      }
    };
    document.addEventListener("keydown", trap);
    return () => {
      document.removeEventListener("keydown", trap);
      previous?.focus();
    };
  }, [privacy, confirmDelete]);
  useEffect(() => {
    end.current?.scrollIntoView({ behavior: "smooth", block: "nearest" });
  }, [messages.length, busy]);

  const ensureSession = async () => {
    if (!token.current) {
      const current = generation.current;
      const data = await api("sessions", "POST");
      if (current !== generation.current) {
        await fetch("/api/support/sessions", {
          method: "DELETE",
          headers: { Authorization: `Bearer ${data.token}` },
        });
        throw new Error("Conversation cancelled.");
      }
      token.current = data.token;
      setSessionToken(data.token);
      sessionStorage.setItem("amani-session", data.token);
    }
  };
  const send = async (event: FormEvent) => {
    event.preventDefault();
    if (!input.trim() || busy) return;
    setBusy(true);
    setError("");
    setNotice("");
    const current = generation.current;
    try {
      await ensureSession();
      const data = await api("chat", "POST", {
        message: input.trim(),
        topic: topic || null,
        ai_consent: aiConsent,
        language,
      });
      if (current !== generation.current) return;
      setInput("");
      setRelated(data.referrals);
      await refreshMessages();
      setNotice(
        data.mode === "ai"
          ? "AI response with directory references"
          : data.mode === "urgent"
            ? "Priority support resources"
            : data.mode === "human" ? "Message sent to human support." : "Directory response",
      );
    } catch (e) {
      if (current === generation.current) setError((e as Error).message);
    } finally {
      if (current === generation.current) setBusy(false);
    }
  };
  const handoff = async (staffId?: string) => {
    setError("");
    setBusy(true);
    try {
      await ensureSession();
      const data = await api("handoff", "POST", {staff_id: staffId || null});
      setCaseInfo(data);
      setChoosingStaff(false);
      setNotice(data.message);
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  };
  const requestHuman = async () => {
    setChoosingStaff(true); setStaffLoading(true); setStaffError("");
    try {
      const data = await api("staff"); setOnlineStaff(data.staff);
    } catch {
      setOnlineStaff([]); setStaffError("Online availability could not be checked. Please retry.");
    } finally { setStaffLoading(false); }
  };
  const clear = async () => {
    setError("");
    try {
      generation.current += 1;
      if (token.current) await api("sessions", "DELETE");
      token.current = "";
      setSessionToken("");
      sessionStorage.removeItem("amani-session");
      setMessages([]);
      setCaseInfo(null);
      setRelated([]);
      setInput("");
      setBusy(false);
      setConfirmDelete(false);
      setNotice("Your conversation has been deleted from this service.");
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  };
  const quickExit = () => {
    if (token.current)
      void fetch("/api/support/sessions", {
        method: "DELETE",
        headers: { Authorization: `Bearer ${token.current}` },
        keepalive: true,
      });
    sessionStorage.removeItem("amani-session");
    token.current = "";
    window.location.replace("https://www.google.com");
  };
  const checkLink = async (event: FormEvent) => {
    event.preventDefault();
    setChecking(true);
    setVerdict(null);
    setError("");
    try {
      for (let attempt = 0; attempt < 6; attempt++) {
        const result = await api("check-link", "POST", {
          url: url.trim(),
          consent: urlConsent,
        });
        setVerdict(result);
        if (!result.providers.some((provider: { status: string }) => provider.status === "pending") || attempt === 5) break;
        await new Promise((resolve) => setTimeout(resolve, 20000));
      }
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setChecking(false);
    }
  };
  const navigate = (id: string) => {
    setTab(id);
    setMenu(false);
    setError("");
    setNotice("");
  };
  const filtered = referrals.filter(
    (r) =>
      (region === "all" || r.regions.includes(region)) &&
      `${translate(r.title, language)} ${r.organisation} ${translate(r.notes, language)} ${r.languages.join(" ")}`
        .toLowerCase()
        .includes(query.toLowerCase()),
  );

  const areas = [
    "all",
    ...Array.from(new Set(referrals.flatMap((r) => r.regions))).sort(),
  ];

  const referralItem = (r: Referral) => (
    <article className="referral" key={r.id}>
      <div className="referral-meta">
        <span>{r.regions.join(", ")}</span>
        <span>{r.hours}</span>
      </div>
      <h3 data-original-text>{r.organisation}</h3>
      <p>{r.notes}</p>
      <div className="referral-meta">
        {r.languages.slice(0, 3).map((item) => (
          <span key={item}>{item}</span>
        ))}
        {r.channels.includes("email") && <span>Email</span>}
      </div>
      <div className="referral-actions">
        {r.phone && (
          <a className="button primary small" href={`tel:${r.phone}`}>
            <Phone size={15} /> {r.phone}
          </a>
        )}
        <a
          href={r.website}
          target="_blank"
          rel="noopener noreferrer"
          className="text-link"
        >
          Official website <ArrowUpRight size={16} />
        </a>
      </div>
      <small>
        {r.verification === "verified" && r.verified_at
          ? `Contact checked ${r.verified_at}`
          : r.verification === "stale"
            ? `Last checked ${r.verified_at}. Needs re-checking before you rely on it.`
            : "Contact details need confirmation with the organisation"}
      </small>
    </article>
  );

  return localize(
    <div className="app-shell">
      <a className="skip-link" href="#main">
        Skip to content
      </a>
      <header className="topbar">
        <Link className="brand" href="/" aria-label="AMANI home">
          <span className="brand-mark">
            <HeartHandshake size={27} strokeWidth={1.8} />
          </span>
          <span>
            AMANI
            <small>RIGHTS & WELLBEING</small>
          </span>
        </Link>
        <div className="top-actions">
          <label className="language-control">
            <span className="sr-only">Language / Langue</span>
            <select
              aria-label="Language / Langue"
              value={language}
              onChange={(e) => {
                const value = e.target.value as Language;
                setLanguage(value);
                localStorage.setItem("amani-language", value);
              }}
            >
              {languageOptions.map((item) => <option key={item.code} value={item.code} data-original-text>{item.native}</option>)}
            </select>
          </label>
          <span className="location">
            Ghana <span className="ghana-flag" aria-label="Ghana flag" />
          </span>
          <button className="exit" onClick={quickExit}>
            Quick exit <LogOut size={16} />
          </button>
          <button
            className="icon-button mobile-menu"
            title="Toggle navigation"
            aria-expanded={menu}
            onClick={() => setMenu(!menu)}
          >
            {menu ? <X /> : <Menu />}
          </button>
        </div>
      </header>
      <div className="workspace">
        <aside className={`sidebar ${menu ? "is-open" : ""}`}>
          <div className="sidebar-label">YOUR SUPPORT SPACE</div>
          <nav aria-label="Main navigation">
            {tabs.map((t) => (
              <button
                key={t.id}
                className={tab === t.id ? "nav-item active" : "nav-item"}
                onClick={() => navigate(t.id)}
                aria-current={tab === t.id ? "page" : undefined}
              >
                <t.icon size={20} />
                {t.label}
                {tab === t.id && <ChevronRight size={15} />}
              </button>
            ))}
          </nav>
          <div className="sidebar-bottom">
            <div className="privacy-note">
              <LockKeyhole size={19} />
              <div>
                <strong>No name needed.</strong>
                <p>You decide what to share.</p>
              </div>
            </div>
            <button className="subtle" onClick={() => setPrivacy(true)}>
              Privacy & your data <ArrowUpRight size={14} />
            </button>
            <button className="subtle" onClick={() => setConfirmDelete(true)}>
              <Trash2 size={15} /> Delete conversation
            </button>
            <div className="sidebar-footer">
              Independent support information.
              <br />
              Not an emergency service.
            </div>
          </div>
        </aside>
        <main id="main" className="main-content">
          <div className="emergency-strip">
            <LifeBuoy size={17} />
            <span>In immediate danger in Ghana?</span>
            <a href="tel:112">
              Call 112 <ArrowUpRight size={15} />
            </a>
          </div>
          <div className="page-heading">
            <div>
              <p className="eyebrow">A LITTLE SUPPORT. A WAY FORWARD.</p>
              <h1>
                {tab === "chat"
                  ? "You can start here."
                  : tab === "topics"
                    ? "Support for what matters."
                    : tab === "directory"
                      ? "Find your next point of support."
                      : tab === "whatsapp" ? "Support on WhatsApp."
                      : "Pause. Check the link."}
              </h1>
              <p>
                {tab === "chat"
                  ? "A space to talk about your rights, safety and wellbeing."
                  : tab === "topics"
                    ? "Nine pathways. Your questions are welcome in all of them."
                    : tab === "directory"
                      ? "Connect with organisations in Ghana and beyond."
                      : tab === "whatsapp" ? "Another way to stay connected with AMANI."
                      : "Look up a suspicious URL without opening it."}
              </p>
            </div>
            <span className={`service-status ${online ? "online" : ""}`}>
              <span />
              {online ? "Support service connected" : "Connecting to support"}
            </span>
          </div>
          <section className="language-banner" aria-label="Multilingual support">
            <div><strong>Multilingual support</strong><p>Choose your language for the interface and new AI replies.</p></div>
            {language !== "en" && <p role="status">{coverage.status === "generating" ? "Preparing translations…" : coverage.status !== "complete" ? "Some text remains in English. Full translation is unavailable right now." : "Translation wording needs native-speaker review."}</p>}
          </section>
          {error && (
            <div className="alert error" role="alert">
              {error}
              <button
                className="icon-button"
                title="Dismiss error"
                onClick={() => setError("")}
              >
                <X size={16} />
              </button>
            </div>
          )}
          {notice && (
            <div className="alert" role="status">
              {notice}
            </div>
          )}
          {tab === "chat" && (
            <>
            <section className="online-support" aria-label="Online human support">
              <div><p className="eyebrow">HUMAN SUPPORT</p><h2>Choose someone to talk to</h2><p>Online staff appear below. Your conversation stays here.</p></div>
              <p><strong>Support hours</strong>: <span data-original-text>{service.hours}</span></p><p data-original-text>{service.response}</p>
              {staffError ? <p role="status">{staffError}</p> : staffLoading ? <p>Checking availability...</p> : onlineStaff.length ? <div className="online-staff-list">{onlineStaff.map((person) => <button className="online-person" key={person.id} onClick={() => void handoff(person.id)} disabled={busy}><span className="presence-dot online" /><span><strong data-original-text={person.role !== "super_admin"}>{person.label}</strong><small>Online · {person.role === "super_admin" ? "Super Admin" : "Staff"}</small></span><ArrowRight size={16} /></button>)}</div> : <p className="muted">No support staff are online right now. You can still join the general queue.</p>}
              {choosingStaff && <div className="human-choice"><p><strong>Support hours</strong>: <span data-original-text>{service.hours}</span></p><p data-original-text>{service.response}</p><p>This is not an emergency service. In Ghana, call 112 for immediate danger.</p><p>Select an online person above, or leave your request in the general queue.</p><button className="button secondary" disabled={busy} onClick={() => void handoff()}>Join general queue</button><button className="text-link" onClick={() => setChoosingStaff(false)}>Cancel</button></div>}
            </section>
            <div className="support-layout">
              <section className="chat-tool" aria-label="Support conversation">
                <div className="chat-header">
                  <span className="assistant-icon">
                    <Sparkles size={21} />
                  </span>
                  <div>
                    <h2>Amani support</h2>
                    <p>
                      {status?.ai_configured
                        ? "AI configured | consent required"
                        : "Directory support | AI unavailable"}
                    </p>
                  </div>
                  <button
                    className="icon-button"
                    title="Delete conversation"
                    onClick={() => setConfirmDelete(true)}
                  >
                    <Trash2 size={18} />
                  </button>
                </div>
                <div
                  className="chat-messages"
                  role="log"
                  aria-live="polite"
                  aria-relevant="additions text"
                >
                  <div className="welcome">
                    <span className="welcome-symbol">
                      <HeartHandshake size={34} />
                    </span>
                    <h3>
                      Whatever brings you here,
                      <br />
                      you deserve to be heard.
                    </h3>
                    <p>
                      I am Amani, an AI-enabled information assistant. I can
                      help you find support, but I am not a lawyer, doctor or
                      counsellor.
                    </p>
                    <p>
                      You do not need to share your name, phone number or
                      address.
                    </p>
                  </div>
                  {messages.length === 0 && (
                    <div className="starter-options">
                      {[
                        "I need wellbeing support",
                        "I have an online safety concern",
                        "I want to understand my rights",
                      ].map((text) => (
                        <button key={text} onClick={() => setInput(translate(text, language))}>
                          {text}
                          <ArrowRight size={16} />
                        </button>
                      ))}
                    </div>
                  )}
                  {messages.map((m) => (
                    <div key={m.id} className={`message ${m.role}`}>
                      <span className="message-label">
                        {m.role === "user"
                          ? "You"
                          : m.role === "human"
                            ? "Human moderator"
                            : "Amani"}
                      </span>
                      <p data-original-text>{m.content}</p>
                      {m.role !== "user" && <div className="message-tools">
                        <button disabled={!aiConsent || translating !== null} title={!aiConsent ? "AI consent is required to translate a reply." : "Translate reply"} onClick={async () => {
                          setTranslating(m.id); setError("");
                          try { const currentGeneration = generation.current; const result = await api("translate", "POST", {message_id: m.id, language, ai_consent: aiConsent}); if (currentGeneration === generation.current) setTranslations((old) => ({...old, [m.id]: {language, text: result.translation}})); }
                          catch (e) { setError((e as Error).message); }
                          finally { setTranslating(null); }
                        }}>Translate reply</button>
                        {translations[m.id]?.language === language && <div className="translated-reply"><small>Automatic translation can make mistakes. Verify important information with the service.</small><p data-original-text dir="auto">{translations[m.id].text}</p></div>}
                      </div>}
                      <time>
                        {new Date(m.created * 1000).toLocaleTimeString([], {
                          hour: "2-digit",
                          minute: "2-digit",
                        })}
                      </time>
                    </div>
                  ))}
                  {busy && (
                    <p className="working" role="status">
                      Working on your request...
                    </p>
                  )}
                  <div ref={end} />
                </div>
                {caseInfo && (
                  <div className="case-status">
                    <Users size={16} />
                    <span>
                      Human support request {caseInfo.id}:{" "}
                      {caseInfo.status.replace("_", " ")}{caseInfo.assignee ? ` · ${caseInfo.assignee === "super-admin" ? "Super Admin" : caseInfo.assignee}` : ""}. Response time is not
                      guaranteed.
                    </span>
                  </div>
                )}
                {caseInfo?.events?.length ? <div className="case-notices" aria-live="polite">{caseInfo.events.slice(-5).map((event) => <p key={event.id}>
                  {event.kind === 'transferred' ? <>Your request was transferred to <span data-original-text>{event.target === 'super-admin' ? 'Super Admin' : event.target || 'General queue'}</span>.</> : event.kind === 'resolved' ? 'Your support request has been resolved.' : event.kind === 'queued' ? 'Your support request is waiting in the queue.' : 'Your support request is in progress.'}
                </p>)}</div> : null}
                {caseInfo?.status === 'resolved' && <section className="feedback-panel">
                  <h3>How was your human support?</h3>
                  {caseInfo.feedback_submitted ? <p role="status">Thank you. Your feedback has been submitted.</p> : <form onSubmit={(e) => {e.preventDefault(); const current=generation.current; const caseId=caseInfo.id; setBusy(true); void api(`cases/${caseId}/feedback`,'POST',{rating:Number(rating),comment:feedbackComment,consent:feedbackConsent,public_consent:publicConsent}).then(async () => {if(current===generation.current){setFeedbackComment('');setFeedbackConsent(false);setPublicConsent(false);await refreshMessages();}}).catch((e) => {if(current===generation.current)setError(e.message);}).finally(() => setBusy(false));}}>
                    <p>Optional feedback is shared with Super Admin. Please avoid names or sensitive details. Deleting this conversation also removes its feedback from the active service.</p>
                    <label>Support rating<select aria-label="Support rating" value={rating} onChange={(e) => setRating(e.target.value)}><option value="5">5 — Very helpful</option><option value="4">4 — Helpful</option><option value="3">3 — Neutral</option><option value="2">2 — Unhelpful</option><option value="1">1 — Very unhelpful</option></select></label>
                    <label>Optional feedback comment<textarea maxLength={2000} value={feedbackComment} onChange={(e) => setFeedbackComment(e.target.value)} /></label>
                    <label><input type="checkbox" checked={feedbackConsent} onChange={(e) => setFeedbackConsent(e.target.checked)} />I agree to share this rating and comment with Super Admin.</label>
                    <label><input type="checkbox" checked={publicConsent} onChange={(e) => setPublicConsent(e.target.checked)} />I also allow Super Admin to publish my rating and an anonymous excerpt of my comment on the public Reviews page.</label>
                    <p>Public sharing is optional. Staff review comments for privacy. Your rating is never changed. Deleting your conversation removes its published review from this service.</p>
                    <button className="button secondary" disabled={busy || !feedbackConsent}>Submit feedback</button>
                  </form>}
                </section>}
                <div className="composer-area">
                  <label className="topic-select">
                    Topic{" "}
                    <select
                      aria-label="Conversation topic"
                      value={topic}
                      onChange={(e) => setTopic(e.target.value)}
                    >
                      <option value="">Let Amani help me find it</option>
                      {topics.map((t) => (
                        <option key={t.id} value={t.id}>
                          {t.title}
                        </option>
                      ))}
                    </select>
                  </label>
                  <label className="consent">
                    <input
                      type="checkbox"
                      checked={aiConsent}
                      onChange={(e) => setAiConsent(e.target.checked)}
                      disabled={!status?.ai_configured}
                    />
                    <span>
                      Use AI replies. My recent messages will be sent to the AI
                      provider.
                    </span>
                  </label>
                  <form onSubmit={send} className="composer">
                    <textarea
                      aria-label="Your message"
                      placeholder="What's on your mind?"
                      value={input}
                      onChange={(e) => setInput(e.target.value)}
                      maxLength={4000}
                      rows={2}
                      onKeyDown={(e) => {
                        if (e.key === "Enter" && !e.shiftKey) {
                          e.preventDefault();
                          if (input.trim() && !busy)
                            e.currentTarget.form?.requestSubmit();
                        }
                      }}
                    />
                    <button
                      type="submit"
                      className="send-button"
                      title="Send message"
                      disabled={busy || !input.trim()}
                    >
                      <Send size={19} />
                    </button>
                  </form>
                  <p className="composer-foot">
                    <LockKeyhole size={12} /> Encrypted storage. Deleted after 7
                    days or when you delete your chat.
                  </p>
                </div>
              </section>
              <aside className="support-aside">
                <div className="aside-section">
                  <p className="eyebrow">A HUMAN CONNECTION</p>
                  <h2>Some things are better talked through.</h2>
                  <p>
                    You can request a moderator. Messages stay in this
                    conversation; you do not need to provide contact details.
                  </p>
                  <button
                    className="button secondary"
                    onClick={() => { void requestHuman(); document.querySelector(".online-support")?.scrollIntoView({behavior: "smooth", block: "start"}); }}
                    disabled={busy}
                  >
                    <Users size={17} /> Request human support
                  </button>
                  <small>
                    Choose an online person above or join the general queue.
                  </small>
                </div>
                <div className="aside-section"><p className="eyebrow">WHATSAPP</p><h3>Stay connected on WhatsApp</h3><p>{status?.whatsapp_url ? "Open a conversation with AMANI on WhatsApp." : "WhatsApp setup is pending. Web support is available here."}</p>{status?.whatsapp_url ? <a className="button primary whatsapp-chat" href={status.whatsapp_url} target="_blank" rel="noopener noreferrer"><MessageCircle size={18} /> Chat on WhatsApp <ArrowUpRight size={16} /></a> : <button className="button primary whatsapp-chat" onClick={() => navigate("whatsapp")}><MessageCircle size={18} /> Chat on WhatsApp <ArrowRight size={16} /></button>}</div>
                <div className="aside-section">
                  <p className="eyebrow">DIRECT SUPPORT</p>
                  {related.length ? (
                    related.map(referralItem)
                  ) : (
                    <>
                      <h3>Find the right organisation.</h3>
                      <p>
                        Explore official contact channels for rights, wellbeing
                        and safety support.
                      </p>
                      <button
                        className="text-link"
                        onClick={() => navigate("directory")}
                      >
                        Open support directory <ArrowRight size={16} />
                      </button>
                    </>
                  )}
                </div>
                <div className="aside-section link-prompt">
                  <ShieldCheck size={24} />
                  <h3>Not sure about a link?</h3>
                  <p>Check its reputation before sharing information.</p>
                  <button
                    className="text-link"
                    onClick={() => navigate("links")}
                  >
                    Check a link <ArrowRight size={16} />
                  </button>
                </div>
              </aside>
            </div>
            </>
          )}
          {tab === 'reviews' && <section className="reviews-panel">
            <p className="eyebrow">VISITOR EXPERIENCES</p><h1>Reviews</h1>
            <p>Anonymous feedback from completed human-support cases. Visitors opt in to public sharing; Super Admin selects reviews for publication and may remove private details by publishing an excerpt.</p>
            <p>These are selected published reviews, not all feedback received. Ratings are shown unchanged.</p>
            {reviewsLoading ? <p role="status">Loading reviews...</p> : reviewsError ? <p role="alert">{reviewsError}</p> : <>
              <div className="review-summary"><strong>{reviews.average_rating?.toFixed(1) ?? '—'} / 5</strong><span>{reviews.total} published reviews</span></div>
              {!reviews.total && <p>No public reviews yet. Consented reviews will appear here after publication.</p>}
              <div className="review-grid">{reviews.reviews.map((review,index) => <article className="review-card" key={index}>
                <strong>Anonymous visitor</strong><p aria-label={`${review.rating} out of 5`}>{'★'.repeat(review.rating)}{'☆'.repeat(5-review.rating)} · {review.rating} / 5</p>
                {review.comment && <blockquote data-original-text dir="auto">{review.comment}</blockquote>}
                <small>Published {new Date(review.published_at*1000).toLocaleDateString()}</small>
              </article>)}</div>
              {reviews.total > reviews.reviews.length && <p>Showing the latest 50 published reviews.</p>}
            </>}
          </section>}
          {tab === "whatsapp" && <section className="whatsapp-panel">
            <MessageCircle size={38} /><h2>AMANI on WhatsApp</h2>
            <span className={`channel-status ${status?.whatsapp_url ? "ready" : "pending"}`}>{status?.whatsapp_url ? "Available" : "Setup pending"}</span>
            <p>Chat with AMANI from WhatsApp. Meta receives your phone number; you can continue using anonymous web support instead.</p>
            {status?.whatsapp_url ? <a className="button primary whatsapp-chat" href={status.whatsapp_url} target="_blank" rel="noopener noreferrer">Chat on WhatsApp <ArrowUpRight size={17} /></a> : <p>The public WhatsApp business number has not been configured. Web support is available here.</p>}
            {status?.whatsapp_configured ? <p>When connected, use <strong data-original-text>human</strong> to request support, <strong data-original-text>updates</strong> to collect human replies, and <strong data-original-text>forget</strong> to delete your AMANI conversation. AI replies require opt-in.</p> : <p>Automated WhatsApp support is awaiting setup. A configured chat link can still open the business conversation.</p>}
            <button className="button secondary" onClick={() => navigate("chat")}>Continue with web support</button>
          </section>}
          {tab === "topics" && (
            <div className="topic-grid">
              {topics.map((t, i) => (
                <article className="topic-item" key={t.id}>
                  <span className="topic-number">
                    {String(i + 1).padStart(2, "0")}
                  </span>
                  <h2>{t.title}</h2>
                  <p>{t.description}</p>
                  <p className="source-name">{t.source}</p>
                  <div className="referral-actions">
                    <button
                      className="text-link"
                      onClick={() => {
                        setTopic(t.id);
                        navigate("chat");
                        setInput(
                          translate("I would like support with {topic}.", language).replace("{topic}", translate(t.title, language)),
                        );
                      }}
                    >
                      Talk about this <ArrowRight size={16} />
                    </button>
                    <a
                      href={t.url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="icon-button"
                      title={`Visit ${t.source}`}
                    >
                      <ExternalLink size={17} />
                    </a>
                  </div>
                </article>
              ))}
            </div>
          )}
          {tab === "directory" && (
            <section>
              <div className="directory-filters">
                <label className="search-input">
                  <Search size={19} />
                  <input
                    aria-label="Search organisations"
                    placeholder="Search by topic or organisation"
                    value={query}
                    onChange={(e) => setQuery(e.target.value)}
                  />
                </label>
                <select
                  aria-label="Coverage area"
                  value={region}
                  onChange={(e) => setRegion(e.target.value)}
                >
                  {areas.map((option) => (
                    <option key={option} value={option}>
                      {option === "all" ? "All coverage areas" : option}
                    </option>
                  ))}
                </select>
              </div>
              <p className="results-count">
                {filtered.length} organisations | Confirm availability directly.
                Listings do not imply a partnership.
              </p>
              <div className="directory-grid">{filtered.map(referralItem)}</div>
              {!filtered.length && (
                <p className="empty-state">
                  No organisations match this search. Try a broader term.
                </p>
              )}
            </section>
          )}
          {tab === "links" && (
            <section className="link-layout">
              <div className="link-tool">
                <span className="large-icon">
                  <ShieldCheck size={36} />
                </span>
                <h2>Check a suspicious link</h2>
                <p>
                  Reputation checks can identify known threats. A result with no
                  detections is never a guarantee of safety.
                </p>
                <form onSubmit={checkLink}>
                  <label className="field-label" htmlFor="url">
                    Website URL
                  </label>
                  <div className="url-input">
                    <Link2 size={19} />
                    <input
                      id="url"
                      type="url"
                      required
                      maxLength={4096}
                      placeholder="https://example.com"
                      value={url}
                      onChange={(e) => setUrl(e.target.value)}
                    />
                  </div>
                  <label className="consent">
                    <input
                      type="checkbox"
                      checked={urlConsent}
                      onChange={(e) => setUrlConsent(e.target.checked)}
                    />
                    <span>
                      I agree to share this URL with the configured reputation
                      providers for lookup and fresh scanning. Reports may be public.
                      I have removed private tokens and personal information.
                    </span>
                  </label>
                  <button
                    className="button primary"
                    disabled={checking || !urlConsent || !url.trim()}
                  >
                    <Search size={17} />
                    {checking ? "Checking reputation..." : "Check link"}
                  </button>
                </form>
                {!status?.scanner_configured && (
                  <p className="service-note">
                    Live reputation providers are not configured. Checks will
                    return an unknown result.
                  </p>
                )}
                {verdict && (
                  <div className={`verdict ${verdict.verdict}`} role="status">
                    <h3>
                      {verdict.verdict === "flagged"
                        ? "Threat reported"
                        : verdict.verdict === "no_known_threats"
                          ? "No known threats reported"
                          : verdict.providers.some((p) => p.status === "pending")
                            ? "Fresh analysis in progress"
                            : "Unable to verify this link"}
                    </h3>
                    {verdict.reasons.map((r) => (
                      <p key={r}>{r}</p>
                    ))}
                    {verdict.providers.map((p) => (
                      <p key={p.provider}>
                        {p.provider}: {p.status.replaceAll("_", " ")}
                      </p>
                    ))}
                    <small>
                      Checked {new Date(verdict.checked_at).toLocaleString()}
                    </small>
                  </div>
                )}
              </div>
              <aside className="support-aside">
                <div className="aside-section">
                  <p className="eyebrow">SOMETHING FEELS WRONG?</p>
                  <h2>Report a cyber incident.</h2>
                  <p>
                    Ghana's Cyber Security Authority provides an official
                    incident reporting channel.
                  </p>
                  <a className="button secondary" href="tel:292">
                    <Phone size={17} /> Call 292
                  </a>
                  <a
                    className="text-link"
                    href="https://csa.gov.gh/report"
                    target="_blank"
                    rel="noopener noreferrer"
                  >
                    Official reporting page <ArrowUpRight size={16} />
                  </a>
                </div>
              </aside>
            </section>
          )}
          <footer className="page-footer">
            <span>
              AMANI <span className="footer-dot">/</span> Rights. Safety.
              Wellbeing.
            </span>
            <button onClick={() => setPrivacy(true)}>
              Privacy & safeguarding
            </button>
          </footer>
        </main>
      </div>
      {(privacy || confirmDelete) && (
        <div
          className="modal-backdrop"
          onClick={() => {
            setPrivacy(false);
            setConfirmDelete(false);
          }}
        >
          <section
            className="modal"
            role="dialog"
            aria-modal="true"
            aria-label={
              privacy ? "Privacy and safeguarding" : "Delete conversation"
            }
            onClick={(e) => e.stopPropagation()}
          >
            <button
              className="icon-button modal-close"
              title="Close dialog"
              autoFocus
              onClick={() => {
                setPrivacy(false);
                setConfirmDelete(false);
              }}
            >
              <X size={20} />
            </button>
            {privacy ? (
              <>
                <LockKeyhole size={28} />
                <h2>Your privacy matters.</h2>
                <p>
                  No account or identity is required. Conversations are
                  encrypted in storage and retained for up to 7 days. Your
                  browser tab stores a random access token.
                </p>
                <p>
                  AI replies require consent to send recent conversation text to
                  the configured AI provider. Provider retention policies may
                  apply. Moderators can read conversations referred to the
                  queue.
                </p>
                <p>
                  Delete conversation removes messages and linked cases from
                  this service. Quick exit attempts deletion and leaves
                  immediately; network failure can prevent deletion. Neither
                  control erases browser or network history, backups, or
                  provider records.
                </p>
                <p>
                  This is not an emergency service. In Ghana, call 112 for
                  immediate danger. Human response times are not guaranteed.
                  Choose a language for the interface and new AI replies. Some translations need completion and native-speaker review. Reviewed source documents and original chat messages retain their original language.
                </p>
              </>
            ) : (
              <>
                <Trash2 size={28} />
                <h2>Delete this conversation?</h2>
                <p>
                  This deletes your messages and linked support requests from
                  this service. It cannot be undone.
                </p>
                <div className="modal-actions">
                  <button
                    className="button secondary"
                    onClick={() => setConfirmDelete(false)}
                  >
                    Keep conversation
                  </button>
                  <button className="button primary" onClick={clear}>
                    <Check size={16} /> Delete conversation
                  </button>
                </div>
              </>
            )}
          </section>
        </div>
      )}
    </div>,
    language,
  );
}
