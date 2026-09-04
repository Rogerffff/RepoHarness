# rh2-sandbox-script: grader-protect-control-surface v1
set -u
TB=/testbed; UIDV=54322; EXPECTED=1
chown -R "$UIDV:$UIDV" "$TB" || { echo "RH2_PROTECT_ERROR=chown_candidate_failed"; exit 4; }
PROTECTED=0; DIRS=0; MISSING=""; MISSING_N=0; IRREGULAR=""
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
  elif [ -e "$p" ] || [ -L "$p" ]; then
    IRREGULAR="$IRREGULAR$f,"
  else
    MISSING="$MISSING$f,"; MISSING_N=$((MISSING_N+1))
  fi
  protect_dirs "$p"
done
chown 0:0 -- "$TB" && chmod 1777 -- "$TB" || { echo "RH2_PROTECT_ERROR=testbed_root"; exit 4; }
for f in tests/test_example.py; do
  p="$TB/$f"
  if [ -f "$p" ] && [ ! -L "$p" ]; then st=$(stat -c '%u %a' -- "$p"); [ "$st" = "0 644" ] || { echo "RH2_PROTECT_ERROR=verify_file:$f:$st"; exit 4; }; fi
  d=$(dirname -- "$p")
  while :; do
    case "$d" in "$TB"|"$TB"/*) ;; *) break ;; esac
    if [ -d "$d" ]; then st=$(stat -c '%u %a' -- "$d"); [ "$st" = "0 1777" ] || { echo "RH2_PROTECT_ERROR=verify_dir:$d:$st"; exit 4; }; fi
    [ "$d" = "$TB" ] && break
    d=$(dirname -- "$d")
  done
done
echo "EXPECTED_FILES=$EXPECTED"; echo "PROTECTED_FILES=$PROTECTED"; echo "PROTECTED_DIRS=$DIRS"
echo "MISSING_FILES=$MISSING"; echo "MISSING_FILES_COUNT=$MISSING_N"; echo "IRREGULAR_FILES=$IRREGULAR"
echo "TESTBED_STAT=$(stat -c '%u %a' -- "$TB")"
[ -z "$IRREGULAR" ] || { echo "RH2_PROTECT_ERROR=official_test_file_not_regular:$IRREGULAR"; exit 5; }
[ "$MISSING_N" = "0" ] || { echo "RH2_PROTECT_ERROR=official_test_file_missing:$MISSING"; exit 5; }
[ "$PROTECTED" -eq "$EXPECTED" ] || { echo "RH2_PROTECT_ERROR=coverage_mismatch:$PROTECTED!=$EXPECTED"; exit 5; }
echo "RH2_PROTECT_OK=1"
