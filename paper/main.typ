// dosen-sim manuscript. Build: see paper/README.md.
#set document(
  title: "How to win the lecturer game: an agent-based, game-theoretic simulation of an Indonesian faculty",
  author: "Matin Nuhamunada",
)
#set page(paper: "a4", margin: (x: 2.2cm, y: 2.4cm), numbering: "1")
#set text(font: ("Libertinus Serif", "New Computer Modern"), size: 10.5pt, lang: "en")
#set par(justify: true, leading: 0.62em)
#set heading(numbering: "1.1")
#set math.equation(numbering: "(1)")
#show heading.where(level: 1): it => block(above: 1.4em, below: 0.8em, it)
#show figure.caption: set text(size: 9pt)
#show table: set text(size: 8.5pt)
#show link: set text(fill: rgb("#1f4e8c"))

#let todo(body) = text(fill: rgb("#a0522d"))[#body]

// --- title block ---------------------------------------------------------------------
#align(center)[
  #text(size: 16pt, weight: "bold")[How to win the lecturer game: an agent-based, game-theoretic simulation of an Indonesian faculty]
  #v(0.8em)
  #text(size: 11pt)[Matin Nuhamunada]\
  #text(size: 9pt)[#link("mailto:matin_nuhamunada@ugm.ac.id")[matin\_nuhamunada\@ugm.ac.id]]\
  #v(0.3em)
  #text(size: 9pt, style: "italic")[Prepared with Claude (Anthropic), an AI assistant; see the AI-use statement.]\
  #text(size: 9pt)[Preprint, dosen-sim version 0.2.3 · October 2026]
]

#v(1em)
#block(inset: (x: 1.2cm))[
  #set par(justify: true)
  #text(weight: "bold")[Abstract.] Indonesian university lecturers play a long game: they divide
  limited weekly hours between the _tridharma_ duties (teaching, research, community service),
  supervision, administration, outside work and rest, under a cumulative credit system that
  decides promotion and a pay system that rewards different things. I built `dosen-sim`, an
  agent-based simulator in which rule-based lecturer agents allocate their time under
  configurable regulations, and an engine computes every credit, salary and promotion. The main
  scenario is my own faculty: 70 lecturers in 12 laboratories over 30 years, with recruitment,
  probation, a no-rank teaching-staff period, doctoral study leave, workload reporting in credit
  units (SKS) and the performance bonus that depends on it, imposed teaching, and power
  dynamics: supervisor grades with a quota on the top grade, standing, liking, lab ties,
  favouritism in access to grants and students, and seniors who pass their work to juniors
  while keeping the credit. The scenario is partly calibrated to public aggregate data (the
  faculty's publications, one semester's timetable, public pay rules), to my own payslips and
  to my own estimates. This paper describes the mechanisms, rules, parameters and calibration
  in detail. A first, descriptive comparison of new hires finds that the research maximiser wins
  on promotion, pay and burnout at once, while the archetype most devoted to teaching loses on
  all three; I discuss how this incentive structure aligns and misaligns with the _tridharma_
  purpose of higher education. A rigorous strategy comparison is left for future work. It is a personal, curiosity-driven experiment by a member of
  the Indonesian academic community. Many assumptions are mine and therefore subjective, and
  the model needs independent data validation before any result is taken seriously: the one
  untuned check so far fails, with about 64 % of lecturers reaching professor after 30 years
  against 24 % today.

  #text(weight: "bold")[Keywords:] agent-based modelling; game theory; academic careers;
  Indonesia; higher education policy; workload; power dynamics; ODD protocol
]

= Introduction

Every lecturer in Indonesia is, whether they like it or not, a player in a game with written
rules and unwritten ones. The written rules are national and institutional regulations: a
ladder of academic ranks (Asisten Ahli, Lektor, Lektor Kepala, Profesor) climbed by
accumulating credit points (_angka kredit_, here KUM) in fixed proportions across education,
research and community service; a yearly workload report (_Beban Kerja Dosen_, BKD) in credit
units (_satuan kredit semester_, SKS); a certification that unlocks a professional allowance;
and, at autonomous state universities (PTNBH), a performance bonus. The unwritten rules are the
ones every lecturer learns in the corridor: who assigns the courses, whose grade counts, who
gets the grant and the good students, who does the committee work, and who can hand their
teaching to a junior colleague and still claim it.

This project started as my own curiosity. As a junior lecturer at an Indonesian faculty I
wanted to see, in a sandbox, how one "wins" in this environment: which allocation of time
reaches professorship fastest, which earns most, which keeps a person healthy, and how the
answer changes when the institution changes its rules. It is also, frankly, a critique: by
writing the unwritten rules down as explicit mechanisms, the simulation makes them visible and
open to argument. It is not a study commissioned by anyone, and it is not a prediction of any
person's career.

The simulator, `dosen-sim` @lecsim2026, follows a few strict design rules. The engine owns the
truth: agents only choose actions, and the engine computes every outcome. Rules are pure,
unit-tested functions. Regulations live in configuration files, and every value either cites a
source or is marked as a placeholder. Every random draw comes from a seeded stream, so a run is
reproducible to the byte. Every action, message and outcome is appended to an event log, from
which all metrics and a 3D replay viewer are computed. The model is described following the
ODD protocol @grimm2006odd @grimm2020odd.

This paper documents version 0.2.3 in detail: the mechanisms (@sec-model), the agents
(@sec-agents), the rules and their parameters (@sec-rules), the department and its power
dynamics (@sec-power), the faculty case and its calibration (@sec-case), what the model shows
so far (@sec-obs), who wins and whether the game serves higher education (@sec-discussion), its
caveats (@sec-caveats) and what comes next (@sec-outlook).

= Background <sec-background>

== The lecturer career game

The setting is a single faculty of a PTNBH university. The elements below are those the
simulator encodes; values are given in @sec-rules.

- *Ranks and credit.* A lecturer is promoted when they have spent a minimum time in rank,
  accumulated a cumulative credit total, earned a minimum share of their in-rank credit from
  research, kept community service below a cap, published at least one paper at a given
  journal tier, and hold the required degree (a doctorate for Profesor). The degree itself
  counts toward the credit total @popak2019.
- *Workload and the bonus.* Each semester a lecturer reports their workload in SKS (one SKS is
  taken as 2.5 hours a week; 16 SKS is the paid norm). The faculty's performance bonus is paid
  only if teaching, supervision and research reach 12 SKS and there is at least one community
  service activity, counted on what can be claimed (assigned teaching, research with a funded
  project), not on hours actually worked. Work above 16 SKS is unpaid overtime.
- *Pay.* Monthly pay combines a base salary, a functional allowance by rank
  @perpres65_2007, a professional allowance of one base salary once certified, an honorary
  allowance of two base salaries for professors @uu14_2005, two extra salary months a year,
  meal allowances, honoraria for teaching and examining, role allowances, and the semester
  bonus. Consulting income is outside the university pay system.
- *Entry and degrees.* New lecturers must hold a doctorate and are appointed as Lektor
  @permendiktisaintek52_2025, after a one-year probation at 80 % of base salary @pp11_2017
  @pp7_1977 and, in practice, one to two years as "teaching staff" without a rank. Lecturers
  holding only a master's degree must start doctoral study leave (_tugas belajar_) within three
  years of entry or resign; during the leave they receive the base salary only.
- *Retirement.* Lecturers retire at 65, professors at 70 @uu14_2005.

== Related modelling work

Agent-based models grow social patterns from individual rules @epstein1996growing
@macal2010tutorial, and Python frameworks such as Mesa @kazil2020mesa make them routine.
`dosen-sim` borrows its interaction games from the game-theory canon: alternating-offers
bargaining @rubinstein1982bargaining for teaching loads, the volunteer's dilemma
@diekmann1985volunteer for administrative roles, tit-for-tat reciprocity @axelrod1984evolution
for co-authorship, a contest @tullock1980rent for grants, and quantal-response choice
@mckelvey1995qre for bounded rationality. Cumulative advantage @merton1968matthew and metric
gaming @strathern1997goodhart are expected emergent effects. Language-model agents
@park2023generative are planned as a later layer, but the version described here uses only
rule-based agents and no language model.

= Model overview <sec-model>

== Entities and scales

The entities are lecturers, the department (its head, structural roles, committees and
laboratories) and stochastic external processes (journals, grant agencies, a patent market).
One tick is one semester; the faculty case runs 60 semesters (30 years). A lecturer has a weekly
budget of 56 hours split across seven activities: teaching, research, supervision, community
service, administration (duty activities), external work and rest.

== The semester tick

Each semester runs six phases (@tab-tick). The engine validates every allocation against the
workload rules and commitments and aborts the run on a violation, so no agent can break a rule.

#figure(
  table(
    columns: (auto, 1fr),
    align: (left, left),
    table.header[*Phase*][*What happens*],
    [1. Events], [Grants and roles expire; retirement and burnout-driven departures; due hires join (probation, then teaching staff); journal decisions fall due; study leave starts or ends.],
    [2. Negotiation], [Probationers get mentors; unranked staff cannot supervise; the head fills roles and committees; teaching demand is assigned (imposed in the faculty case); co-authors pair.],
    [3. Allocation], [Each lecturer's policy returns weekly hours, a journal tier and a grant decision. Senior "dumpers" then pass part of their claimed hours to juniors.],
    [4. Resolution], [Research and community output are drawn; manuscripts are submitted; grants are drawn; patents advance.],
    [5. Evaluation], [Supervisors grade everyone (quota on the top grade); credit is scored and scaled by the grade; certification, pay, burnout and promotion are computed; snapshots are logged.],
    [6. Reflection], [A hook for learning agents; a no-op for the rule-based agents used here.],
  ),
  caption: [The six phases of a semester.],
) <tab-tick>

== Design principles

The engine is the single source of truth; agents receive an observation (their own state, the
rules, their promotion gaps, engine-computed forecasts) and return an action. Every stochastic
draw uses a named stream derived from the run seed, so adding a mechanism does not shift other
draws, and the same configuration and seed give an identical event log. Every run header
records the configuration hash, seed, code commit and simulator version.

= Agents and behaviour <sec-agents>

== Archetypes

Five archetypes describe what a lecturer values and how they spend a standard 40-hour week
(@tab-arch). Their objective is a per-semester utility

$ u = w_"pay" dot I / I_"ref" + w_"rank" dot k / 3 + w_"wb" dot (R / B - b), $ <eq-utility>

where $I$ is semester income, $I_"ref"$ a reference income, $k in {0, 1, 2, 3}$ the rank index,
$R$ weekly rest, $B$ the weekly budget and $b in [0, 1]$ burnout. Shares are rescaled from the
40-hour calibration to the 56-hour budget so that each archetype works the same hours; rest
takes the remainder.

#figure(
  table(
    columns: 9,
    align: (left, center, center, center, center, center, center, center, left),
    table.header[*Archetype*][$w_"rank"$][$w_"pay"$][$w_"wb"$][*Teach*][*Research*][*Admin*][*External*][*Preferred tier*],
    [research maximiser], [0.6], [0.2], [0.2], [0.15], [0.40], [0.05], [0.00], [international reputable],
    [teaching loyalist], [0.3], [0.3], [0.4], [0.40], [0.10], [0.07], [0.00], [national],
    [admin climber], [0.5], [0.4], [0.1], [0.20], [0.10], [0.30], [0.00], [national accredited],
    [external earner], [0.1], [0.8], [0.1], [0.20], [0.10], [0.10], [0.30], [national],
    [balanced strategist], [0.4], [0.4], [0.2], [0.20], [0.25], [0.08], [0.05], [international],
  ),
  caption: [Archetypes: utility weights, base shares of a 40-hour week (supervision, community service and rest omitted) and preferred journal tier. All values are my assumptions.],
) <tab-arch>

== Behaviour models

Each lecturer pairs an archetype with one of the behaviour models, all behind one `Policy`
interface (`decide_allocation`, `respond`, `reflect`):

- *Career-stage machine (`stage`)*: base shares per career stage (early, mid, pre-promotion
  push, post-promotion, senior) plus threshold rules that move time toward unmet promotion
  requirements and toward rest when burnout is high.
- *Myopic utility with logit noise (`utility`)*: evaluates about 400 candidate allocations with
  engine forecasts of credit, income and burnout, and picks one with probability
  $P(a) prop exp(U(a) \/ lambda)$, a quantal response @mckelvey1995qre with temperature
  $lambda = 0.05$.
- *Optimiser (`optimiser`)*: an exact plan of one allocation per rank under certainty-equivalent
  dynamics, re-planned at each promotion; the rational benchmark.

The faculty case assigns the 70 founders evenly across the five archetypes and three behaviour
models. Agents do not anticipate grades, workload dumping, study leave or the teaching-staff
period: they plan as if ranked and credited in full.

= Rules and parameters <sec-rules>

Values are those of the faculty case. Each has a source in the repository's
`docs/assumptions.md`; "user-stated" means my own estimate, "placeholder" means an invented
round number awaiting data.

== Workload, SKS and the bonus

The weekly budget is 56 hours (a 40-hour norm plus room for overtime and rest). Reported SKS
are claimable hours divided by 2.5: assigned teaching only, research capped at 6 SKS without a
grant (placeholder), and supervision within the lecturer's access cap. The bonus requires at
least 12 SKS of teaching, supervision and research plus at least 0.1 SKS of community service
(one activity); deans and vice deans are exempt. Overtime above 16 SKS is unpaid and causes
strain.

== Credit and promotion

Credit is scored per semester from outputs and accumulated by category (education, research,
community service, support). Publications earn 10, 20, 30 and 40 points at the national,
nationally accredited, international and reputable international tiers; co-authored papers
give the first author 60 % (placeholders). The degree counts as education credit: 150 for a
master's degree and 200 for a doctorate (my recollection of the operational guideline
@popak2019, to be checked). @tab-promo gives the promotion requirements, which are
placeholders except the degree rule. Probationers and teaching staff earn half credit for
teaching.

#figure(
  table(
    columns: 7,
    align: (left, center, center, center, center, left, left),
    table.header[*Into rank*][*Min. semesters*][*Cumulative credit*][*Research share*][*Community cap*][*Publication*][*Degree*],
    [Lektor], [4], [200], [≥ 0.3], [≤ 0.2], [1 national], [master],
    [Lektor Kepala], [4], [400], [≥ 0.4], [≤ 0.2], [1 nationally accredited], [master],
    [Profesor], [6], [800], [≥ 0.5], [≤ 0.2], [1 reputable international], [doctorate],
  ),
  caption: [Promotion requirements (shares are of credit earned in the current rank).],
) <tab-promo>

== Pay

Monthly pay is the sum of the components in @tab-pay. The bonus (10 M IDR per semester for
Asisten Ahli, 20 M for higher ranks, user-stated) is paid only when the BKD condition is met.
On probation only 80 % of the base salary is paid; teaching staff get full pay without rank
allowances; lecturers on study leave get the base salary only. Consulting is paid at a
placeholder 100,000 IDR an hour and reported separately.

#figure(
  table(
    columns: (auto, 1fr, auto),
    align: (left, left, left),
    table.header[*Component*][*Value*][*Source*],
    [Base salary], [3.5 / 4.0 / 4.5 / 5.0 M IDR (AA / L / LK / Prof)], [user-stated for Lektor; others placeholder],
    [Functional allowance], [0.375 / 0.70 / 0.90 / 1.35 M IDR], [@perpres65_2007],
    [Professional allowance], [1 × base salary, once certified], [@uu14_2005],
    [Honorary allowance], [2 × base salary, Profesor only], [@uu14_2005],
    [Extra salary months], [2 a year (13th salary, THR) on base + functional], [yearly regulation],
    [Meal allowance], [0.6 M IDR], [user-stated],
    [Honoraria], [3 M IDR, every rank], [user-stated for Lektor],
    [Role allowance], [dean 10 M, vice dean 7.5 M, head of department 4 M, programme head 3 M, lab head 1 M], [placeholder],
    [BKD bonus], [10 M (AA) or 20 M IDR per semester], [user-stated],
  ),
  caption: [Monthly pay components in the faculty case.],
) <tab-pay>

== Production, journals and grants

Research output in manuscript-equivalents per semester is

$ y = a dot h^alpha dot epsilon dot m, quad epsilon tilde "LogNormal", E[epsilon] = 1, $ <eq-prod>

with $h$ research hours in the semester (16 weeks), $a = 0.05$, $alpha = 0.7$ and noise
$sigma = 0.3$. The multiplier $m$ combines research resources by rank (0.7, 0.9, 1.2, 1.7 for
the four ranks: students, laboratory, network), a grant ($times 1.5$), a co-author
($times 1.3$), leadership networks for role holders, and burnout ($1 - 0.8 b$). Finished
manuscripts are submitted at the chosen tier and accepted with probability 0.7, 0.5, 0.3 and 0.3
(reputable, calibrated in @sec-case) after one or two semesters; rejected manuscripts are
resubmitted. A grant succeeds with probability
$min(0.5, 0.1 + 0.02 n) dot "access" + "leadership bonus"$, where $n$ is the publication count
@tullock1980rent.

== Burnout

Burnout follows

$ b_(t+1) = "clip"_([0,1]) ( b_t + s k (max(0, W_t - S)) / S - r R_t / B ), $ <eq-burnout>

where $W_t$ is real weekly work, $R_t$ rest, $S = 40$ sustainable hours, $k = 0.3$ the strain
rate, $r = 0.3$ the recovery rate, $B = 56$ and $s$ the archetype's sensitivity. Real work
differs from reported work for low-effort lecturers and under workload dumping (@sec-power).
Above $b = 0.8$ a lecturer leaves with probability 0.01 a semester; in the faculty case burnt-out
lecturers rarely leave but produce less (user-stated).

== Entry, probation, teaching staff and study leave

New hires hold a doctorate and enter as Lektor after a two-semester probation (80 % base
salary, half teaching credit, no supervision, a senior co-teaching mentor) and a further 2–4
semesters (drawn) as teaching staff: full pay without rank allowances, the same credit limits,
no roles, no certification or promotion, and no time in rank. Lecturers with a master's degree
start study leave within six semesters of entry and stay away 8–10 semesters (drawn;
user-stated 4–5 years) on base salary only, with no workload; colleagues cover their teaching.
At the start, 12 of the 16 master's-holding founders are already part-way through it
(user-stated). They return with a doctorate and 50 extra credit points.

= The department and its power dynamics <sec-power>

== Roles, committees and teaching

The faculty has a dean, three vice deans, a head of department, three programme heads and
twelve laboratory heads, each with weekly hours, a five-year term, an allowance, a minimum rank,
and leadership perks (a higher grant chance and a research network). Recurring committees
(accreditation, anniversary, summer course, seminar, events) are staffed by the vice deans, junior
staff first; seniors are often excused. Teaching is _imposed_: the head assigns each lecturer
the demand times their rank weight (0.8, 1.0, 1.0, 1.1 from Asisten Ahli to Profesor), up to
50 hours a week, and assigns any shortfall to the least-loaded lecturers.

== Assessment with a quota

Each semester the lecturer's supervisor (lab head, or the next role up the reporting chain)
scores them:

$ "score" = 1.0 dot p + 0.5 dot a + 0.3 dot ell + 0.5 dot f + 0.3 z, $ <eq-score>

where $p in [-1, 1]$ is credit relative to the department median, $a$ the supervisor's liking
of the lecturer, $ell = 1$ if they share a lab, $f$ the lecturer's standing and
$z tilde N(0, 1)$. Grades translate the score into the share of that semester's credit that
counts for promotion: _very good_ 100 %, _good_ 80 %, _fair_ 60 %, _poor_ 40 %. In practice
almost everyone is _good_ or _very good_, but _very good_ has a quota: the lecturers are ranked
and at most 30 % (placeholder) receive it; the rest drop to _good_. Grades below _good_ are
rare (score below −1).

== Standing, liking and access

Liking between two lecturers has a mutual part drawn once per pair ($N(0, 0.5)$, plus 0.3 for
the same archetype) and one-sided shifts. Standing decays by 20 % a semester, rises with
willing committee service (+0.2) and falls with consulting. Access to grants, students and
courses is

$ "access" = "clip"("base"_"rank" + 0.25 (f + a_"sup")), $ <eq-access>

with base 0.5, 0.8, 1.0, 1.0 by rank (0.4 on probation), and the dean adding 0.2 for their own
lab and 0.1 for lecturers like themselves. Weekly supervision is capped at $10 dot "access"$
hours. Structural roles go to the eligible lecturer with the highest appointment score
$0.5 dot "rank" + 0.5 f + 0.5 a + 0.3 ell + 0.3 z$; the dean is elected by mean liking and lab
size.

== Workload dumping

From observation, many seniors pass part of their work to juniors, still claim the hours and
therefore work overtime on paper without burning out. In the model, 45 % of lecturers carry
this habit (drawn once; user-stated 40–50 % of seniors) and, once Lektor Kepala or Profesor,
every semester hand 3–8 hours a week of any work (drawn) to a junior (Asisten Ahli, Lektor or
teaching staff) in their lab if possible: the most junior with probability 0.6, otherwise their
favourite. A junior absorbs at most 8 extra hours a week, and 5 % refuse (user-stated), losing
the senior's liking. The senior keeps the credit, the SKS and the pay. The junior works the
hours with no credit, taking them from rest and then from research. The junior's liking of the
senior falls by 0.2; the senior's liking of the junior and the junior's standing rise by 0.1,
which helps their grades, access and appointments. All three sizes are placeholders.

== Low effort

About 10 % of lecturers (drawn once) put in only 30–35 hours a week through minimal
preparation rather than outside work (user-stated). Their reported SKS, credit and pay are
unchanged; their real teaching time is 0.4 of the reported time (calibrated), and the rest
counts as rest for burnout.

= The faculty case and its calibration <sec-case>

The case has 70 founders (16 professors, as in the faculty's public staff directory; the
non-professor split is a placeholder) in 12 laboratories, with ages, years of service, credits
and publication histories seeded by rank. The calibration targets come from four kinds of
evidence, each used only in aggregate: (i) the faculty's journal articles 2015–2025 in OpenAlex
@priem2022openalex, with each journal's Scopus status from Wikidata; (ii) the scheduled SKS of
one semester's public timetable; (iii) public pay rules and my own payslips, which stay private
and enter the model only as rounded estimates; and (iv) my estimates as a lecturer at the
faculty. @tab-calib compares five seeds with these targets.

#figure(
  table(
    columns: (1fr, auto, auto),
    align: (left, left, left),
    table.header[*Pattern*][*Model (seeds 1–5)*][*Target*],
    [Journal tiers: national / international / reputable], [40–44 / 10–11 / 45–49 %], [33–40 / 6 / 50–59 % (record)],
    [Accepted papers a year], [297–315], [300–450 (inferred)],
    [Scheduled teaching SKS: all / Profesor], [10.4–10.6 / 10.5–10.8], [10.4 / 12 (timetable)],
    [Weekly hours worked, median (incl. consulting)], [48–49], [48–56 (mine)],
    [Low-effort lecturers, weekly hours], [30–35], [30–35 (mine)],
    [Share burnt out ($b >= 0.5$)], [12–16 %], [10–20 % (mine)],
    [Burnout departures in 30 years], [0–6], [rare (mine)],
    [Grades: very good / good / lower], [29 / 67–68 / 3–4 %], [quota / most / rare (mine)],
    [Monthly pay: certified Lektor / teaching staff], [16.8 / 11.8 M IDR], [15.7 / 10.5 M (payslips)],
    [Monthly pay: professor vice dean], [38 M IDR], [40–60 M (hearsay)],
    [Years in rank: AA→L / L→LK / LK→Prof, median], [2 / 3.5 / 5], [plausible (mine)],
    [*Hold-out (not tuned):* Profesor share of active lecturers at year 30], [64 % (median 43 of about 67; 35–52 over 30 seeds)], [24 % (16 of 68 today)],
  ),
  caption: [Calibration results. All rows but the last were used to tune parameters, so they show a calibration, not an independent validation. The last row is the one untuned check, and it fails.],
) <tab-calib>

The tier mix was matched by raising the acceptance rate of reputable international journals from
0.15 to 0.3. Paper volume needed no change: the model counts a paper once per lecturer-author,
whereas the bibliographic record counts it once, and the faculty's articles have about 2.5
faculty-affiliated authors each. Teaching demand (23.5 hours a week per lecturer at the initial
headcount) reproduces the timetable's 657 scheduled SKS. The burnout parameters (strain 0.3,
productivity penalty 0.8, departure probability 0.01) were tuned to my estimates of hours and
burnout.

#figure(
  grid(columns: 2, gutter: 8pt,
    image("figures/time_in_rank.svg", width: 100%),
    image("figures/pay_by_status.svg", width: 100%),
  ),
  caption: [Left: years in rank at promotion (five seeds). Right: monthly university pay by status, consulting and royalties excluded.],
) <fig-rank-pay>

= Preliminary observations <sec-obs>

These are observations of what the model does under my assumptions, not findings about any real
faculty.

*Imposed teaching produces chronic overtime.* With the real teaching load, nearly every
lecturer works past 40 hours (@fig-burnout, right), the bonus condition is met by most, and research time
shrinks: accepted papers fall from about 420 to about 300 a year compared with negotiated
teaching.

*Dumping lets seniors overwork on paper.* Senior dumpers average a burnout of 0.07–0.13 against
0.18–0.26 for other seniors with the same claimed duty of about 45 hours (@fig-burnout), and
juniors carry the difference. Non-dumping seniors end up more burnt out than seniors in runs
without dumping, plausibly because many were dumped on as juniors; this is not yet verified.

*The dumping trap.* Low-research juniors (teaching loyalists, external earners) who are dumped on
almost every semester stay burnt out, earn a third of a typical junior's credit, and can remain
Lektor for 10–20 years. I believe this happens in reality, if less often than the model shows.

*The master's-degree ceiling.* Before study leave was modelled, most of the long-stuck Lektor
Kepala were master's holders who could never become Profesor and waited until retirement. Study
leave and degree credit remove that ceiling (median time still in rank at the end of a run falls
from 14–18 years to about 3.5).

#figure(
  grid(columns: 2, gutter: 8pt,
    image("figures/burnout_by_group.svg", width: 100%),
    image("figures/hours.svg", width: 100%),
  ),
  caption: [Left: mean burnout over time for senior dumpers, other seniors and juniors (band: range over five seeds). Right: weekly duty hours as reported and as really worked (low effort, dumping), consulting excluded.],
) <fig-burnout>


= Discussion: who wins, and is it the right game? <sec-discussion>

== Which archetype wins

The proper test (twin runs, @sec-outlook) is still to come, but a first, descriptive answer is
possible by comparing like with like. New hires all start alike (a doctorate, probation, teaching
staff, then Lektor), so their outcomes by archetype are the cleanest comparison the current runs
allow (@tab-winner; founders grouped by starting rank show the same ordering for promotion and
papers).

#figure(
  table(
    columns: 9,
    align: (left, center, center, center, center, center, center, center, center),
    table.header[*Archetype*][*n*][*Ranks per decade*][*Pay (M IDR/yr)*][*+ consulting*][*Papers/yr*][*Burnout*][*Real duty h/wk*][*Dumped on /yr*],
    [research maximiser], [41], [1.49], [226], [2], [2.9], [0.08], [42.2], [1.7],
    [balanced strategist], [38], [1.29], [216], [12], [2.4], [0.23], [43.5], [1.8],
    [admin climber], [34], [0.99], [210], [14], [2.3], [0.22], [46.5], [2.3],
    [teaching loyalist], [38], [0.93], [198], [2], [1.9], [0.26], [45.3], [2.4],
    [external earner], [29], [0.87], [192], [21], [2.1], [0.20], [40.9], [2.0],
  ),
  caption: [Outcomes of new hires by archetype, pooled over five seeds (means per lecturer; pay is university pay, consulting shown separately; real hours include low effort and dumping).],
) <tab-winner>

Under the encoded rules the research maximiser wins on every axis at once: it is promoted
fastest, publishes most, earns the most university pay, works the fewest real hours and burns out
least. The teaching loyalist, who spends the most real hours in the classroom, is promoted
slowest, earns least from the university, burns out most and is dumped on most often. The
external earner trades promotion for consulting income and disengagement; among founders who are
already senior it has almost no burnout (0.02–0.05) and is among the most frequent dumpers. At
the top of the ladder, pay goes to those who take structural roles (admin climbers and dutiful
teaching loyalists), not to those who teach or publish more. Among behaviour models, plain
rules of thumb (the stage machine) beat myopic utility maximisation: utility agents burn out
(mean 0.36 among new hires) chasing short-term gains. The winning strategy is therefore not to
work harder but to publish in the right tier, protect research time, claim what can be claimed
and, once senior, hand work down.

This ranking is not a law of nature. It follows from the rules I encoded and the archetypes I
defined: a publication is worth 10–40 credit points while an hour of teaching is worth 0.01, so
any agent that shifts hours from teaching to research climbs faster. That is exactly the point
of the exercise: the model makes the incentive structure explicit, and the incentive structure
picks the winner.

== Alignment with the purpose of higher education

Indonesian higher education states its purpose as the _tridharma_: education, research and
community service. Judged against it, the simulated system rewards some of the right things
and many of the wrong ones.

- *Research is rewarded, but as counts.* Credit and promotion depend on the number of papers at
  each journal tier. The model's lecturers respond as the real record suggests: about half of
  the faculty's articles are in reputable international journals, many of them indexed outlets
  that publish quickly. The incentive is to reach a tier, not to answer a question; a measure
  that becomes a target stops measuring @strathern1997goodhart.
- *Teaching is the core activity and the least rewarded.* Teaching fills a quarter or more of
  every lecturer's week, yet it earns almost no promotion credit, and its quality is invisible:
  the bonus counts claimed SKS, so a lecturer who prepares minimally is paid exactly like one who
  prepares well. The archetype most devoted to students loses on every career measure.
- *Community service is a checkbox.* One activity of any size satisfies the bonus condition, and
  credit for community service is capped. The third dharma is satisfied on paper.
- *Reported work, not real work, is what counts.* Because promotion, the bonus and pay read the
  workload report, two behaviours become free: low effort (the same SKS for fewer hours) and
  workload dumping (the same SKS while a junior does the work). Both are invisible to the
  institution and both pay. The system cannot tell its most committed staff from its best
  reporters.
- *Seniority converts into extraction.* Dumping turns what should be mentorship into a transfer
  of labour from juniors to seniors. Juniors gain standing, which the model rewards with better
  grades and access, so the arrangement is self-reinforcing; those who never escape it, typically
  juniors whose interests lie in teaching, can stay burnt out and unpromoted for a decade or two.
  Cumulative advantage @merton1968matthew operates through workload, not only through citations.
- *Grades are a tournament.* A quota on "very good" makes assessment a rank-order contest for a
  fixed number of top grades, in which liking, lab ties and standing matter alongside merit. It
  rewards being visible to the right supervisor as much as doing the work.
- *Overtime is structural.* With real teaching loads, nearly every lecturer works beyond the
  paid norm; the excess is unpaid, crowds out research and produces burnout, yet the system's
  own reports show it as "meeting the BKD".
- *Some rules do align.* Requiring a doctorate and funding doctoral study leave raise the
  faculty's capacity; once modelled, they removed a ceiling that otherwise trapped the
  master's-degree holders among the senior staff. Seniority-based pay and allowances give security. The problem is less any
  single rule than the gap between what is measured (claims, counts, grades) and what the
  institution exists for (students who learn, knowledge that matters, communities that benefit).

If the simulation is even roughly right, an institution that wants its staff to serve the
_tridharma_ would measure real work rather than reported work, give teaching and mentoring real
weight in promotion, cap or audit the transfer of workload to juniors, and grade against
standards rather than quotas. These are hypotheses for the policy experiments in
@sec-outlook, not conclusions.

= Caveats and limitations <sec-caveats>

- *Subjective assumptions.* Many parameters are my own estimates as one lecturer at one faculty:
  hours, burnout, effort, dumping, the assessment quota, honoraria, study-leave timing. Others are
  placeholders. A single informant is not a sample, and my position (junior, at the receiving end
  of some of these dynamics) shapes what I see.
- *Calibration is not validation.* Nearly every target in @tab-calib was used to tune a
  parameter. The model reproduces what it was fitted to; it has not been tested on data it did
  not see (time-in-rank records, promotion ages, attrition, grant success). The one untuned
  check I ran fails (last row of @tab-calib): after 30 years about 64 % of active lecturers are
  Profesor, against 24 % today. Each promotion step looks plausible on its own, but the ladder is
  too easy overall, because the real requirements (credit, first-author papers in reputable
  journals, external review, rejections and delays) are mostly placeholders. Until it is fixed,
  results that depend on reaching Profesor, including the comparison of archetypes in
  @sec-discussion, illustrate mechanisms rather than estimate outcomes.
- *Data gaps.* The tier classification uses "ever indexed in Scopus" and misses national journals
  without DOIs; the timetable covers one semester and only scheduled classes; pay rests on one
  person's payslips and on hearsay for senior roles; the credit and promotion values are mostly
  placeholders, as are the degree credit values.
- *Behaviour.* Agents are rule-based archetypes, not people. They do not learn, do not anticipate
  grades, dumping or study leave, and cannot refuse imposed teaching. Real lecturers adapt, form
  alliances and resist.
- *Structure.* The model has no students as agents, no teaching quality, no family or health
  shocks, no outside job market and no change of regulations over 30 years. Liking and standing
  are single numbers.
- *Measurement.* Logs and metrics record reported hours; real hours can be reconstructed but are
  not yet reported by the standard metrics or the viewer.
- *Scope and ethics.* Results describe a stylised faculty under stated assumptions. They are not
  predictions or advice for any individual and must not be read as claims about named people.
  Lecturer identifiers are pseudonyms and all data are used in aggregate.

= Future outlook <sec-outlook>

- *Fix the promotion ladder.* Replace the placeholder promotion requirements with the real ones
  and recheck the professor share against today's 24 % before any strategy or policy result.
- *The strategy race.* Because lecturers start from different ranks, ages, labs and degrees, raw
  outcomes mostly reflect starting points. The planned method is twin runs: the same seed and
  initial state with one lecturer's archetype and behaviour changed, comparing that lecturer's
  outcomes, which measures a best response in the given environment. It will be cross-checked on
  the new-hire cohort, which starts alike, and reported on several outcomes (years to each rank,
  pay per year, papers per year, burnout) rather than one score.
- *Policy experiments.* Counterfactuals with ≥ 30 seeds each: no power dynamics, an
  unconditional bonus, no dumping, a different quota, negotiated instead of imposed teaching.
- *Robustness.* ±20 % perturbations of the parameters that drive results (the quota, dumping
  sizes, the effort factor, liking and standing sizes).
- *Data validation.* Faculty-level human-resources aggregates (time in rank, promotion ages,
  attrition), SINTA journal ranks, grant records, and elicitation from more lecturers at
  different ranks and faculties to replace my single perspective.
- *Learning and language-model agents.* Reinforcement learning @roth1995learning and peer
  imitation, then local and frontier language-model agents, compared with the rule-based and
  optimiser baselines; a check that agents reproduce a known game-theory result such as
  declining contributions in public goods games @fehr2000cooperation.
- *A teaching tool.* The 3D replay viewer already lets anyone follow a lecturer through 30 years;
  with real-hours reporting it could support discussion of workload policy.

= Statements

*Author contribution.* M.N. conceived the project, supplied the domain knowledge, all
user-stated assumptions and the private pay data, directed the design and analysis, and is
responsible for the content.

*AI-use statement.* The simulator code, tests, documentation, calibration analyses, figures and a
first draft of this manuscript were produced with Claude (Anthropic), an AI assistant, working
under the author's direction in Claude Code. The author reviewed the design decisions and is
accountable for the text. Claude is not an author.

*Code and data availability.* `dosen-sim` is released under the MIT License @lecsim2026; the repository is currently private and will be opened with the preprint. Every number in this paper
can be recomputed from the event logs of `configs/scenarios/faculty_case.yaml` (seeds 1–5) with
`paper/make_figures.py` and the repository's validation scripts. The payslips are private and
not included. Bibliographic and timetable data were used only in aggregate.

*Conflict of interest.* The author is a lecturer at the faculty that inspired the case and
writes partly as a critic of its working environment.

#bibliography("refs.bib", style: "apa", title: "References")
