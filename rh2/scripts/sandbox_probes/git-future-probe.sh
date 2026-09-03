# rh2-sandbox-script: git-future-probe v1
set -u
R=/tmp/rh2_git_future_probe; rm -rf "$R"; mkdir -p "$R"; cd "$R"
git init -q -b main . && git config user.email p@rh2 && git config user.name rh2
echo base > f.py && git add . && git commit -qm base && BASE=$(git rev-parse HEAD)
echo 'RH2_FUTURE_SOLUTION_CANARY_5c1e' > f.py && git commit -qam fix && FUT=$(git rev-parse HEAD)
git tag v99.0 && echo more > g.py && git add . && git commit -qm later && git branch feature
git reset -q --hard "$BASE"
if git cat-file -e "$FUT" 2>/dev/null; then echo "FUTURE_BEFORE=RECOVERABLE"; else echo "FUTURE_BEFORE=GONE"; fi
( cd "$R" && (
set -u
cd /tmp/rh2_git_future_probe 2>/dev/null || { echo "RH2_GIT_SANITIZE_ERROR=no_workdir"; exit 2; }
git config --global --add safe.directory '*' >/dev/null 2>&1 || true
HEAD_BEFORE=$(git rev-parse HEAD 2>/dev/null) || { echo "RH2_GIT_SANITIZE_ERROR=no_head"; exit 2; }
COUNT_BEFORE=$(git rev-list --count HEAD)
T0=${EPOCHREALTIME:-$SECONDS}
for r in $(git remote); do git remote remove "$r" >/dev/null 2>&1 || true; done
DELETED=0
for ref in $(git for-each-ref --format='%(refname)'); do
  sha=$(git rev-parse --verify -q "$ref^{commit}" 2>/dev/null || true)
  if [ -z "$sha" ] || ! git merge-base --is-ancestor "$sha" "$HEAD_BEFORE" 2>/dev/null; then
    git update-ref -d "$ref" >/dev/null 2>&1 || git update-ref --no-deref -d "$ref" >/dev/null 2>&1 || true
    DELETED=$((DELETED+1))
  fi
done
rm -rf .git/logs .git/refs/remotes .git/lost-found .git/FETCH_HEAD .git/ORIG_HEAD .git/MERGE_HEAD .git/CHERRY_PICK_HEAD .git/REVERT_HEAD 2>/dev/null
git reflog expire --expire=now --expire-unreachable=now --all >/dev/null 2>&1 || true
git repack -a -d -q 2>/dev/null || { echo "RH2_GIT_SANITIZE_ERROR=repack_failed"; exit 2; }
git prune --expire=now 2>/dev/null || { echo "RH2_GIT_SANITIZE_ERROR=prune_failed"; exit 2; }
git worktree prune >/dev/null 2>&1 || true
UNREACHABLE=$(git fsck --unreachable --no-reflogs --connectivity-only 2>/dev/null | grep -c '^unreachable ' || true)
HEAD_AFTER=$(git rev-parse HEAD)
COUNT_AFTER=$(git rev-list --count HEAD)
T1=${EPOCHREALTIME:-$SECONDS}
echo "RH2_GIT_SANITIZE_OK=1"
echo "HEAD_BEFORE=$HEAD_BEFORE"
echo "HEAD_AFTER=$HEAD_AFTER"
echo "HISTORY_COUNT_BEFORE=$COUNT_BEFORE"
echo "HISTORY_COUNT_AFTER=$COUNT_AFTER"
echo "REFS_DELETED=$DELETED"
echo "REFS_REMAINING=$(git for-each-ref | wc -l | tr -d ' ')"
echo "REMOTES=$(git remote | wc -l | tr -d ' ')"
echo "REFLOG_ENTRIES=$(git reflog 2>/dev/null | wc -l | tr -d ' ')"
echo "UNREACHABLE_OBJECTS=${UNREACHABLE:-0}"
echo "SECONDS_ELAPSED=$(awk "BEGIN{print $T1-$T0}")"

) ) | sed 's/^/SANITIZE_/'
cd "$R"
if git cat-file -e "$FUT" 2>/dev/null; then echo "FUTURE_CATFILE=RECOVERABLE"; else echo "FUTURE_CATFILE=GONE"; fi
LOST=$(git fsck --lost-found 2>/dev/null | grep -c dangling || true); echo "FUTURE_LOSTFOUND=${LOST:-0}"
if grep -rq RH2_FUTURE_SOLUTION_CANARY_5c1e .git 2>/dev/null; then echo "FUTURE_GREP=FOUND"; else echo "FUTURE_GREP=ABSENT"; fi
if git show v99.0 >/dev/null 2>&1; then echo "FUTURE_TAG=RECOVERABLE"; else echo "FUTURE_TAG=GONE"; fi
if git rev-parse --verify -q feature >/dev/null 2>&1; then echo "FUTURE_BRANCH=RECOVERABLE"; else echo "FUTURE_BRANCH=GONE"; fi
echo "BASE_HISTORY=$(git rev-list --count HEAD)"; echo "HEAD_IS_BASE=$( [ "$(git rev-parse HEAD)" = "$BASE" ] && echo 1 || echo 0 )"
rm -rf "$R"; echo "RH2_PROBE_OK=1"
