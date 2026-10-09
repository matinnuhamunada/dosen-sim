"""Helpers shared by rule-based policies: fitting shares to workload rules, tier and
logit choice. These manipulate the agent's own plan only; they compute no outcomes."""

from __future__ import annotations

import math
from collections.abc import Iterable, Mapping

import numpy as np

from lecsim.agents.base import Observation
from lecsim.config import Archetype, Persona, WorkloadRules
from lecsim.core.actions import Activity, Proposal, Response
from lecsim.rules.workload import check_commitments, check_limits, check_workload


def _move(
    h: dict[Activity, float], take: Mapping[Activity, float], give: list[Activity], amount: float
) -> None:
    """Move ``amount`` hours from ``take`` (weighted by its values) into ``give``
    (proportional to current hours, equally if all zero)."""
    if amount <= 0:
        return
    cap = sum(take.values())
    if amount > cap + 1e-9:
        raise ValueError("workload limits cannot be satisfied")
    base = {a: h[a] for a in give}
    total = sum(base.values())
    for a, w in take.items():
        h[a] = max(0.0, h[a] - amount * w / cap)
    for a in give:
        h[a] += amount * (base[a] / total if total > 0 else 1 / len(give))


def fit_to_workload(
    shares: Mapping[str, float],
    rules: WorkloadRules,
    budget: float,
    floors: Mapping[str, float] | None = None,
    ceilings: Mapping[str, float] | None = None,
) -> dict[Activity, float]:
    """Turn target shares into a valid weekly allocation with minimal reshuffling.

    0. Raise committed activities to their ``floors`` (agreed teaching load, role hours),
       taking proportionally from the other activities.
    1. Scale shares to the budget.
    2. Clamp duty hours into [min, max], moving hours between duty and free activities.
    3. Raise any tridharma category below its minimum share, taking only from other
       categories' surplus above their own minimum.
    No step takes an activity below its floor. Activities with a ``ceiling`` (probation:
    supervision 0) are cut to it first, the excess going to the same tridharma category,
    and never receive hours afterwards.
    """
    floor = {Activity(a): v for a, v in (floors or {}).items()}
    ceil = {Activity(a): v for a, v in (ceilings or {}).items()}
    h = {a: shares.get(a, 0.0) * budget for a in Activity}
    cat_of = {Activity(a): c for a, c in rules.activity_category.items()}

    def open_(acts: list[Activity]) -> list[Activity]:
        # ponytail: a capped activity never receives hours, exact for 0 ceilings only
        return [a for a in acts if a not in ceil]

    for a, cap in ceil.items():
        if h[a] > cap:
            to = open_([b for b in cat_of if cat_of[b] == cat_of.get(a)]) or [Activity.REST]
            for b in to:
                h[b] += (h[a] - cap) / len(to)
            h[a] = cap

    def free(a: Activity) -> float:
        return max(0.0, h[a] - floor.get(a, 0.0))

    short = {a: v - h[a] for a, v in floor.items() if v > h[a]}
    for a, need in short.items():
        _move(h, {b: free(b) for b in Activity if b not in short}, [a], need)

    duty_acts = [Activity(a) for a in rules.duty_activities]
    free_acts = [a for a in Activity if a not in duty_acts]
    duty = sum(h[a] for a in duty_acts)
    target = min(max(duty, rules.min_duty_hours_per_week), rules.max_duty_hours_per_week)
    if target > duty:
        _move(h, {a: free(a) for a in free_acts}, open_(duty_acts), target - duty)
    elif target < duty:
        _move(h, {a: free(a) for a in duty_acts}, open_(free_acts), duty - target)

    cats = sorted({cat_of[a] for a in duty_acts})  # sorted: set order varies across processes
    for _ in range(len(rules.min_share) + 1):  # raising duty can dilute an earlier category
        short_any = False
        for cat, lo in rules.min_share.items():
            mine = [a for a in duty_acts if cat_of[a] == cat]
            duty = sum(h[a] for a in duty_acts)
            need = lo * duty - sum(h[a] for a in mine)
            if need <= 1e-9:
                continue
            short_any = True
            # first from other categories' surplus (duty hours unchanged) ...
            donors: dict[Activity, float] = {}
            for other in cats:
                if other == cat:
                    continue
                acts = [a for a in duty_acts if cat_of[a] == other]
                surplus = sum(h[a] for a in acts) - rules.min_share.get(other, 0.0) * duty
                spare = sum(free(a) for a in acts)
                if surplus > 0 and spare > 0:
                    # split by free hours, not total hours: a floored activity can't give
                    scale = min(1.0, surplus / spare)
                    donors.update({a: free(a) * scale for a in acts})
            take = min(need, sum(donors.values()))
            _move(h, donors, open_(mine), take)
            need -= take
            # ... then from external work / rest, which also raises duty hours: x(1 - lo) = need
            if need > 1e-9:
                x = need / (1 - lo)
                if x > rules.max_duty_hours_per_week - duty + 1e-9:
                    raise ValueError("workload limits cannot be satisfied")
                _move(h, {a: free(a) for a in free_acts}, open_(mine), x)
        if not short_any:
            break

    violations = check_workload(h, rules, budget) + check_commitments(h, floor)
    violations += check_limits(h, ceil)
    if violations:
        raise ValueError(f"could not fit allocation: {violations}")
    return h


def transfer(
    shares: Mapping[str, float],
    to: Iterable[Activity],
    amount: float,
    keep: Iterable[Activity] = (),
) -> dict[str, float]:
    """Move ``amount`` of share into ``to`` (split equally), taken proportionally from all
    activities not in ``to`` or ``keep``. Capped at what is available."""
    to, keep = list(dict.fromkeys(to)), set(keep)
    out = {a: shares.get(a, 0.0) for a in Activity}
    donors = {a: v for a, v in out.items() if a not in to and a not in keep and v > 0}
    avail = sum(donors.values())
    amount = min(amount, avail)
    if amount <= 0 or not to:
        return out
    for a, v in donors.items():
        out[a] = v - amount * v / avail
    for a in to:
        out[a] += amount / len(to)
    return out


def tier_floor(obs: Observation) -> str | None:
    """Lowest tier that counts toward an unmet publication requirement, if any."""
    floors = [g.key for g in obs.gaps if g.kind == "publications"]
    return max(floors, key=obs.journal_tiers.index) if floors else None


def preferred_tier(obs: Observation, preferred: str) -> str:
    """The archetype's preferred tier, raised to the binding publication requirement."""
    floor = tier_floor(obs)
    if floor is None:
        return preferred
    return max(preferred, floor, key=obs.journal_tiers.index)


def risk_adjusted_tier(obs: Observation, persona: Persona) -> str:
    """Tier maximising discounted expected credit minus a risk penalty.

    value = c * d^(lag/p) - risk_aversion * c * sqrt(p (1 - p)), over tiers that count
    toward any unmet publication requirement.
    """
    f = obs.forecast
    floor = tier_floor(obs)
    tiers = obs.journal_tiers[obs.journal_tiers.index(floor) :] if floor else obs.journal_tiers

    def value(tier: str) -> float:
        p = f.env.journals[tier].accept_prob
        c = f.reg.credit_table[f"publication_{tier}"].points_per_unit
        if p <= 0:
            return -math.inf
        return c * persona.discount ** f.expected_delay(
            tier
        ) - persona.risk_aversion * c * math.sqrt(p * (1 - p))

    return max(tiers, key=value)


def logit_choice(utils: np.ndarray, temperature: float, rng: np.random.Generator) -> int:
    """Quantal-response choice: P(i) ∝ exp(u_i / temperature); argmax when temperature = 0."""
    if temperature <= 0:
        return int(np.argmax(utils))
    z = (utils - utils.max()) / temperature
    p = np.exp(z)
    return int(rng.choice(len(utils), p=p / p.sum()))


# --- rule-based interaction strategies (PRD: interaction strategies) -----------------
# ponytail: thresholds are module constants; move to archetype config if they need tuning.
ROLE_COOPERATION = 0.7  # cooperativeness at which a lecturer accepts a role out of duty
COAUTHOR_COOPERATION = 0.5  # cooperativeness at which an unknown partner is accepted
COAUTHOR_RESEARCH_SHARE = 0.25  # research-oriented lecturers accept co-authors anyway


def archetype_respond(arch: Archetype, obs: Observation, proposal: Proposal) -> Response:
    """Default lecturer responses to the head and to co-authorship offers.

    - teaching_load: accept up to reservation r = preferred teaching x (1 + cooperativeness),
      otherwise counter with r.
    - extra_teaching (volunteering): accept if the extra still fits under r.
    - admin_role / committee: accept if the archetype wants the admin time, or if
      cooperative and holding no role yet (volunteer's dilemma).
    - coauthor: tit-for-tat on the partner's last answer; otherwise accept if cooperative
      or research-oriented.
    """
    coop = arch.persona.cooperativeness
    budget = obs.hours_per_week
    terms = proposal.terms
    match proposal.topic:
        case "teaching_load":
            r = arch.shares.get("teaching", 0.0) * budget * (1 + coop)
            if terms["hours"] <= r + 1e-9:
                return Response(kind="accept")
            counter = Proposal(sender=obs.me.id, topic="teaching_load", terms={"hours": r})
            return Response(kind="counter", counter=counter)
        case "extra_teaching":
            r = arch.shares.get("teaching", 0.0) * budget * (1 + coop)
            ok = terms["current"] + terms["hours"] <= r + 1e-9
            return Response(kind="accept" if ok else "reject")
        case "admin_role" | "committee":
            wanted = arch.shares.get("admin", 0.0) * budget - obs.me.commitments.get("admin", 0.0)
            ok = wanted >= terms["hours"] / 2 or (coop >= ROLE_COOPERATION and not obs.me.roles)
            return Response(kind="accept" if ok else "reject")
        case "coauthor":
            last = terms.get("partner_accepted_last", -1)
            if last in (0, 1):
                ok = bool(last)
            else:
                ok = (
                    coop >= COAUTHOR_COOPERATION
                    or arch.shares.get("research", 0.0) >= COAUTHOR_RESEARCH_SHARE
                )
            return Response(kind="accept" if ok else "reject")
    return Response(kind="reject")


class ArchetypeResponder:
    """Mixin: archetype-driven ``respond`` and no-op ``reflect``."""

    arch: Archetype

    def respond(self, obs: Observation, proposal: Proposal) -> Response:
        return archetype_respond(self.arch, obs, proposal)

    def reflect(self, obs: Observation) -> None:
        return None
