#!/bin/bash
# D 重测：disconnect 前已建立的 TCP 连接，断网后能否继续收发新数据（echo 服务器，不是 HTTP 缓冲）
set -u
IMG=python:3.12-slim; T=rh2nd$$
docker network create --internal -o com.docker.network.bridge.gateway_mode_ipv4=isolated --subnet 10.213.8.0/29 $T-net >/dev/null
docker run -d --rm --network $T-net --network-alias echo --name $T-e $IMG python3 -c "
import socketserver
class H(socketserver.StreamRequestHandler):
    def handle(self):
        while True:
            line=self.rfile.readline()
            if not line: break
            self.wfile.write(b'echo:'+line); self.wfile.flush()
socketserver.ThreadingTCPServer.allow_reuse_address=True
socketserver.ThreadingTCPServer(('0.0.0.0',7000),H).serve_forever()" >/dev/null
sleep 1
docker run -d --rm --network $T-net --name $T-g $IMG sleep 300 >/dev/null
docker exec -d $T-g python3 -c "
import socket,time
s=socket.create_connection(('echo',7000),timeout=3)
s.sendall(b'one\n'); r1=s.recv(64)
open('/tmp/d.txt','w').write('D0 before_disconnect=%r\n' % r1)
time.sleep(4)   # 宿主在 +1s 断网
try:
    s.settimeout(6); s.sendall(b'two\n'); r2=s.recv(64)
    open('/tmp/d.txt','a').write('D3 after_disconnect_roundtrip=%r (SURVIVES)\n' % r2)
except Exception as e:
    open('/tmp/d.txt','a').write('D3 after_disconnect_roundtrip=broken: %s %s\n' % (type(e).__name__, str(e)[:60]))
try:
    s2=socket.create_connection(('10.213.8.2',7000),timeout=3); open('/tmp/d.txt','a').write('D4 new_conn_after_disconnect=OK\n')
except Exception as e:
    open('/tmp/d.txt','a').write('D4 new_conn_after_disconnect=refused: %s\n' % type(e).__name__)
"
sleep 1; docker network disconnect $T-net $T-g && echo "D2 disconnect_with_open_conn=ok (t=+1s)"
sleep 12; docker exec $T-g cat /tmp/d.txt
docker rm -f $T-g $T-e >/dev/null 2>&1; docker network rm $T-net >/dev/null && echo cleanup=ok
