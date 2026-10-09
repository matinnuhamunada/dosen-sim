# Assumptions and parameters

Every modelling assumption and parameter, with its source. **All numeric regulation and
environment values are currently placeholders** (`TODO(source)`): obviously fake round
numbers so the engine runs. None of them is a real regulation value.

Status legend: **TODO** = placeholder awaiting a source; **struct** = structural modelling
choice; **fact** = calendar or definitional fact.

## Regulation — `configs/regulations/national.yaml`

| Parameter | Placeholder value | Status | Needed source |
| --- | --- | --- | --- |
| `time.weeks_per_semester` | 16 | TODO | Effective working weeks per semester |
| `time.hours_per_week` | 40 | TODO | Weekly hour budget (incl. rest) |
| `time.months_per_semester` | 6 | fact | Two semesters per year |
| `workload.duty_activities` | teaching, research, supervision, community_service, admin | struct | External work and rest are not regulated duty |
| `workload.activity_category` | teaching, supervision → education; admin → support | struct | Tridharma mapping; confirm supervision → education |
| `workload.min_duty_hours_per_week` | 20 | TODO | Minimum workload (BKD); real rule is in SKS |
| `workload.max_duty_hours_per_week` | 36 | TODO | Maximum workload; real rule is in SKS |
| `workload.min_share.education` | 0.2 | TODO | Tridharma balance rule |
| `workload.min_share.research` | 0.1 | TODO | Tridharma balance rule |
| `workload.min_share.community_service` | 0.05 | TODO | Tridharma balance rule |
| `credit_table.teaching_hours` | 0.01 pt/h, cap 10/semester | TODO | KUM credit for teaching (real: per SKS) |
| `credit_table.supervision_hours` | 0.01 pt/h | TODO | KUM credit for supervision (real: per student/thesis) |
| `credit_table.community_outputs` | 1.0 pt/output | TODO | KUM credit for community service |
| `credit_table.admin_hours` | 0.005 pt/h, cap 5/semester | TODO | KUM credit for support activities |
| `credit_table.grant_awarded` | 5.0 | TODO | Credit (if any) for winning a grant |
| `credit_table.publication_*` | 10 / 20 / 30 / 40 | TODO | KUM credit per journal tier |
| `journal_tiers` | national < national_accredited < international < international_reputable | struct | Confirm tier list (e.g. SINTA levels) |
| `degrees` | master < doctorate | struct | |
| `career.ranks` names | Asisten Ahli, Lektor, Lektor Kepala, Profesor | struct | Confirmed by user (2026-10-09) |
| `career.ranks[*].min_semesters_in_rank` | 4 / 4 / 6 | TODO | Minimum time in rank |
| `career.ranks[*].min_cumulative_credit` | 200 / 400 / 800 | TODO | Cumulative KUM per rank |
| `career.ranks[*].min_share_in_rank.research` | 0.3 / 0.4 / 0.5 | TODO | Minimum research share of new credit |
| `career.ranks[*].max_share_in_rank.community_service` | 0.2 each | TODO | Cap on community-service share |
| `career.ranks[*].min_publications` | ≥1 national / ≥1 accredited / ≥1 reputable intl. | TODO | Publication prerequisites |
| `career.ranks[*].required_degree` | master / master / doctorate | TODO | Degree prerequisites |
| `certification.min_rank` | Asisten Ahli | TODO | Serdos eligibility |
| `certification.min_semesters_service` | 4 | TODO | Serdos eligibility |
| `pay.base_salary_by_rank` | 1.0 / 2.0 / 3.0 / 4.0 M IDR | TODO | Real base salary depends on civil-service grade (golongan), not rank |
| `pay.seniority_increment_per_year` | 10 000 IDR | TODO | Periodic salary step |
| `pay.functional_allowance_by_rank` | 100k / 200k / 300k / 400k IDR | TODO | Functional allowance table |
| `pay.professional_allowance_multiplier` | 1.0 × base | TODO | Professional (certification) allowance |
| `pay.honorary_allowance_multiplier_by_rank` | Profesor 1.0 × base | TODO | Professor's honorary allowance |
| `pay.remuneration` | disabled | struct | National baseline has no institutional remuneration |
| `pay.external_rate_per_hour` | 100 000 IDR | TODO | Market rate for consulting / external work |

## Local override — `configs/regulations/ptnbh.yaml`

| Parameter | Placeholder value | Status | Needed source |
| --- | --- | --- | --- |
| `pay.remuneration.base_by_rank` | 0.5 / 1.0 / 1.5 / 2.0 M IDR/month | TODO | PTNBH remuneration scheme |
| `pay.remuneration.per_credit_point` | 10 000 IDR | TODO | PTNBH performance pay |

## Environment — `configs/scenarios/baseline.yaml`

| Parameter | Placeholder value | Status | Needed source |
| --- | --- | --- | --- |
| `production.research` | scale 0.05, alpha 0.7, sigma 0.3 | TODO | Manuscripts per semester-hour; literature + expert elicitation |
| `production.community_service` | scale 0.05, alpha 0.7, sigma 0.3 | TODO | Expert elicitation |
| `journals.*.accept_prob` | 0.7 / 0.5 / 0.3 / 0.15 | TODO | SINTA / Scopus aggregates |
| `journals.*.lag_semesters` | 1 / 1 / 2 / 2 | TODO | Typical decision times |
| `grants.base_prob` | 0.1 | TODO | Grant success rates |
| `grants.prob_per_publication` | 0.02 | TODO | Track-record effect |
| `grants.max_prob` | 0.5 | TODO | |
| `grants.duration_semesters` | 4 | TODO | |
| `grants.research_multiplier` | 1.5 | TODO | Productivity effect of funding |

## Structural assumptions (M1)

1. **Classic cumulative-KUM scheme.** Credits accumulate over a career; promotion needs a cumulative total plus category-share rules on credit earned *in the current rank*. Assumed for now (user, 2026-10-09); newer regulations may differ.
2. **Credits in rank reset on promotion**; there is no carry-over of excess credit into the new rank's share calculation. The cumulative total is kept.
3. **Promotion is immediate** once eligible, evaluated at the end of each semester. Committee delay and strictness arrive with `institution/` in M3.
4. **Certification is automatic** once eligible; there is no exam or quota.
5. **Pay is gross.** Tax and deductions are not modelled. Pay is computed at the rank held during the semester; a promotion affects the next semester.
6. **Years of service** = whole years of semesters served; the seniority step is linear per year.
7. **Professional and honorary allowances** are multiples of base salary, including the seniority step.
8. **Production** = `scale × hours^alpha × lognormal(mean 1, sigma)`, with alpha < 1 for diminishing returns. Fractional research output accumulates into whole manuscripts (a production lag).
9. **Journals:** the acceptance decision is drawn at submission and revealed after `lag_semesters`. Rejected manuscripts return to the pool and may be resubmitted. Every ready manuscript is submitted to the single tier the agent chooses that semester.
10. **Grants:** success probability is `min(max_prob, base + slope × total publications)`. A grant raises research productivity from the next semester for `duration_semesters`.
11. **Teaching, supervision and admin** credit is linear in hours (subject to caps). Teaching quality and student throughput are not modelled in M1.
12. **No burnout, roles or negotiation in M1.** Rest hours have no effect yet (M3).
13. **Degree is fixed** in M1; there is no doctoral study.
14. **Workload is validated in hours per week**, whereas the real rule is in SKS. An SKS ↔ hours conversion is needed (TODO(source)).
15. **Invalid allocations abort the run** in M1. A fallback policy comes later.
