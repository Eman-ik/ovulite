import { useCallback, useEffect, useMemo, useState } from "react";
import {
  AlertTriangle,
  Building2,
  Check,
  Clock,
  KeyRound,
  Lock,
  Pencil,
  Plus,
  Search,
  ShieldCheck,
  UserCog,
  X,
} from "lucide-react";
import api from "@/lib/api";
import { PasswordRules, passwordProblems } from "@/components/auth/PasswordRules";
import { useAuth } from "@/contexts/AuthContext";
import type {
  AdminUser,
  Laboratory,
  LaboratoryUsage,
  PaginatedResponse,
  RoleDescriptor,
} from "@/lib/types";
import { normalizeRole } from "@/lib/roleRoutes";

/**
 * Administration — users, roles and sites.
 *
 * Until this page existed, adding a user or changing a role meant opening
 * Postgres directly: `/auth/register` is self-service signup and nothing else
 * touched the users table. The whole RBAC design was therefore unusable by the
 * person it was designed for.
 *
 * The role picker is built from `/admin/roles`, which derives each role's
 * capabilities from the same tuples the API dependencies enforce. That keeps
 * this screen from claiming a permission the backend would refuse.
 */

function errorText(err: unknown): string {
  const detail = (err as { response?: { data?: { detail?: unknown } } })?.response?.data?.detail;
  if (typeof detail === "string") return detail;
  if (Array.isArray(detail) && detail.length > 0) {
    const first = detail[0] as { msg?: string };
    if (first?.msg) return first.msg;
  }
  return err instanceof Error ? err.message : "Request failed";
}

function formatDate(value: string | null): string {
  if (!value) return "—";
  const parsed = new Date(value);
  return Number.isNaN(parsed.getTime()) ? "—" : parsed.toISOString().slice(0, 10);
}

/** True while a failed-login lockout is still in force. */
function isLocked(user: AdminUser): boolean {
  if (!user.locked_until) return false;
  const until = new Date(user.locked_until).getTime();
  return !Number.isNaN(until) && until > Date.now();
}


type Tab = "users" | "sites";

export default function AdminPage() {
  const [tab, setTab] = useState<Tab>("users");

  return (
    <div className="space-y-5">
      <div>
        <h1 className="text-2xl font-semibold dash-heading">Administration</h1>
        <p className="mt-1 text-sm dash-muted-strong">
          Accounts, roles and sites for your organization. Changes here take effect on the
          user's next request.
        </p>
      </div>

      <div className="flex gap-1 rounded-xl bg-black/[0.04] p-1" role="tablist">
        {(
          [
            { key: "users", label: "Users & Roles", icon: UserCog },
            { key: "sites", label: "Sites", icon: Building2 },
          ] as const
        ).map(({ key, label, icon: Icon }) => (
          <button
            key={key}
            type="button"
            role="tab"
            aria-selected={tab === key}
            onClick={() => setTab(key)}
            className={`inline-flex flex-1 items-center justify-center gap-2 rounded-lg px-3 py-2 text-sm font-medium transition ${
              tab === key
                ? "bg-[var(--card)] dash-heading shadow-sm"
                : "dash-muted-strong hover:bg-black/[0.03]"
            }`}
          >
            <Icon className="h-4 w-4" />
            {label}
          </button>
        ))}
      </div>

      {tab === "users" ? <UsersPanel /> : <SitesPanel />}
    </div>
  );
}

/* ─────────────────────────────── Users ─────────────────────────────── */

type UserDraft = {
  username: string;
  password: string;
  role: string;
  full_name: string;
  email: string;
};

const EMPTY_DRAFT: UserDraft = {
  username: "",
  password: "",
  role: "researcher",
  full_name: "",
  email: "",
};

function UsersPanel() {
  const { user: currentUser } = useAuth();
  const [users, setUsers] = useState<AdminUser[]>([]);
  const [roles, setRoles] = useState<RoleDescriptor[]>([]);
  const [search, setSearch] = useState("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [creating, setCreating] = useState(false);
  const [draft, setDraft] = useState<UserDraft>(EMPTY_DRAFT);
  const [editing, setEditing] = useState<AdminUser | null>(null);
  const [resetting, setResetting] = useState<AdminUser | null>(null);
  const [busy, setBusy] = useState(false);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [userRes, roleRes] = await Promise.all([
        api.get<PaginatedResponse<AdminUser>>("/admin/users", {
          params: { page_size: 100, ...(search.trim() ? { search: search.trim() } : {}) },
        }),
        api.get<RoleDescriptor[]>("/admin/roles"),
      ]);
      setUsers(userRes.data.items);
      setRoles(roleRes.data);
    } catch (err) {
      setError(errorText(err));
    } finally {
      setLoading(false);
    }
  }, [search]);

  useEffect(() => {
    const timer = setTimeout(() => void load(), search ? 300 : 0);
    return () => clearTimeout(timer);
  }, [load, search]);

  const roleLabel = useMemo(() => {
    const map = new Map(roles.map((r) => [r.role, r.label]));
    return (role: string | null) => (role ? map.get(role) ?? role : "—");
  }, [roles]);

  const activeAdmins = users.filter(
    (u) => u.active && normalizeRole(u.role) === "admin",
  ).length;

  const run = async (action: () => Promise<void>, success: string) => {
    setBusy(true);
    setError(null);
    setNotice(null);
    try {
      await action();
      setNotice(success);
      await load();
      return true;
    } catch (err) {
      setError(errorText(err));
      return false;
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="space-y-4">
      {error && <Banner tone="error" title="That didn't work" body={error} />}
      {notice && <Banner tone="ok" title={notice} />}

      <div className="flex flex-wrap items-center gap-3">
        <label className="relative flex-1 min-w-[220px]">
          <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 dash-muted" />
          <input
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Search username, name or email"
            className="h-10 w-full rounded-xl border border-[var(--border)] bg-[var(--input)] pl-9 pr-3 text-sm text-[var(--foreground)]"
          />
        </label>
        <button
          type="button"
          onClick={() => {
            setDraft(EMPTY_DRAFT);
            setCreating(true);
          }}
          className="inline-flex h-10 items-center gap-1.5 rounded-xl bg-[var(--primary)] px-4 text-sm font-semibold text-[var(--primary-foreground)] transition hover:bg-[#596070]"
        >
          <Plus className="h-4 w-4" />
          Add user
        </button>
      </div>

      {/* The last-admin rule is enforced server-side; saying so here stops the
          operator discovering it as a 409 halfway through a deactivation. */}
      {activeAdmins === 1 && (
        <Banner
          tone="warn"
          title="One active administrator"
          body="This organization has a single admin account. It cannot be demoted or deactivated — add a second admin first."
        />
      )}

      <div className="dash-card p-0">
        <div className="custom-scrollbar overflow-x-auto">
          <table className="w-full min-w-[760px] text-sm">
            <thead>
              <tr className="border-b border-[var(--border)] text-left text-xs uppercase tracking-wide dash-muted">
                <th className="px-4 py-3 font-medium">User</th>
                <th className="px-4 py-3 font-medium">Role</th>
                <th className="px-4 py-3 font-medium">Status</th>
                <th className="px-4 py-3 font-medium">Last login</th>
                <th className="px-4 py-3 font-medium text-right">Actions</th>
              </tr>
            </thead>
            <tbody>
              {loading && (
                <tr>
                  <td colSpan={5} className="px-4 py-8 text-center dash-muted">
                    Loading…
                  </td>
                </tr>
              )}
              {!loading && users.length === 0 && (
                <tr>
                  <td colSpan={5} className="px-4 py-8 text-center dash-muted">
                    No users match that search.
                  </td>
                </tr>
              )}
              {users.map((u) => {
                const isSelf = u.user_id === currentUser?.user_id;
                return (
                  <tr key={u.user_id} className="border-b border-[var(--border)] last:border-0">
                    <td className="px-4 py-3">
                      <div className="font-medium dash-heading">
                        {u.username}
                        {isSelf && (
                          <span className="ml-2 rounded-full bg-[rgba(148, 169, 190,0.22)] px-2 py-0.5 text-[10px] font-semibold text-[#3F4758]">
                            you
                          </span>
                        )}
                      </div>
                      <div className="text-xs dash-muted">
                        {u.full_name || "—"}
                        {u.email ? ` · ${u.email}` : ""}
                      </div>
                    </td>
                    <td className="px-4 py-3 dash-muted">{roleLabel(u.role)}</td>
                    <td className="px-4 py-3">
                      {/* Ordered by what is actually blocking the user. A
                          pending account reads as "Active" otherwise, which
                          says nothing about why they cannot sign in. */}
                      {u.pending_approval ? (
                        <span className="inline-flex items-center gap-1 text-xs font-medium text-[#7a5a12]">
                          <Clock className="h-3.5 w-3.5" /> Pending approval
                        </span>
                      ) : !u.active ? (
                        <span className="inline-flex items-center gap-1 text-xs font-medium text-[#9d3730]">
                          <X className="h-3.5 w-3.5" /> Deactivated
                        </span>
                      ) : isLocked(u) ? (
                        <span className="inline-flex items-center gap-1 text-xs font-medium text-[#9d3730]">
                          <Lock className="h-3.5 w-3.5" /> Locked out
                        </span>
                      ) : u.must_change_password ? (
                        <span className="inline-flex items-center gap-1 text-xs font-medium text-[#7a5a12]">
                          <KeyRound className="h-3.5 w-3.5" /> Must change password
                        </span>
                      ) : (
                        <span className="inline-flex items-center gap-1 text-xs font-medium text-[#3F4758]">
                          <Check className="h-3.5 w-3.5" /> Active
                        </span>
                      )}
                    </td>
                    <td className="px-4 py-3 dash-muted">{formatDate(u.last_login)}</td>
                    <td className="px-4 py-3">
                      <div className="flex justify-end gap-1.5">
                        {u.pending_approval && (
                          <>
                            <button
                              type="button"
                              disabled={busy}
                              title="Approve this signup so the account can log in"
                              onClick={() =>
                                void run(
                                  async () => {
                                    await api.post(`/admin/users/${u.user_id}/approve`);
                                  },
                                  `${u.username} approved.`,
                                )
                              }
                              className="rounded-lg px-2.5 py-1.5 text-xs font-semibold text-[#35748a] transition hover:bg-[rgba(53,116,138,0.10)] disabled:opacity-35"
                            >
                              Approve
                            </button>
                            <button
                              type="button"
                              disabled={busy}
                              title="Refuse this signup"
                              onClick={() =>
                                void run(
                                  async () => {
                                    await api.post(`/admin/users/${u.user_id}/reject`);
                                  },
                                  `${u.username} rejected.`,
                                )
                              }
                              className="rounded-lg px-2.5 py-1.5 text-xs font-semibold text-[#9d3730] transition hover:bg-[rgba(157,55,48,0.10)] disabled:opacity-35"
                            >
                              Reject
                            </button>
                          </>
                        )}
                        {isLocked(u) && (
                          <button
                            type="button"
                            disabled={busy}
                            title="Clear the failed-login lockout now"
                            onClick={() =>
                              void run(
                                async () => {
                                  await api.post(`/admin/users/${u.user_id}/unlock`);
                                },
                                `${u.username} unlocked.`,
                              )
                            }
                            className="rounded-lg px-2.5 py-1.5 text-xs font-semibold text-[#3F4758] transition hover:bg-[rgba(89,96,112,0.10)] disabled:opacity-35"
                          >
                            Unlock
                          </button>
                        )}
                        <IconButton label="Edit" icon={Pencil} onClick={() => setEditing(u)} />
                        <IconButton
                          label="Reset password"
                          icon={KeyRound}
                          onClick={() => setResetting(u)}
                        />
                        {u.active && !u.pending_approval && (
                          <button
                            type="button"
                            disabled={busy || isSelf}
                            title={
                              isSelf
                                ? "You cannot deactivate your own account"
                                : "Deactivate this user"
                            }
                            onClick={() =>
                              void run(
                                async () => {
                                  await api.delete(`/admin/users/${u.user_id}`);
                                },
                                `${u.username} deactivated.`,
                              )
                            }
                            className="rounded-lg px-2.5 py-1.5 text-xs font-semibold text-[#9d3730] transition hover:bg-[rgba(157,55,48,0.10)] disabled:opacity-35"
                          >
                            Deactivate
                          </button>
                        )}
                        {!u.active && (
                          <button
                            type="button"
                            disabled={busy}
                            onClick={() =>
                              void run(
                                async () => {
                                  await api.put(`/admin/users/${u.user_id}`, { active: true });
                                },
                                `${u.username} reactivated.`,
                              )
                            }
                            className="rounded-lg px-2.5 py-1.5 text-xs font-semibold text-[#3F4758] transition hover:bg-[rgba(89, 96, 112,0.10)] disabled:opacity-35"
                          >
                            Reactivate
                          </button>
                        )}
                      </div>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </div>

      <RoleReference roles={roles} />

      {creating && (
        <Modal title="Add user" onClose={() => setCreating(false)}>
          <UserForm
            draft={draft}
            roles={roles}
            onChange={setDraft}
            requirePassword
            busy={busy}
            submitLabel="Create user"
            onSubmit={async () => {
              const ok = await run(
                async () => {
                  await api.post("/admin/users", {
                    username: draft.username.trim(),
                    password: draft.password,
                    role: draft.role,
                    full_name: draft.full_name.trim() || null,
                    email: draft.email.trim() || null,
                  });
                },
                `${draft.username.trim()} created.`,
              );
              if (ok) setCreating(false);
            }}
          />
        </Modal>
      )}

      {editing && (
        <Modal title={`Edit ${editing.username}`} onClose={() => setEditing(null)}>
          <EditUserForm
            user={editing}
            roles={roles}
            busy={busy}
            onSubmit={async (changes) => {
              const ok = await run(
                async () => {
                  await api.put(`/admin/users/${editing.user_id}`, changes);
                },
                `${editing.username} updated.`,
              );
              if (ok) setEditing(null);
            }}
          />
        </Modal>
      )}

      {resetting && (
        <Modal title={`Reset password — ${resetting.username}`} onClose={() => setResetting(null)}>
          <PasswordForm
            busy={busy}
            onSubmit={async (password) => {
              const ok = await run(
                async () => {
                  await api.post(`/admin/users/${resetting.user_id}/password`, {
                    new_password: password,
                  });
                },
                `Password reset for ${resetting.username}.`,
              );
              if (ok) setResetting(null);
            }}
          />
        </Modal>
      )}
    </div>
  );
}

function RoleReference({ roles }: { roles: RoleDescriptor[] }) {
  if (roles.length === 0) return null;
  return (
    <div className="dash-card">
      <div className="flex items-center gap-2">
        <ShieldCheck className="h-4 w-4 dash-muted" />
        <h2 className="text-base font-semibold dash-heading">What each role can do</h2>
      </div>
      <p className="mt-1 text-xs dash-muted">
        Served from the API, derived from the same role groups the endpoints enforce — this table
        cannot claim a permission the backend would refuse.
      </p>
      <div className="custom-scrollbar mt-3 overflow-x-auto">
        <table className="w-full min-w-[640px] text-sm">
          <thead>
            <tr className="border-b border-[var(--border)] text-left text-xs uppercase tracking-wide dash-muted">
              <th className="py-2 pr-4 font-medium">Role</th>
              <th className="py-2 pr-4 font-medium">Lab data</th>
              <th className="py-2 pr-4 font-medium">ET data</th>
              <th className="py-2 pr-4 font-medium">Run predictions</th>
              <th className="py-2 font-medium">Admin</th>
            </tr>
          </thead>
          <tbody>
            {roles.map((r) => (
              <tr key={r.role} className="border-b border-[var(--border)] last:border-0">
                <td className="py-2.5 pr-4">
                  <div className="font-medium dash-heading">{r.label}</div>
                  <div className="text-xs dash-muted">{r.description}</div>
                </td>
                <Yes on={r.can_write_lab} />
                <Yes on={r.can_write_et} />
                <Yes on={r.can_run_predictions} />
                <Yes on={r.is_admin} last />
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

function Yes({ on, last = false }: { on: boolean; last?: boolean }) {
  return (
    <td className={`py-2.5 ${last ? "" : "pr-4"}`}>
      {on ? (
        <Check className="h-4 w-4 text-[#3F4758]" aria-label="yes" />
      ) : (
        <span className="dash-muted" aria-label="no">
          —
        </span>
      )}
    </td>
  );
}

function UserForm({
  draft,
  roles,
  onChange,
  onSubmit,
  busy,
  requirePassword,
  submitLabel,
}: {
  draft: UserDraft;
  roles: RoleDescriptor[];
  onChange: (next: UserDraft) => void;
  onSubmit: () => void | Promise<void>;
  busy: boolean;
  requirePassword: boolean;
  submitLabel: string;
}) {
  // The backend enforces app/auth/password_policy.py on admin-set passwords
  // too, so a length-only check here would promise a password the API refuses.
  const canSubmit =
    draft.username.trim().length >= 3 &&
    (!requirePassword || passwordProblems(draft.password).length === 0);

  return (
    <form
      className="space-y-3"
      onSubmit={(e) => {
        e.preventDefault();
        if (canSubmit) void onSubmit();
      }}
    >
      <Field label="Username">
        <input
          value={draft.username}
          onChange={(e) => onChange({ ...draft, username: e.target.value })}
          autoFocus
          className={inputClass}
        />
      </Field>
      {requirePassword && (
        <Field
          label="Password"
          hint="A temporary password — the user must replace it at first sign-in."
        >
          <input
            type="password"
            value={draft.password}
            onChange={(e) => onChange({ ...draft, password: e.target.value })}
            className={inputClass}
          />
          <div className="mt-2">
            <PasswordRules password={draft.password} />
          </div>
        </Field>
      )}
      <Field label="Role">
        <select
          value={draft.role}
          onChange={(e) => onChange({ ...draft, role: e.target.value })}
          className={inputClass}
        >
          {roles.map((r) => (
            <option key={r.role} value={r.role}>
              {r.label}
            </option>
          ))}
        </select>
        <p className="mt-1 text-xs dash-muted">
          {roles.find((r) => r.role === draft.role)?.description ?? ""}
        </p>
      </Field>
      <Field label="Full name (optional)">
        <input
          value={draft.full_name}
          onChange={(e) => onChange({ ...draft, full_name: e.target.value })}
          className={inputClass}
        />
      </Field>
      <Field label="Email (optional)">
        <input
          type="email"
          value={draft.email}
          onChange={(e) => onChange({ ...draft, email: e.target.value })}
          className={inputClass}
        />
      </Field>
      <SubmitRow busy={busy} disabled={!canSubmit} label={submitLabel} />
    </form>
  );
}

function EditUserForm({
  user,
  roles,
  onSubmit,
  busy,
}: {
  user: AdminUser;
  roles: RoleDescriptor[];
  onSubmit: (changes: Record<string, unknown>) => void | Promise<void>;
  busy: boolean;
}) {
  const [role, setRole] = useState(user.role ?? "researcher");
  const [fullName, setFullName] = useState(user.full_name ?? "");
  const [email, setEmail] = useState(user.email ?? "");

  return (
    <form
      className="space-y-3"
      onSubmit={(e) => {
        e.preventDefault();
        void onSubmit({
          role,
          full_name: fullName.trim() || null,
          email: email.trim() || null,
        });
      }}
    >
      <Field label="Role">
        <select value={role} onChange={(e) => setRole(e.target.value)} className={inputClass}>
          {roles.map((r) => (
            <option key={r.role} value={r.role}>
              {r.label}
            </option>
          ))}
        </select>
        <p className="mt-1 text-xs dash-muted">
          {roles.find((r) => r.role === role)?.description ?? ""}
        </p>
      </Field>
      <Field label="Full name">
        <input value={fullName} onChange={(e) => setFullName(e.target.value)} className={inputClass} />
      </Field>
      <Field label="Email">
        <input
          type="email"
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          className={inputClass}
        />
      </Field>
      <SubmitRow busy={busy} disabled={false} label="Save changes" />
    </form>
  );
}

function PasswordForm({
  onSubmit,
  busy,
}: {
  onSubmit: (password: string) => void | Promise<void>;
  busy: boolean;
}) {
  const [password, setPassword] = useState("");
  const [confirm, setConfirm] = useState("");
  const problems = passwordProblems(password);
  const mismatch = confirm.length > 0 && confirm !== password;
  const canSubmit = problems.length === 0 && confirm === password;

  return (
    <form
      className="space-y-3"
      onSubmit={(e) => {
        e.preventDefault();
        if (canSubmit) void onSubmit(password);
      }}
    >
      <Field label="New password" hint="The user must replace it at their next sign-in.">
        <input
          type="password"
          value={password}
          autoFocus
          onChange={(e) => setPassword(e.target.value)}
          className={inputClass}
        />
        <div className="mt-2">
          <PasswordRules password={password} />
        </div>
      </Field>
      <Field label="Confirm">
        <input
          type="password"
          value={confirm}
          onChange={(e) => setConfirm(e.target.value)}
          className={inputClass}
        />
        {mismatch && <p className="mt-1 text-xs text-[#9d3730]">Passwords do not match.</p>}
      </Field>
      <p className="text-xs dash-muted">
        Recorded as its own audit event, separate from any other edit to this account.
      </p>
      <SubmitRow busy={busy} disabled={!canSubmit} label="Reset password" />
    </form>
  );
}

/* ─────────────────────────────── Sites ─────────────────────────────── */

type SiteDraft = {
  name: string;
  site_type: string;
  code: string;
  city: string;
  country: string;
  contact_name: string;
  contact_phone: string;
  contact_email: string;
};

const EMPTY_SITE: SiteDraft = {
  name: "",
  site_type: "Laboratory",
  code: "",
  city: "",
  country: "",
  contact_name: "",
  contact_phone: "",
  contact_email: "",
};

const SITE_TYPES = ["Laboratory", "Satellite", "Farm", "Customer"];

function SitesPanel() {
  const [sites, setSites] = useState<Laboratory[]>([]);
  const [usage, setUsage] = useState<Record<number, LaboratoryUsage>>({});
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [creating, setCreating] = useState(false);
  const [draft, setDraft] = useState<SiteDraft>(EMPTY_SITE);
  const [editing, setEditing] = useState<Laboratory | null>(null);
  const [busy, setBusy] = useState(false);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await api.get<PaginatedResponse<Laboratory>>("/laboratories/", {
        params: { page_size: 100, include_inactive: true },
      });
      setSites(res.data.items);
      // Usage decides whether a site can be deleted or only deactivated, so it
      // is fetched up front rather than on click.
      const usages = await Promise.all(
        res.data.items.map((s) =>
          api
            .get<LaboratoryUsage>(`/laboratories/${s.laboratory_id}/usage`)
            .then((r) => r.data)
            .catch(() => null),
        ),
      );
      const map: Record<number, LaboratoryUsage> = {};
      usages.forEach((u) => {
        if (u) map[u.laboratory_id] = u;
      });
      setUsage(map);
    } catch (err) {
      setError(errorText(err));
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  const run = async (action: () => Promise<void>, success: string) => {
    setBusy(true);
    setError(null);
    setNotice(null);
    try {
      await action();
      setNotice(success);
      await load();
      return true;
    } catch (err) {
      setError(errorText(err));
      return false;
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="space-y-4">
      {error && <Banner tone="error" title="That didn't work" body={error} />}
      {notice && <Banner tone="ok" title={notice} />}

      <div className="flex items-center justify-between gap-3">
        <p className="text-sm dash-muted-strong">
          Sites replaced the free-text location that used to be typed on each transfer. Renaming one
          here re-labels every record attached to it.
        </p>
        <button
          type="button"
          onClick={() => {
            setDraft(EMPTY_SITE);
            setCreating(true);
          }}
          className="inline-flex h-10 shrink-0 items-center gap-1.5 rounded-xl bg-[var(--primary)] px-4 text-sm font-semibold text-[var(--primary-foreground)] transition hover:bg-[#596070]"
        >
          <Plus className="h-4 w-4" />
          Add site
        </button>
      </div>

      <div className="dash-card p-0">
        <div className="custom-scrollbar overflow-x-auto">
          <table className="w-full min-w-[760px] text-sm">
            <thead>
              <tr className="border-b border-[var(--border)] text-left text-xs uppercase tracking-wide dash-muted">
                <th className="px-4 py-3 font-medium">Site</th>
                <th className="px-4 py-3 font-medium">Type</th>
                <th className="px-4 py-3 font-medium">Attached records</th>
                <th className="px-4 py-3 font-medium">Status</th>
                <th className="px-4 py-3 font-medium text-right">Actions</th>
              </tr>
            </thead>
            <tbody>
              {loading && (
                <tr>
                  <td colSpan={5} className="px-4 py-8 text-center dash-muted">
                    Loading…
                  </td>
                </tr>
              )}
              {!loading && sites.length === 0 && (
                <tr>
                  <td colSpan={5} className="px-4 py-8 text-center dash-muted">
                    No sites yet.
                  </td>
                </tr>
              )}
              {sites.map((s) => {
                const u = usage[s.laboratory_id];
                const attached = u ? u.transfers + u.opu_sessions + u.recipients : 0;
                return (
                  <tr key={s.laboratory_id} className="border-b border-[var(--border)] last:border-0">
                    <td className="px-4 py-3">
                      <div className="font-medium dash-heading">{s.name}</div>
                      <div className="text-xs dash-muted">
                        {[s.code, s.city, s.country].filter(Boolean).join(" · ") || "—"}
                      </div>
                    </td>
                    <td className="px-4 py-3 dash-muted">{s.site_type ?? "—"}</td>
                    <td className="px-4 py-3 dash-muted">
                      {u ? (
                        <span title={`${u.transfers} transfers, ${u.opu_sessions} OPU sessions, ${u.recipients} recipients`}>
                          {attached.toLocaleString()}
                        </span>
                      ) : (
                        "—"
                      )}
                    </td>
                    <td className="px-4 py-3">
                      {s.active ? (
                        <span className="inline-flex items-center gap-1 text-xs font-medium text-[#3F4758]">
                          <Check className="h-3.5 w-3.5" /> Active
                        </span>
                      ) : (
                        <span className="inline-flex items-center gap-1 text-xs font-medium dash-muted">
                          <X className="h-3.5 w-3.5" /> Hidden
                        </span>
                      )}
                    </td>
                    <td className="px-4 py-3">
                      <div className="flex justify-end gap-1.5">
                        <IconButton label="Edit" icon={Pencil} onClick={() => setEditing(s)} />
                        {s.active ? (
                          <button
                            type="button"
                            disabled={busy}
                            title={
                              attached > 0
                                ? `${attached} records point at this site — it will be hidden from pickers, not deleted.`
                                : "Nothing references this site, so it will be deleted outright."
                            }
                            onClick={() =>
                              void run(
                                async () => {
                                  await api.delete(`/laboratories/${s.laboratory_id}`);
                                },
                                attached > 0 ? `${s.name} hidden.` : `${s.name} deleted.`,
                              )
                            }
                            className="rounded-lg px-2.5 py-1.5 text-xs font-semibold text-[#9d3730] transition hover:bg-[rgba(157,55,48,0.10)] disabled:opacity-35"
                          >
                            {attached > 0 ? "Hide" : "Delete"}
                          </button>
                        ) : (
                          <button
                            type="button"
                            disabled={busy}
                            onClick={() =>
                              void run(
                                async () => {
                                  await api.put(`/laboratories/${s.laboratory_id}`, { active: true });
                                },
                                `${s.name} restored.`,
                              )
                            }
                            className="rounded-lg px-2.5 py-1.5 text-xs font-semibold text-[#3F4758] transition hover:bg-[rgba(89, 96, 112,0.10)] disabled:opacity-35"
                          >
                            Restore
                          </button>
                        )}
                      </div>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </div>

      {creating && (
        <Modal title="Add site" onClose={() => setCreating(false)}>
          <SiteForm
            draft={draft}
            onChange={setDraft}
            busy={busy}
            submitLabel="Create site"
            onSubmit={async () => {
              const ok = await run(
                async () => {
                  await api.post("/laboratories/", {
                    name: draft.name.trim(),
                    site_type: draft.site_type,
                    code: draft.code.trim() || null,
                    city: draft.city.trim() || null,
                    country: draft.country.trim() || null,
                    contact_name: draft.contact_name.trim() || null,
                    contact_phone: draft.contact_phone.trim() || null,
                    contact_email: draft.contact_email.trim() || null,
                  });
                },
                `${draft.name.trim()} created.`,
              );
              if (ok) setCreating(false);
            }}
          />
        </Modal>
      )}

      {editing && (
        <Modal title={`Edit ${editing.name}`} onClose={() => setEditing(null)}>
          <SiteForm
            draft={{
              name: editing.name,
              site_type: editing.site_type ?? "Laboratory",
              code: editing.code ?? "",
              city: editing.city ?? "",
              country: editing.country ?? "",
              contact_name: editing.contact_name ?? "",
              contact_phone: editing.contact_phone ?? "",
              contact_email: editing.contact_email ?? "",
            }}
            onChange={() => undefined}
            controlled={false}
            busy={busy}
            submitLabel="Save changes"
            onSubmit={async (next) => {
              const ok = await run(
                async () => {
                  await api.put(`/laboratories/${editing.laboratory_id}`, {
                    name: next.name.trim(),
                    site_type: next.site_type,
                    code: next.code.trim() || null,
                    city: next.city.trim() || null,
                    country: next.country.trim() || null,
                    contact_name: next.contact_name.trim() || null,
                    contact_phone: next.contact_phone.trim() || null,
                    contact_email: next.contact_email.trim() || null,
                  });
                },
                `${next.name.trim()} updated.`,
              );
              if (ok) setEditing(null);
            }}
          />
        </Modal>
      )}
    </div>
  );
}

function SiteForm({
  draft,
  onChange,
  onSubmit,
  busy,
  submitLabel,
  controlled = true,
}: {
  draft: SiteDraft;
  onChange: (next: SiteDraft) => void;
  onSubmit: (next: SiteDraft) => void | Promise<void>;
  busy: boolean;
  submitLabel: string;
  controlled?: boolean;
}) {
  const [local, setLocal] = useState<SiteDraft>(draft);
  const value = controlled ? draft : local;
  const update = (next: SiteDraft) => {
    if (controlled) onChange(next);
    else setLocal(next);
  };
  const canSubmit = value.name.trim().length > 0;

  return (
    <form
      className="space-y-3"
      onSubmit={(e) => {
        e.preventDefault();
        if (canSubmit) void onSubmit(value);
      }}
    >
      <Field label="Name">
        <input
          value={value.name}
          autoFocus
          onChange={(e) => update({ ...value, name: e.target.value })}
          className={inputClass}
        />
      </Field>
      <Field label="Type">
        <select
          value={value.site_type}
          onChange={(e) => update({ ...value, site_type: e.target.value })}
          className={inputClass}
        >
          {SITE_TYPES.map((t) => (
            <option key={t} value={t}>
              {t}
            </option>
          ))}
        </select>
      </Field>
      <div className="grid grid-cols-2 gap-3">
        <Field label="Code (optional)">
          <input
            value={value.code}
            onChange={(e) => update({ ...value, code: e.target.value })}
            className={inputClass}
          />
        </Field>
        <Field label="City (optional)">
          <input
            value={value.city}
            onChange={(e) => update({ ...value, city: e.target.value })}
            className={inputClass}
          />
        </Field>
      </div>
      <Field label="Contact name (optional)">
        <input
          value={value.contact_name}
          onChange={(e) => update({ ...value, contact_name: e.target.value })}
          className={inputClass}
        />
      </Field>
      <div className="grid grid-cols-2 gap-3">
        <Field label="Phone (optional)">
          <input
            value={value.contact_phone}
            onChange={(e) => update({ ...value, contact_phone: e.target.value })}
            className={inputClass}
          />
        </Field>
        <Field label="Email (optional)">
          <input
            type="email"
            value={value.contact_email}
            onChange={(e) => update({ ...value, contact_email: e.target.value })}
            className={inputClass}
          />
        </Field>
      </div>
      <SubmitRow busy={busy} disabled={!canSubmit} label={submitLabel} />
    </form>
  );
}

/* ───────────────────────────── Primitives ───────────────────────────── */

const inputClass =
  "h-10 w-full rounded-xl border border-[var(--border)] bg-[var(--input)] px-3 text-sm text-[var(--foreground)]";

function Field({
  label,
  hint,
  children,
}: {
  label: string;
  hint?: string;
  children: React.ReactNode;
}) {
  return (
    <label className="block">
      <span className="mb-1.5 block text-xs font-medium uppercase tracking-wide dash-muted">
        {label}
      </span>
      {children}
      {hint && <p className="mt-1 text-xs dash-muted">{hint}</p>}
    </label>
  );
}

function SubmitRow({
  busy,
  disabled,
  label,
}: {
  busy: boolean;
  disabled: boolean;
  label: string;
}) {
  return (
    <button
      type="submit"
      disabled={busy || disabled}
      className="mt-2 inline-flex h-10 w-full items-center justify-center rounded-xl bg-[var(--primary)] text-sm font-semibold text-[var(--primary-foreground)] transition hover:bg-[#596070] disabled:opacity-40"
    >
      {busy ? "Working…" : label}
    </button>
  );
}

function IconButton({
  label,
  icon: Icon,
  onClick,
}: {
  label: string;
  icon: typeof Pencil;
  onClick: () => void;
}) {
  return (
    <button
      type="button"
      title={label}
      aria-label={label}
      onClick={onClick}
      className="rounded-lg p-2 dash-muted transition hover:bg-black/[0.05]"
    >
      <Icon className="h-4 w-4" />
    </button>
  );
}

function Banner({
  tone,
  title,
  body,
}: {
  tone: "ok" | "warn" | "error";
  title: string;
  body?: string;
}) {
  const styles = {
    ok: "border-[rgba(148, 169, 190,0.34)] bg-[rgba(148, 169, 190,0.16)] text-[#3F4758]",
    warn: "border-[rgba(122,90,18,0.28)] bg-[rgba(208,164,94,0.14)] text-[#7a5a12]",
    error: "border-[rgba(157,55,48,0.28)] bg-[rgba(157,55,48,0.10)] text-[#9d3730]",
  }[tone];
  return (
    <div className={`rounded-2xl border p-4 text-sm ${styles}`}>
      <p className="flex items-center gap-2 font-semibold">
        {tone === "ok" ? <Check className="h-4 w-4" /> : <AlertTriangle className="h-4 w-4" />}
        {title}
      </p>
      {body && <p className="mt-1">{body}</p>}
    </div>
  );
}

function Modal({
  title,
  onClose,
  children,
}: {
  title: string;
  onClose: () => void;
  children: React.ReactNode;
}) {
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [onClose]);

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4"
      onClick={onClose}
      role="presentation"
    >
      <div
        className="max-h-[90vh] w-full max-w-md overflow-y-auto rounded-2xl bg-[var(--card)] p-5 shadow-2xl"
        onClick={(e) => e.stopPropagation()}
        role="dialog"
        aria-modal="true"
        aria-label={title}
      >
        <div className="mb-4 flex items-center justify-between">
          <h2 className="text-base font-semibold dash-heading">{title}</h2>
          <button
            type="button"
            onClick={onClose}
            aria-label="Close"
            className="rounded-lg p-1.5 dash-muted transition hover:bg-black/[0.05]"
          >
            <X className="h-4 w-4" />
          </button>
        </div>
        {children}
      </div>
    </div>
  );
}
