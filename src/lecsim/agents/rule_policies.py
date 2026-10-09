"""Rule-based archetype policies: fixed share, threshold rules, career-stage machine."""

from __future__ import annotations

import numpy as np

from lecsim.agents.base import Observation
from lecsim.agents.common import ArchetypeResponder, fit_to_workload, preferred_tier, transfer
from lecsim.config import Archetype, StageRules
from lecsim.core.actions import Activity, Allocation


class FixedSharePolicy(ArchetypeResponder):
    """Constant fraction of hours per activity (repaired to the workload rules)."""

    def __init__(
        self, rng: np.random.Generator, archetype: Archetype, stages: StageRules | None = None
    ) -> None:
        self.rng = rng
        self.arch = archetype
        self.stages = stages

    def target_shares(self, obs: Observation) -> tuple[dict[str, float], dict]:
        return dict(self.arch.shares), {}

    def tier(self, obs: Observation) -> str:
        return self.arch.journal_tier

    def decide_allocation(self, obs: Observation) -> Allocation:
        shares, info = self.target_shares(obs)
        return Allocation(
            hours=fit_to_workload(shares, obs.workload, obs.hours_per_week, obs.me.commitments),
            journal_tier=self.tier(obs),
            apply_grant=self.arch.apply_grants,
            info=info,
        )


class ThresholdPolicy(FixedSharePolicy):
    """Fixed shares plus if-then rules on the engine's promotion gaps:

    - a category below its minimum in-rank share -> shift ``gap_shift`` toward it;
    - a category above its maximum share -> shift ``gap_shift`` away from it;
    - unmet publication or cumulative-credit requirement -> shift ``gap_shift`` to research;
    - publication requirement -> submit at least at the required tier;
    - burnout above the archetype's ``burnout_limit`` -> shift ``2 * gap_shift`` to rest.
    """

    def base_shares(self, obs: Observation) -> tuple[dict[str, float], dict]:
        return dict(self.arch.shares), {}

    def target_shares(self, obs: Observation) -> tuple[dict[str, float], dict]:
        shares, info = self.base_shares(obs)
        cat_acts: dict[str, list[Activity]] = {}
        for act in obs.workload.duty_activities:
            cat_acts.setdefault(obs.workload.activity_category[act], []).append(Activity(act))
        rules: list[str] = []
        boosted: list[Activity] = []
        for g in obs.gaps:
            if g.kind == "min_share":
                to = cat_acts[g.key][:1]  # primary activity of the category
            elif g.kind in ("publications", "credit"):
                to = [Activity.RESEARCH]
            elif g.kind == "max_share":
                shares = transfer(
                    shares,
                    [a for a in Activity if a not in cat_acts[g.key] and a != Activity.REST],
                    self.arch.gap_shift,
                    keep=[Activity.REST],
                )
                rules.append(f"cut:{g.key}")
                continue
            else:
                continue
            if to[0] in boosted:
                continue
            boosted.append(to[0])
            shares = transfer(shares, to, self.arch.gap_shift, keep=boosted)
            rules.append(f"{g.kind}:{g.key or ''}->{to[0]}")
        if obs.me.burnout > self.arch.burnout_limit:
            shares = transfer(shares, [Activity.REST], 2 * self.arch.gap_shift)
            rules.append("burnout->rest")
        return shares, info | {"rules": rules}

    def tier(self, obs: Observation) -> str:
        return preferred_tier(obs, self.arch.journal_tier)


def career_stage(obs: Observation, rules: StageRules) -> str:
    me = obs.me
    if any(g.kind == "top" for g in obs.gaps):
        return "senior"
    if obs.promotion_distance <= rules.push_distance:
        return "pre_promotion_push"
    if me.rank != obs.rank_names[0] and me.semesters_in_rank < rules.post_promotion_semesters:
        return "post_promotion"
    if me.semesters_service < rules.early_career_semesters:
        return "early_career"
    return "mid_career"


class StagePolicy(ThresholdPolicy):
    """Career-stage state machine: base shares per stage, then the threshold rules."""

    def base_shares(self, obs: Observation) -> tuple[dict[str, float], dict]:
        if self.stages is None:
            raise ValueError("StagePolicy needs stage rules (scenario `agents:` file)")
        stage = career_stage(obs, self.stages)
        return dict(self.arch.stage_shares.get(stage, self.arch.shares)), {"stage": stage}
