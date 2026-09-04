# rh2-sandbox-script: grader-protect-control-surface v1
set -u
TB=/testbed; UIDV=54322
chown -R "$UIDV:$UIDV" "$TB" || { echo "RH2_PROTECT_ERROR=chown_candidate_failed"; exit 4; }
PROTECTED=0; DIRS=0; MISSING=""
protect_dirs() {
  d=$(dirname -- "$1")
  while :; do
    case "$d" in "$TB"|"$TB"/*) ;; *) break ;; esac
    if [ -d "$d" ] && [ ! -L "$d" ]; then
      chown 0:0 -- "$d" && chmod 1777 -- "$d" || { echo "RH2_PROTECT_ERROR=dir:$d"; exit 4; }
      DIRS=$((DIRS+1))
    fi
    [ "$d" = "$TB" ] && break
    d=$(dirname -- "$d")
  done
}
for f in tests/test_example.py; do
  p="$TB/$f"
  if [ -f "$p" ] && [ ! -L "$p" ]; then
    chown 0:0 -- "$p" && chmod 0644 -- "$p" || { echo "RH2_PROTECT_ERROR=file:$f"; exit 4; }
    PROTECTED=$((PROTECTED+1))
  else
    MISSING="$MISSING$f,"
  fi
  protect_dirs "$p"
done
chown 0:0 -- "$TB" && chmod 1777 -- "$TB" || { echo "RH2_PROTECT_ERROR=testbed_root"; exit 4; }
for f in tests/test_example.py; do
  p="$TB/$f"
  if [ -f "$p" ]; then st=$(stat -c '%u %a' -- "$p"); [ "$st" = "0 644" ] || { echo "RH2_PROTECT_ERROR=verify_file:$f:$st"; exit 4; }; fi
  d=$(dirname -- "$p")
  while :; do
    case "$d" in "$TB"|"$TB"/*) ;; *) break ;; esac
    if [ -d "$d" ]; then st=$(stat -c '%u %a' -- "$d"); [ "$st" = "0 1777" ] || { echo "RH2_PROTECT_ERROR=verify_dir:$d:$st"; exit 4; }; fi
    [ "$d" = "$TB" ] && break
    d=$(dirname -- "$d")
  done
done
echo "RH2_PROTECT_OK=1"; echo "PROTECTED_FILES=$PROTECTED"; echo "PROTECTED_DIRS=$DIRS"
echo "MISSING_FILES=$MISSING"; echo "TESTBED_STAT=$(stat -c '%u %a' -- "$TB")"
