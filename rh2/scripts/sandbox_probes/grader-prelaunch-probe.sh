# rh2-sandbox-script: grader-prelaunch-probe v1
set -u

echo "UID=$(id -u)"; echo "GID=$(id -g)"
awk '/^CapEff/{print "CAPEFF="$2} /^CapPrm/{print "CAPPRM="$2} /^CapBnd/{print "CAPBND="$2} /^NoNewPrivs/{print "NNP="$2}' /proc/self/status
if [ -f /sys/fs/cgroup/pids.max ]; then
  echo "CG_VERSION=v2"
  echo "CG_PIDS_MAX=$(cat /sys/fs/cgroup/pids.max 2>/dev/null || echo unreadable)"
  echo "CG_MEMORY_MAX=$(cat /sys/fs/cgroup/memory.max 2>/dev/null || echo unreadable)"
  echo "CG_SWAP_MAX=$(cat /sys/fs/cgroup/memory.swap.max 2>/dev/null || echo unreadable)"
  echo "CG_CPU_MAX=$(cat /sys/fs/cgroup/cpu.max 2>/dev/null || echo unreadable)"
else
  echo "CG_VERSION=v1"
  echo "CG_PIDS_MAX=$(cat /sys/fs/cgroup/pids/pids.max 2>/dev/null || echo unreadable)"
  echo "CG_MEMORY_MAX=$(cat /sys/fs/cgroup/memory/memory.limit_in_bytes 2>/dev/null || echo unreadable)"
  MEMSW=$(cat /sys/fs/cgroup/memory/memory.memsw.limit_in_bytes 2>/dev/null || echo unreadable)
  MEM=$(cat /sys/fs/cgroup/memory/memory.limit_in_bytes 2>/dev/null || echo unreadable)
  if [ "$MEMSW" = "$MEM" ]; then echo "CG_SWAP_MAX=0"; else echo "CG_SWAP_MAX=$MEMSW"; fi
  echo "CG_CPU_MAX=$(cat /sys/fs/cgroup/cpu/cpu.cfs_quota_us 2>/dev/null || echo unreadable) $(cat /sys/fs/cgroup/cpu/cpu.cfs_period_us 2>/dev/null || echo unreadable)"
fi
echo "IFACES=$(ls /sys/class/net 2>/dev/null | sort | tr '\n' ',')"
echo "ROUTED_IFACES=$(awk 'NR>1{print $1}' /proc/net/route 2>/dev/null | sort -u | tr '\n' ',')"
probe() { if timeout 3 bash -c "exec 3<>/dev/tcp/$2/$3" 2>/dev/null; then echo "NET_$1=CONNECTED"; else echo "NET_$1=DENIED"; fi; }
if getent hosts example.com >/dev/null 2>&1; then echo "DNS_EXTERNAL=RESOLVED"; else echo "DNS_EXTERNAL=DENIED"; fi
echo "HOME_WRITABLE=$( [ -n "${HOME:-}" ] && [ -w "$HOME" ] && echo 1 || echo 0 )"
echo "TMP_WRITABLE=$( [ -w /tmp ] && echo 1 || echo 0 )"
probe forbidden_0 169.254.169.254 80
probe forbidden_1 1.1.1.1 443
probe forbidden_2 172.17.0.1 18001
echo "RH2_PROBE_OK=1"
