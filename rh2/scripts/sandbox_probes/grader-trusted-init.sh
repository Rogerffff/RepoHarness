# rh2-sandbox-script: grader-trusted-init v1
set -u

U=rh2grader; UIDV=54322
if ! id -u "$U" >/dev/null 2>&1; then
  if command -v useradd >/dev/null 2>&1; then
    getent group "$UIDV" >/dev/null 2>&1 || groupadd -g "$UIDV" "$U"
    useradd -M -u "$UIDV" -g "$UIDV" -s /bin/bash -d "/home/$U" "$U"
  else
    echo "$U:x:$UIDV:$UIDV::/home/$U:/bin/bash" >> /etc/passwd
    echo "$U:x:$UIDV:" >> /etc/group
  fi
fi
ACT=$(id -u "$U")
if [ "$ACT" != "$UIDV" ]; then echo "RH2_INIT_ERROR=uid_mismatch:$ACT"; exit 3; fi
mkdir -p "/home/$U"
git config --system --add safe.directory '*' >/dev/null 2>&1 || true
chown 54322:54322 /home/rh2grader || { echo "RH2_INIT_ERROR=chown_failed"; exit 4; }
echo "RH2_INIT_OK=1"; echo "GRADER_UID=$ACT"
