#!/usr/bin/env bash
# Build the static viewer with bundled example runs and commit it to the cf-pages branch
# (Cloudflare Pages: no build command, output directory "/"). Run from the repo root.
set -euo pipefail
root=$(git rev-parse --show-toplevel)
cd "$root"
out=viewer/public/runs
rm -rf "$out"
for c in baseline teaching_cap reward_supervision reward_community; do
  .venv/bin/lecsim run "configs/scenarios/policies/$c.yaml" --seed 1 --out "$out/policy_experiments" >/dev/null
done
.venv/bin/lecsim run configs/scenarios/archetypes.yaml --seed 1 --out "$out" >/dev/null
.venv/bin/lecsim run configs/scenarios/department_stress.yaml --seed 1 --out "$out" >/dev/null
.venv/bin/lecsim run configs/scenarios/faculty_case.yaml --seed 1 --out "$out" >/dev/null
(cd viewer && npm test --silent && npm run build --silent)

src=$(git rev-parse --short HEAD)
wt=$(mktemp -d)
trap 'git worktree remove --force "$wt"' EXIT
if git show-ref --quiet refs/heads/cf-pages; then
  git worktree add -q "$wt" cf-pages
else
  git worktree add -q --orphan -b cf-pages "$wt"
fi
find "$wt" -mindepth 1 -maxdepth 1 ! -name .git -exec rm -rf {} +
cp -r viewer/dist/. "$wt/"
git -C "$wt" add -A
git -C "$wt" commit -q -m "Static viewer build from $src" || echo "cf-pages: no changes"
echo "cf-pages updated; push with: git push origin cf-pages"
