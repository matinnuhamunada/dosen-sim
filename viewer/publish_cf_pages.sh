#!/usr/bin/env bash
# Build the static viewer with the bundled faculty-case run and commit it to the cf-pages branch
# (Cloudflare Pages: no build command, output directory "/"). Run from the repo root.
set -euo pipefail
root=$(git rev-parse --show-toplevel)
cd "$root"
out=viewer/public/runs
rm -rf "$out"
# Only the faculty case is published for now (the other scenarios stay in configs/).
.venv/bin/lecsim run configs/scenarios/faculty_case.yaml --seed 1 --out "$out" >/dev/null
# Pages rejects files over 25 MiB; the viewer gunzips in the browser.
find "$out" -name events.jsonl -exec gzip -9 {} +
cp paper/main.pdf viewer/public/paper.pdf # linked from the top bar
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
