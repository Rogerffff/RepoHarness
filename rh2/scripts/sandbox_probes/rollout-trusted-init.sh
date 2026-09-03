# rh2-sandbox-script: rollout-trusted-init v1
set -u

U=agent; UIDV=54321
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
chown -R 54321:54321 /home/agent || { echo "RH2_INIT_ERROR=chown_home_failed"; exit 4; }
if [ -d /testbed ]; then chown -R 54321:54321 /testbed || { echo "RH2_INIT_ERROR=chown_workdir_failed"; exit 4; }; echo "WORKDIR_PRESENT=1"; else echo "WORKDIR_PRESENT=0"; fi
echo "RH2_INIT_OK=1"; echo "AGENT_UID=$ACT"
