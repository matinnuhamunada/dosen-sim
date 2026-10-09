// Parse a lecsim JSONL event log into a replay model. The viewer is read-only: everything
// shown is derived from the log, never from the simulator.

export interface Persona {
  w_rank: number;
  w_pay: number;
  w_wellbeing: number;
  discount: number;
}

export interface RunInfo {
  scenario: string;
  horizon: number;
  regulation_version: string;
  rank_names: string[];
  activities: string[];
  credit_categories: string[];
  journal_tiers: string[];
  hours_per_week: number;
  income_ref: number;
  semesters_per_year: number;
  roles: string[];
  archetypes: Record<string, Persona>;
  lecturers: Record<string, { policy: string; archetype: string | null }>;
}

export interface Header {
  scenario: string;
  seed: number;
  config_hash: string;
  git_commit: string;
  lecsim_version: string;
}

export interface AgentSem {
  t: number;
  hours: Record<string, number>;
  commitments: Record<string, number>;
  paidRank: string; // rank held during the semester
  rank: string; // rank at the end of the semester (after any promotion)
  income: number;
  cumIncome: number;
  burnout: number;
  credits: Record<string, number>;
  publications: number;
  roles: string[];
  committees: string[];
  coauthor: string | null;
  age: number | null; // end of semester; null when ages are not modelled
  probation: boolean; // on probation during this semester
  mentor: string | null;
}

export type EventKind =
  | "paper"
  | "promotion"
  | "grant"
  | "role"
  | "committee"
  | "teaching"
  | "coauthor"
  | "attrition"
  | "retirement"
  | "mentor"
  | "hire"
  | "certified";

export interface KeyEvent {
  t: number;
  kind: EventKind;
  agent: string;
  text: string;
  outcome?: string;
}

export interface Agent {
  id: string;
  policy: string;
  archetype: string | null;
  hiredAt: number;
  leftAt: number | null;
  sems: Map<number, AgentSem>;
  events: KeyEvent[];
  grants: number;
}

export interface DeptSem {
  t: number;
  active: number;
  demand: number;
  coverage: number;
  meanBurnout: number;
  roles: number;
  pairs: number;
}

export interface Run {
  name: string;
  header: Header;
  info: RunInfo;
  agents: Map<string, Agent>;
  dept: DeptSem[];
  events: Map<number, KeyEvent[]>; // by semester
  semesters: number; // semesters actually present in the log
}

type Raw = Record<string, any>; // eslint-style escape: log events are open-ended JSON

export function parseLog(text: string, name = "run"): Run {
  const lines = text.split("\n").filter((l) => l.trim().length > 0);
  if (lines.length < 2) throw new Error("empty event log");
  const header = JSON.parse(lines[0]) as Header & { type: string };
  if (header.type !== "header") throw new Error("first line is not a lecsim run header");
  const raw: Raw[] = lines.slice(1).map((l) => JSON.parse(l));
  const infoEv = raw.find((e) => e.type === "run_info");
  if (!infoEv) throw new Error("log has no run_info event (written by lecsim >= M4)");
  const info = infoEv as unknown as RunInfo;

  const agents = new Map<string, Agent>();
  const getAgent = (id: string, policy?: string, archetype?: string | null, t = 0): Agent => {
    let a = agents.get(id);
    if (!a) {
      const known = info.lecturers[id];
      a = {
        id,
        policy: policy ?? known?.policy ?? "?",
        archetype: archetype !== undefined ? archetype : (known?.archetype ?? null),
        hiredAt: t,
        leftAt: null,
        sems: new Map(),
        events: [],
        grants: 0,
      };
      agents.set(id, a);
    }
    return a;
  };
  for (const id of Object.keys(info.lecturers)) getAgent(id);

  const pending = new Map<string, Partial<AgentSem>>(); // key `${agent}@${t}`
  const part = (agent: string, t: number) => {
    const k = `${agent}@${t}`;
    let p = pending.get(k);
    if (!p) pending.set(k, (p = { t }));
    return p;
  };
  const dept: DeptSem[] = [];
  const events = new Map<number, KeyEvent[]>();
  const push = (ev: KeyEvent) => {
    getAgent(ev.agent).events.push(ev);
    if (!events.has(ev.t)) events.set(ev.t, []);
    events.get(ev.t)!.push(ev);
  };

  for (const e of raw) {
    const t: number = e.t;
    switch (e.type) {
      case "allocation": {
        const p = part(e.agent, t);
        p.hours = e.hours;
        p.commitments = e.commitments ?? {};
        break;
      }
      case "pay": {
        const p = part(e.agent, t);
        p.paidRank = e.rank;
        p.income = e.semester.total;
        break;
      }
      case "snapshot": {
        const s = e.state;
        const a = getAgent(e.agent, s.policy, s.archetype, s.hired_at);
        a.hiredAt = s.hired_at;
        const p = part(e.agent, t);
        Object.assign(p, {
          rank: s.rank,
          cumIncome: s.cumulative_income,
          burnout: s.burnout,
          credits: s.credits_total,
          publications: Object.values(s.publications as Record<string, number>).reduce(
            (x, y) => x + y,
            0,
          ),
          roles: Object.keys(s.roles ?? {}),
          committees: Object.keys(s.committees ?? {}),
          coauthor: s.coauthor ?? null,
          age: s.age ?? null,
          probation: s.probation_until != null && t < s.probation_until,
          mentor: s.mentor ?? null,
        });
        a.sems.set(t, p as AgentSem);
        break;
      }
      case "journal_decision":
        if (e.accepted) {
          for (const author of [e.agent, ...(e.coauthors ?? [])]) {
            push({ t, kind: "paper", agent: author, text: `paper accepted (${e.tier})` });
          }
        }
        break;
      case "promotion":
        push({ t, kind: "promotion", agent: e.agent, text: `promoted to ${e.to}` });
        break;
      case "grant_application":
        if (e.awarded) {
          getAgent(e.agent).grants += 1;
          push({ t, kind: "grant", agent: e.agent, text: "grant awarded" });
        }
        break;
      case "role_assigned":
        push({ t, kind: "role", agent: e.agent, text: `${e.role} (${e.outcome})`, outcome: e.outcome });
        break;
      case "committee_assigned":
        push({ t, kind: "committee", agent: e.agent, text: `${e.committee.replaceAll("_", " ")} (${e.outcome})`, outcome: e.outcome });
        break;
      case "teaching_agreed":
        push({
          t,
          kind: "teaching",
          agent: e.agent,
          text: `teaching ${e.hours.toFixed(1)} h (${e.outcome.replace("_", " ")})`,
          outcome: e.outcome,
        });
        break;
      case "coauthorship":
        push({ t, kind: "coauthor", agent: e.agent, text: `co-authoring with ${e.partner}` });
        push({ t, kind: "coauthor", agent: e.partner, text: `co-authoring with ${e.agent}` });
        break;
      case "attrition":
        getAgent(e.agent).leftAt = t;
        push({ t, kind: "attrition", agent: e.agent, text: `left (burnout ${e.burnout.toFixed(2)})` });
        break;
      case "retirement":
        getAgent(e.agent).leftAt = t;
        push({ t, kind: "retirement", agent: e.agent, text: `retired at ${Math.floor(e.age)} (${e.rank})` });
        break;
      case "mentor_assigned":
        push({ t, kind: "mentor", agent: e.agent, text: `co-teaching with mentor ${e.mentor}` });
        push({ t, kind: "mentor", agent: e.mentor, text: `mentoring ${e.agent}` });
        break;
      case "hire":
        getAgent(e.agent, e.policy, e.archetype, t).hiredAt = t;
        push({
          t,
          kind: "hire",
          agent: e.agent,
          text: e.rank ? `hired as ${e.rank}${e.probation_until != null ? " (probation)" : ""}` : "hired",
        });
        break;
      case "certified":
        push({ t, kind: "certified", agent: e.agent, text: "certified (serdos)" });
        break;
      case "department":
        dept.push({
          t,
          active: e.active,
          demand: e.teaching_demand,
          coverage: e.teaching_coverage,
          meanBurnout: e.mean_burnout,
          roles: e.roles_filled,
          pairs: e.coauthor_pairs,
        });
        break;
    }
  }
  const semesters = dept.length > 0 ? dept[dept.length - 1].t + 1 : 0;
  return { name, header, info, agents, dept, events, semesters };
}

/** Latest semester record at or before t (agents keep their last state after leaving). */
export function semAt(agent: Agent, t: number): AgentSem | undefined {
  for (let k = t; k >= agent.hiredAt; k--) {
    const s = agent.sems.get(k);
    if (s) return s;
  }
  return undefined;
}

export function isPresent(agent: Agent, t: number): boolean {
  return t >= agent.hiredAt && (agent.leftAt === null || t < agent.leftAt);
}

export function tierOf(policy: string): string {
  // All MVP policies are rule-based; Phase 2 adds model-driven tiers.
  return ["random", "fixed_share", "threshold", "stage", "utility", "optimiser"].includes(policy)
    ? "rule-based"
    : policy;
}
