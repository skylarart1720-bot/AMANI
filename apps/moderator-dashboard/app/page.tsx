"use client";
import { FormEvent, useCallback, useEffect, useState } from "react";

type Case = {
  id: string;
  priority: string;
  status: string;
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
  const [authenticated, setAuthenticated] = useState(false);
  const [token, setToken] = useState("");
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
    const [queue, refs, knowledge] = await Promise.all([
      api("admin/queue"),
      api("admin/directory"),
      api("admin/knowledge"),
    ]);
    setCases(queue);
    setDirectory(refs);
    setEntries(knowledge);
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
  const login = (e: FormEvent) => {
    e.preventDefault();
    void perform(async () => {
      await api("login", "POST", { token });
      setToken("");
      await refresh();
    });
  };
  const active = cases.find((c) => c.id === selected);
  if (!authenticated)
    return (
      <main className="login">
        <section>
          <span className="wordmark">AMANI</span>
          <h1>Moderator sign in</h1>
          <form onSubmit={login}>
            <label>
              Access token
              <input
                type="password"
                autoComplete="current-password"
                value={token}
                onChange={(e) => setToken(e.target.value)}
                required
              />
            </label>
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
    );
  return (
    <div>
      <header>
        <div>
          <span className="wordmark">AMANI</span>
          <span className="muted">Moderator workspace</span>
        </div>
        <button
          onClick={() =>
            void perform(async () => {
              await api("logout", "POST");
              setAuthenticated(false);
              setCases([]);
            })
          }
        >
          Sign out
        </button>
      </header>
      <main className="workspace">
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
          {["queue", "directory", "knowledge", "audit"].map((t) => (
            <button
              key={t}
              className={t === tab ? "active" : ""}
              onClick={() => {
                setTab(t);
                setError("");
                setNotice("");
                if (t === "audit") void loadAudit(auditActor).catch((e) => setError(e.message));
              }}
            >
              {t === "queue"
                ? "Support queue"
                : t === "directory"
                  ? "Referral directory"
                  : t === "knowledge"
                    ? "Knowledge review"
                    : "Audit log"}
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
                          <p>{m.content}</p>
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
                      <td>{r.organisation}</td>
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
  );
}
