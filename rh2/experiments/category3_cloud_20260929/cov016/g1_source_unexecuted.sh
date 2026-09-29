# G1 复验：--source 目录里有一个未执行、文件名含非 UTF-8 字节 0xff 的 .py
set -u
mkdir -p /tmp/g1 && cd /tmp/g1
printf 'print("main ran")\n' > main.py
python3 -c "open(b'/tmp/g1/\xff.py', 'wb').write(b'x = 1\n')" 2>/dev/null || /testbed/.venv/bin/python -c "open(b'/tmp/g1/\xff.py', 'wb').write(b'x = 1\n')"
ls -b
/testbed/.venv/bin/python -m coverage run --source=. main.py; echo "[run rc=$?]"
/testbed/.venv/bin/python -m coverage report 2>&1 | tail -3; echo "[report rc=$?]"
