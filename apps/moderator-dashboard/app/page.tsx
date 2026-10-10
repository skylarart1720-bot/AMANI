"use client";
import { FormEvent, useCallback, useEffect, useState } from "react";
import {Language, languageOptions, localize, useLanguage} from "./localization";

type Case = {
  id: string;
  priority: string;
  status: string;
  assignee: string | null;
  created: number;
  messages: { id: number; role: string; content: string }[];
};
type Referral = {
  id: string;
  title: string;
  organisation: string;
  category: string;
  region: string;
  regions: string[];
  phone: string | null;
  website: string;
  notes: string;
  verified_at: string | null;
  review_due: string | null;
  hours: string;
  languages: string[];
  channels: string[];
  trust: string;
  evidence: string | null;
  verification: "verified" | "stale" | "unverified";
};
type Entry = {
  id?: string;
  title: string;
  summary: string;
  category: string;
  source: string;
  source_url: string;
  verified_at: string;
  status?: string;
};
type AuditEntry = {
  id: number;
  action: string;
  actor: string;
  resource: string | null;
  outcome: string;
  detail: string | null;
  created: number;
};
type StaffAccount = { id: string; active: boolean | number; online: boolean; created: number };
type SetupItem = {name: string; status: string; next: string; missing_api_settings?: string[]};
const blank: Entry = {
  title: "",
  summary: "",
  category: "protest-rights",
  source: "",
  source_url: "",
  verified_at: "",
};
const categories = [
  "protest-rights",
  "activism",
  "mental-health",
  "climate",
  "digital-rights",
  "governance",
  "defenders",
  "gender-rights",
  "mens-circle",
];
const channels = ["phone", "website", "email", "in-person", "sms"];
const trustTiers = ["official", "community", "unverified"];
const blankReferral: Referral = {
  id: "",
  title: "",
  organisation: "",
  category: "protest-rights",
  region: "Ghana",
  regions: ["Ghana"],
  phone: null,
  website: "",
  notes: "",
  verified_at: null,
  review_due: null,
  hours: "Confirm with organisation",
  languages: ["English"],
  channels: ["website"],
  trust: "unverified",
  evidence: null,
  verification: "unverified",
};

export default function Dashboard() {
  const {language, setLanguage, coverage, refreshTranslations} = useLanguage();
  const [authenticated, setAuthenticated] = useState(false);
  const [token, setToken] = useState("");
  const [loginMode, setLoginMode] = useState<"staff" | "super_admin">("staff");
  const [staffId, setStaffId] = useState("");
  const [password, setPassword] = useState("");
  const [identity, setIdentity] = useState<{actor: string; role: string} | null>(null);
  const [available, setAvailable] = useState(true);
  const [presenceOnline, setPresenceOnline] = useState(false);
  const [setupItems, setSetupItems] = useState<SetupItem[]>([]);
  const [staff, setStaff] = useState<StaffAccount[]>([]);
  const [newStaffId, setNewStaffId] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [resetId, setResetId] = useState("");
  const [resetPassword, setResetPassword] = useState("");
  const [tab, setTab] = useState("queue");
  const [cases, setCases] = useState<Case[]>([]);
  const [directory, setDirectory] = useState<Referral[]>([]);
  const [entries, setEntries] = useState<Entry[]>([]);
  const [selected, setSelected] = useState("");
  const [filter, setFilter] = useState("all");
  const [reply, setReply] = useState("");
  const [editing, setEditing] = useState<Referral | null>(null);
  const [draft, setDraft] = useState<Entry>(blank);
  const [audit, setAudit] = useState<AuditEntry[]>([]);
  const [auditActor, setAuditActor] = useState("");
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [busy, setBusy] = useState(false);
  const [lastUpdated, setLastUpdated] = useState("");
  const api = useCallback(
    async (path: string, method = "GET", body?: unknown) => {
      const response = await fetch(`/api/${path}`, {
        method,
        headers: { "Content-Type": "application/json" },
        body: body === undefined ? undefined : JSON.stringify(body),
        signal: AbortSignal.timeout(15000),
      });
      const data = await response.json();
      if (response.status === 401) setAuthenticated(false);
      if (!response.ok)
        throw new Error(
          typeof data.detail === "string"
            ? data.detail
            : "Please check the submitted fields.",
        );
      return data;
    },
    [],
  );
  const refresh = useCallback(async () => {
    const [queue, refs, knowledge, me] = await Promise.all([
      api("admin/queue"),
      api("admin/directory"),
      api("admin/knowledge"),
      api("admin/me"),
    ]);
    setCases(queue);
    setDirectory(refs);
    setEntries(knowledge);
    setIdentity(me);
    setLastUpdated(new Date().toLocaleTimeString());
    setAuthenticated(true);
  }, [api]);
  const loadAudit = useCallback(
    async (actor?: string) => {
      const result = await api(
        `admin/audit?limit=200${actor ? `&actor=${encodeURIComponent(actor)}` : ""}`,
      );
      setAudit(result.entries);
      setLastUpdated(new Date().toLocaleTimeString());
    },
    [api],
  );
  useEffect(() => {
    void refresh().catch(() => {});
  }, [refresh]);
  useEffect(() => {
    if (!authenticated) return;
    const heartbeat = () => {
      void api("admin/presence", "POST", {available}).then((result) => setPresenceOnline(result.online)).catch(() => setPresenceOnline(false));
    };
    heartbeat();
    const timer = setInterval(heartbeat, 15000);
    return () => clearInterval(timer);
  }, [authenticated, available, api]);
  useEffect(() => {
    if (!authenticated) return;
    const events = new EventSource("/api/admin/events");
    events.onmessage = (event) => {
      setCases(JSON.parse(event.data));
      setLastUpdated(new Date().toLocaleTimeString());
    };
    const timer = setInterval(() => {
      if (!document.hidden) void refresh().catch((e) => setError(e.message));
    }, 8000);
    return () => {
      clearInterval(timer);
      events.close();
    };
  }, [authenticated, refresh]);
  const perform = async (action: () => Promise<void>) => {
    setBusy(true);
    setError("");
    setNotice("");
    try {
      await action();
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  };
  useEffect(() => {
    if (!authenticated || tab !== "staff" || identity?.role !== "super_admin") return;
    const timer = setInterval(() => {
      void api("admin/staff").then(setStaff).catch((e) => setError(e.message));
    }, 10000);
    return () => clearInterval(timer);
  }, [authenticated, tab, identity?.role, api]);
  const login = (e: FormEvent) => {
    e.preventDefault();
    void perform(async () => {
      await api("login", "POST", { mode: loginMode, token, staff_id: staffId, password });
      setToken("");
      setPassword("");
      setTab("queue");
      setAvailable(true);
      await refresh();
    });
  };
  const active = cases.find((c) => c.id === selected);
  const languagePicker = <label className="language-picker">Language<select aria-label="Language" value={language} onChange={(e) => setLanguage(e.target.value as Language)}>{languageOptions.map((item) => <option key={item.code} value={item.code} data-original-text>{item.native}</option>)}</select></label>;
  if (!authenticated)
    return localize(
      <main className="login">
        <section>
          <span className="wordmark">AMANI</span>
          <h1>Moderator sign in</h1>
          {languagePicker}
          {language !== "en" && coverage.status !== "complete" && <p className="muted" role="status">Some text remains in English. Full translation is unavailable right now.</p>}
          <form onSubmit={login}>
            <label>Sign in as
              <select value={loginMode} onChange={(e) => {
                setLoginMode(e.target.value as "staff" | "super_admin");
                setToken(""); setPassword(""); setError("");
              }}>
                <option value="staff">Staff</option>
                <option value="super_admin">Super Admin</option>
              </select>
            </label>
            {loginMode === "staff" ? <>
              <label>Staff ID<input autoComplete="username" value={staffId} onChange={(e) => setStaffId(e.target.value)} required maxLength={60} /></label>
              <label>Password<input type="password" autoComplete="current-password" value={password} onChange={(e) => setPassword(e.target.value)} required maxLength={128} /></label>
            </> : <label>
              Super Admin token
              <input
                type="password"
                autoComplete="current-password"
                value={token}
                onChange={(e) => setToken(e.target.value)}
                required
              />
            </label>}
            {error && (
              <p className="error" role="alert">
                {error}
              </p>
            )}
            <button className="primary" disabled={busy}>
              Sign in
            </button>
          </form>
          <p className="muted">Authorised support staff only.</p>
        </section>
      </main>
    , language);
  return localize(
    <div>
      <header>
        {languagePicker}
        <div>
          <span className="wordmark">AMANI</span>
          <span className="muted">{identity?.role === "super_admin" ? "Super Admin" : "Staff"} · {identity?.actor}</span>
        </div>
        <button className="availability" aria-pressed={available} onClick={() => setAvailable(!available)}>
          <span className={`presence-dot ${presenceOnline ? "online" : ""}`} /> {presenceOnline ? "Online" : "Offline"}
        </button>
        <button
          onClick={() =>
            void perform(async () => {
              await api("logout", "POST");
              setAuthenticated(false);
              setCases([]);
              setIdentity(null); setStaff([]); setAudit([]); setTab("queue");
            })
          }
        >
          Sign out
        </button>
      </header>
      <main className="workspace">
        {language !== "en" && coverage.status !== "complete" && <p className="language-note" role="status">Some text remains in English. Full translation is unavailable right now.</p>}
        <div className="heading">
          <div>
            <h1>Support operations</h1>
            <p className="muted">Last refreshed {lastUpdated}</p>
          </div>
          <button disabled={busy} onClick={() => void perform(refresh)}>
            Refresh
          </button>
        </div>
        <nav aria-label="Moderator views">
          {["queue", "directory", "knowledge", ...(identity?.role === "super_admin" ? ["staff", "audit", "setup"] : [])].map((t) => (
            <button
              key={t}
              className={t === tab ? "active" : ""}
              onClick={() => {
                setTab(t);
                setError("");
                setNotice("");
                if (t === "audit") void loadAudit(auditActor).catch((e) => setError(e.message));
                if (t === "staff") void api("admin/staff").then(setStaff).catch((e) => setError(e.message));
                if (t === "setup") void api("admin/setup").then((data) => setSetupItems(data.items)).catch((e) => setError(e.message));
              }}
            >
              {t === "queue"
                ? "Support queue"
                : t === "directory"
                  ? "Referral directory"
                  : t === "knowledge"
                    ? "Knowledge review"
                    : t === "staff" ? "Staff accounts" : t === "setup" ? "Setup & integrations" : "Audit log"}
            </button>
          ))}
        </nav>
        {error && (
          <p className="error" role="alert">
            {error}
          </p>
        )}
        {notice && (
          <p className="notice" role="status">
            {notice}
          </p>
        )}
        {tab === "setup" && identity?.role === "super_admin" && <>
          <div className="heading"><div><h2>Setup & integrations</h2><p className="muted">Configured services, unfinished features and the work needed to finalize AMANI.</p></div><button disabled={busy} onClick={() => void perform(async () => setSetupItems((await api("admin/setup")).items))}>Check configuration</button></div>
          <div className="setup-grid">{setupItems.map((item) => <section className="setup-card" key={item.name}><h3>{item.name}</h3><strong>{item.status}</strong><p>{item.next}</p>{item.missing_api_settings?.length ? <small>Missing API settings: {item.missing_api_settings.join(", ")}</small> : null}</section>)}</div>
          <section className="setup-card language-workbench"><h3>Translation catalogues</h3><p>Complete the selected language with the configured AI provider. Only public interface wording is sent. AI credits are required; native-speaker review is still needed.</p><p>{coverage.translated} / {coverage.total} · <span data-original-text>{languageOptions.find((item) => item.code === language)?.native}</span></p><div className="actions"><button onClick={refreshTranslations}>Refresh translations</button><button className="primary" disabled={busy || language === "en" || coverage.status === "generating"} onClick={() => void perform(async () => { await api(`admin/languages/${language}`, "POST", {}); refreshTranslations(); setNotice("Preparing translations…"); })}>Complete selected language</button></div></section>
        </>}
        {tab === "staff" && identity?.role === "super_admin" && <>
          <h2>Staff accounts</h2>
          <p className="muted">Create an ID and password for each staff member. Their work appears under that ID in the audit log.</p>
          <form onSubmit={(e) => {
            e.preventDefault();
            void perform(async () => {
              await api("admin/staff", "POST", {staff_id: newStaffId, password: newPassword});
              setNewStaffId(""); setNewPassword("");
              setStaff(await api("admin/staff")); setNotice("Staff account created. Share the ID and password privately with that person.");
            });
          }}>
            <div className="form-grid">
              <label>New staff ID<input value={newStaffId} onChange={(e) => setNewStaffId(e.target.value)} required minLength={2} maxLength={60} pattern="[A-Za-z0-9._@-]+" autoComplete="off" /></label>
              <label>Password<input type="password" value={newPassword} onChange={(e) => setNewPassword(e.target.value)} required minLength={12} maxLength={128} autoComplete="new-password" /><small>At least 12 characters.</small></label>
            </div>
            <button className="primary" disabled={busy}>Create staff</button>
          </form>
          {resetId && <form onSubmit={(e) => {
            e.preventDefault();
            void perform(async () => {
              await api(`admin/staff/${encodeURIComponent(resetId)}`, "PATCH", {password: resetPassword});
              setResetId(""); setResetPassword(""); setNotice("Password reset. Existing sessions have been revoked.");
            });
          }}>
            <label>New password for {resetId}<input type="password" value={resetPassword} onChange={(e) => setResetPassword(e.target.value)} required minLength={12} maxLength={128} autoComplete="new-password" /></label>
            <div className="actions"><button type="button" onClick={() => {setResetId(""); setResetPassword("");}}>Cancel</button><button className="primary" disabled={busy}>Reset password</button></div>
          </form>}
          <div className="table-wrap"><table><thead><tr><th>Staff ID</th><th>Status</th><th>Actions</th></tr></thead><tbody>
            {staff.map((account) => <tr key={account.id}><td>{account.id}</td><td>{account.active ? <><span className={`presence-dot ${account.online ? "online" : ""}`} /> {account.online ? "Online" : "Offline"}</> : "Disabled"}</td><td><div className="actions">
              <button disabled={busy} onClick={() => {setResetId(account.id); setResetPassword("");}}>Reset password</button>
              <button disabled={busy} onClick={() => void perform(async () => {
                await api(`admin/staff/${encodeURIComponent(account.id)}`, "PATCH", {active: !account.active});
                setStaff(await api("admin/staff")); setNotice(account.active ? "Account disabled and sessions revoked." : "Account enabled.");
              })}>{account.active ? "Disable" : "Enable"}</button>
              <button onClick={() => {setAuditActor(account.id); setTab("audit"); void loadAudit(account.id).catch((e) => setError(e.message));}}>View activity</button>
            </div></td></tr>)}
          </tbody></table></div>
          {staff.length === 0 && <p>No staff accounts yet. Create your first account above.</p>}
        </>}
        {tab === "queue" && (
          <>
            <div className="stats">
              <span>
                <strong>
                  {cases.filter((c) => c.status === "queued").length}
                </strong>{" "}
                Queued
              </span>
              <span>
                <strong>
                  {
                    cases.filter(
                      (c) =>
                        c.priority === "critical" && c.status !== "resolved",
                    ).length
                  }
                </strong>{" "}
                Critical
              </span>
              <span>
                <strong>
                  {cases.filter((c) => c.status === "in_progress").length}
                </strong>{" "}
                In progress
              </span>
            </div>
            <div className="queue-layout">
              <section>
                <label>
                  Case status
                  <select
                    value={filter}
                    onChange={(e) => setFilter(e.target.value)}
                  >
                    <option value="all">All cases</option>
                    <option value="queued">Queued</option>
                    <option value="in_progress">In progress</option>
                    <option value="resolved">Resolved</option>
                  </select>
                </label>
                <div className="case-list">
                  {cases
                    .filter((c) => filter === "all" || c.status === filter)
                    .map((c) => (
                      <button
                        key={c.id}
                        className={`case ${selected === c.id ? "selected" : ""}`}
                        onClick={() => {
                          setSelected(c.id);
                          setReply("");
                        }}
                      >
                        <span
                          className={
                            c.priority === "critical" ? "critical" : "muted"
                          }
                        >
                          {c.priority}
                        </span>
                        <strong>{c.id}</strong>
                        <span>{c.status.replace("_", " ")}</span>
                        <small>{c.assignee ? `Assigned to ${c.assignee}` : "General queue"}</small>
                        <small>
                          {new Date(c.created * 1000).toLocaleString()}
                        </small>
                      </button>
                    ))}
                  {!cases.length && (
                    <p className="empty">No support requests are waiting.</p>
                  )}
                </div>
              </section>
              <section className="conversation">
                {active ? (
                  <>
                    <div className="heading">
                      <h2>{active.id}</h2>
                      <select
                        aria-label="Update case status"
                        value={active.status}
                        disabled={busy}
                        onChange={(e) =>
                          void perform(async () => {
                            await api(`admin/queue/${active.id}`, "PATCH", {
                              status: e.target.value,
                            });
                            await refresh();
                          })
                        }
                      >
                        <option value="queued">Queued</option>
                        <option value="in_progress">In progress</option>
                        <option value="resolved">Resolved</option>
                      </select>
                    </div>
                    <div className="messages" role="log">
                      {active.messages.map((m) => (
                        <article className={`message ${m.role}`} key={m.id}>
                          <strong>
                            {m.role === "human"
                              ? "Moderator"
                              : m.role === "user"
                                ? "Visitor"
                                : "Amani"}
                          </strong>
                          <p data-original-text dir="auto">{m.content}</p>
                        </article>
                      ))}
                    </div>
                    <form
                      onSubmit={(e) => {
                        e.preventDefault();
                        void perform(async () => {
                          await api(`admin/queue/${active.id}/reply`, "POST", {
                            message: reply,
                          });
                          setReply("");
                          await refresh();
                        });
                      }}
                    >
                      <label>
                        Reply to visitor
                        <textarea
                          required
                          maxLength={4000}
                          rows={3}
                          value={reply}
                          onChange={(e) => setReply(e.target.value)}
                        />
                      </label>
                      <button
                        className="primary"
                        disabled={busy || !reply.trim()}
                      >
                        Send reply
                      </button>
                    </form>
                  </>
                ) : (
                  <p className="empty">Select a conversation.</p>
                )}
              </section>
            </div>
          </>
        )}
        {tab === "directory" && (
          <>
            <div className="heading">
              <h2>Published referral contacts</h2>
              <button
                className="primary"
                onClick={() => setEditing({ ...blankReferral })}
              >
                Add organisation
              </button>
            </div>
            {editing && (
              <form
                className="edit-form"
                onSubmit={(e) => {
                  e.preventDefault();
                  void perform(async () => {
                    await api("admin/directory", "PUT", editing);
                    setEditing(null);
                    setNotice("Directory updated.");
                    await refresh();
                  });
                }}
              >
                <div className="form-grid">
                  {(
                    [
                      "id",
                      "title",
                      "organisation",
                      "phone",
                      "website",
                      "hours",
                      "verified_at",
                    ] as const
                  ).map((key) => (
                    <label key={key}>
                      {key.replace("_", " ")}
                      <input
                        type={
                          key === "verified_at"
                            ? "date"
                            : key === "website"
                              ? "url"
                              : "text"
                        }
                        required={!["phone", "verified_at"].includes(key)}
                        value={editing[key] || ""}
                        onChange={(e) =>
                          setEditing({
                            ...editing,
                            [key]: e.target.value || null,
                          })
                        }
                      />
                    </label>
                  ))}
                  <label>
                    Category
                    <select
                      value={editing.category}
                      onChange={(e) =>
                        setEditing({ ...editing, category: e.target.value })
                      }
                    >
                      {[...categories, "emergency"].map((c) => (
                        <option key={c}>{c}</option>
                      ))}
                    </select>
                  </label>
                </div>
                <label>
                  Service description
                  <textarea
                    required
                    rows={3}
                    value={editing.notes}
                    onChange={(e) =>
                      setEditing({ ...editing, notes: e.target.value })
                    }
                  />
                </label>
                <div className="form-grid">
                  <label>
                    Coverage areas (comma separated)
                    <input
                      type="text"
                      required
                      placeholder="Ghana, International"
                      value={editing.regions.join(", ")}
                      onChange={(e) =>
                        setEditing({
                          ...editing,
                          regions: e.target.value
                            .split(",")
                            .map((r) => r.trim())
                            .filter(Boolean),
                        })
                      }
                    />
                    <small>
                      Coarse areas only. Never record a precise visitor location.
                      The first area is used as the primary coverage filter.
                    </small>
                  </label>
                  <label>
                    Languages served
                    <input
                      type="text"
                      value={editing.languages.join(", ")}
                      onChange={(e) =>
                        setEditing({
                          ...editing,
                          languages: e.target.value
                            .split(",")
                            .map((l) => l.trim())
                            .filter(Boolean),
                        })
                      }
                    />
                  </label>
                  <label>
                    Trust tier
                    <select
                      value={editing.trust}
                      onChange={(e) =>
                        setEditing({ ...editing, trust: e.target.value })
                      }
                    >
                      {trustTiers.map((tier) => (
                        <option key={tier}>{tier}</option>
                      ))}
                    </select>
                    <small>
                      A listing is never a partnership or an endorsement.
                    </small>
                  </label>
                  <label>
                    Review due
                    <input
                      type="date"
                      value={editing.review_due || ""}
                      onChange={(e) =>
                        setEditing({
                          ...editing,
                          review_due: e.target.value || null,
                        })
                      }
                    />
                    <small>
                      Past this date the contact is shown as needing re-checking.
                    </small>
                  </label>
                  <label>
                    What you checked
                    <input
                      type="text"
                      value={editing.evidence || ""}
                      placeholder="Which page or channel confirmed the details"
                      onChange={(e) =>
                        setEditing({
                          ...editing,
                          evidence: e.target.value || null,
                        })
                      }
                    />
                  </label>
                </div>
                <fieldset>
                  <legend>Contact channels offered</legend>
                  {channels.map((option) => (
                    <label key={option} className="checkbox">
                      <input
                        type="checkbox"
                        checked={editing.channels.includes(option)}
                        onChange={(e) =>
                          setEditing({
                            ...editing,
                            channels: e.target.checked
                              ? [...editing.channels, option]
                              : editing.channels.filter((c) => c !== option),
                          })
                        }
                      />
                      {option}
                    </label>
                  ))}
                </fieldset>
                <p className="muted">
                  Saving is a public change. Leave the check date blank if the
                  details were not confirmed; the listing will say so honestly.
                </p>
                <div className="actions">
                  <button type="button" onClick={() => setEditing(null)}>
                    Cancel
                  </button>
                  <button className="primary" disabled={busy}>
                    Save contact
                  </button>
                </div>
              </form>
            )}
            <div className="table-wrap">
              <table>
                <thead>
                  <tr>
                    <th>Organisation</th>
                    <th>Category</th>
                    <th>Coverage</th>
                    <th>Contact status</th>
                    <th />
                  </tr>
                </thead>
                <tbody>
                  {directory.map((r) => (
                    <tr key={r.id}>
                      <td data-original-text>{r.organisation}</td>
                      <td>{r.category}</td>
                      <td>{r.regions.join(", ")}</td>
                      <td>
                        <strong>{r.verification}</strong>
                        <br />
                        <small className="muted">
                          {r.verified_at
                            ? `Checked ${r.verified_at}`
                            : "Needs confirmation"}
                          {r.review_due ? ` · review due ${r.review_due}` : ""}
                        </small>
                      </td>
                      <td>
                        <button onClick={() => setEditing({ ...r })}>
                          Edit
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </>
        )}
        {tab === "audit" && (
          <>
            <div className="heading">
              <div>
                <h2>Staff audit log</h2>
                <p className="muted">
                  Who did what, to which record, and whether it succeeded. Message
                  text, tokens and phone numbers are never recorded here. Entries
                  are removed after 90 days and cannot be edited.
                </p>
              </div>
              <div className="actions">
                <label>
                  Filter by staff id
                  <input
                    type="text"
                    value={auditActor}
                    placeholder="all staff"
                    onChange={(e) => setAuditActor(e.target.value)}
                    onKeyDown={(e) => {
                      if (e.key === "Enter") {
                        e.preventDefault();
                        void perform(() => loadAudit(auditActor));
                      }
                    }}
                  />
                </label>
                <button
                  disabled={busy}
                  onClick={() => void perform(() => loadAudit(auditActor))}
                >
                  Apply
                </button>
              </div>
            </div>
            {!audit.length && <p className="empty">No audit entries to show.</p>}
            <div className="table-wrap">
              <table>
                <thead>
                  <tr>
                    <th>When</th>
                    <th>Staff</th>
                    <th>Action</th>
                    <th>Record</th>
                    <th>Outcome</th>
                    <th>Detail</th>
                  </tr>
                </thead>
                <tbody>
                  {audit.map((row) => (
                    <tr key={row.id}>
                      <td>{new Date(row.created * 1000).toLocaleString()}</td>
                      <td>{row.actor}</td>
                      <td>{row.action}</td>
                      <td>{row.resource || "—"}</td>
                      <td>{row.outcome}</td>
                      <td className="muted">{row.detail || "—"}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </>
        )}
        {tab === "knowledge" && (
          <div className="knowledge-layout">
            <section>
              <h2>Submit source material</h2>
              <form
                className="edit-form"
                onSubmit={(e) => {
                  e.preventDefault();
                  void perform(async () => {
                    await api("admin/knowledge", "POST", draft);
                    setDraft(blank);
                    setNotice(
                      "Submitted for review. This entry is not yet available to the assistant.",
                    );
                    await refresh();
                  });
                }}
              >
                {(
                  ["title", "source", "source_url", "verified_at"] as const
                ).map((key) => (
                  <label key={key}>
                    {key.replace("_", " ")}
                    <input
                      required
                      type={
                        key === "verified_at"
                          ? "date"
                          : key === "source_url"
                            ? "url"
                            : "text"
                      }
                      value={draft[key]}
                      onChange={(e) =>
                        setDraft({ ...draft, [key]: e.target.value })
                      }
                    />
                  </label>
                ))}
                <label>
                  Topic
                  <select
                    value={draft.category}
                    onChange={(e) =>
                      setDraft({ ...draft, category: e.target.value })
                    }
                  >
                    {categories.map((c) => (
                      <option key={c}>{c}</option>
                    ))}
                  </select>
                </label>
                <label>
                  Reviewed source text
                  <textarea
                    required
                    minLength={20}
                    maxLength={6000}
                    rows={6}
                    value={draft.summary}
                    onChange={(e) =>
                      setDraft({ ...draft, summary: e.target.value })
                    }
                  />
                </label>
                <button className="primary" disabled={busy}>
                  Submit for review
                </button>
              </form>
            </section>
            <section>
              <h2>Editorial review</h2>
              {!entries.length && (
                <p className="empty">No source entries submitted yet.</p>
              )}
              {entries.map((entry) => (
                <article className="entry" key={entry.id}>
                  <span className="muted">{entry.status}</span>
                  <h3>{entry.title}</h3>
                  <p>{entry.summary}</p>
                  <a
                    target="_blank"
                    rel="noopener noreferrer"
                    href={entry.source_url}
                  >
                    {entry.source}
                  </a>
                  <small>Verified {entry.verified_at}</small>
                  <div className="actions">
                    {entry.status !== "published" && (
                      <button
                        className="primary"
                        disabled={busy}
                        onClick={() =>
                          void perform(async () => {
                            await api(`admin/knowledge/${entry.id}`, "PATCH", {
                              status: "published",
                            });
                            await refresh();
                          })
                        }
                      >
                        Approve & publish
                      </button>
                    )}
                    {entry.status !== "rejected" && (
                      <button
                        disabled={busy}
                        onClick={() =>
                          void perform(async () => {
                            await api(`admin/knowledge/${entry.id}`, "PATCH", {
                              status: "rejected",
                            });
                            await refresh();
                          })
                        }
                      >
                        {entry.status === "published" ? "Unpublish" : "Reject"}
                      </button>
                    )}
                  </div>
                </article>
              ))}
            </section>
          </div>
        )}
      </main>
    </div>
  , language);
}
