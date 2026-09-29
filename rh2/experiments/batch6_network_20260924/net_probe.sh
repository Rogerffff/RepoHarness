#!/bin/bash
# 网络 Brief 事实探针：grader 容器能否在运行中接入/撤出 internal 网络；--network none 容器能否再 connect。
set -u
IMG=$(docker images --format '{{.Repository}}:{{.Tag}}' | grep -Ev '<none>' | grep -E 'python|alpine|debian|ubuntu|busybox' | head -1)
echo "IMG=$IMG"
T=rh2np$$
docker network create --internal -o com.docker.network.bridge.gateway_mode_ipv4=isolated --subnet 10.213.7.0/29 $T-net >/dev/null && echo "net_create=ok"
# 目标服务：同网络里一个监听 8080 的容器（模拟只开包索引端口的 relay）
docker run -d --rm --network $T-net --network-alias pkgidx --name $T-idx $IMG python3 -c "import http.server,socketserver;socketserver.TCPServer(('0.0.0.0',8080),http.server.SimpleHTTPRequestHandler).serve_forever()" >/dev/null && echo "idx=up"
sleep 1
# A) grader 以 internal 网络启动 → 能连 → disconnect 最后一张网络 → 不能连（容器仍在跑）
docker run -d --rm --network $T-net --name $T-g $IMG sleep 300 >/dev/null
docker exec $T-g python3 -c "import socket;s=socket.create_connection(('pkgidx',8080),timeout=3);print('A1 connect_before_disconnect=ok')" 2>&1 | tail -1
docker network disconnect $T-net $T-g && echo "A2 disconnect_last_network=ok"
docker exec $T-g python3 -c "
import socket
try:
    socket.create_connection(('pkgidx',8080),timeout=3);print('A3 connect_after_disconnect=STILL_OK')
except Exception as e: print('A3 connect_after_disconnect=refused:',type(e).__name__,str(e)[:60])" 2>&1 | tail -1
docker exec $T-g python3 -c "
import socket
try:
    socket.create_connection(('10.213.7.2',8080),timeout=3);print('A4 ip_connect_after_disconnect=STILL_OK')
except Exception as e: print('A4 ip_connect_after_disconnect=refused:',type(e).__name__,str(e)[:60])" 2>&1 | tail -1
docker inspect -f '{{json .NetworkSettings.Networks}}' $T-g | cut -c1-120 | sed 's/^/A5 networks_after=/'
docker exec $T-g sh -c 'ip -o link 2>/dev/null | cut -d: -f2 | tr -d " " | tr "\n" ","; echo' | sed 's/^/A6 links=/'
# B) 再次 connect 同一张网络（阶段重进入是否可能）
docker network connect $T-net $T-g && echo "B1 reconnect=ok"
docker exec $T-g python3 -c "import socket;socket.create_connection(('pkgidx',8080),timeout=3);print('B2 connect_after_reconnect=ok')" 2>&1 | tail -1
docker network disconnect $T-net $T-g
# C) --network none 容器能否 connect
docker run -d --rm --network none --name $T-n $IMG sleep 300 >/dev/null
docker network connect $T-net $T-n 2>&1 | sed 's/^/C1 connect_none_container: /'
# D) 断网期间已在跑的候选后台进程：connect 前建立的 TCP 连接在 disconnect 后是否被切断
docker network connect $T-net $T-g
docker exec -d $T-g python3 -c "
import socket,time
s=socket.create_connection(('pkgidx',8080),timeout=3)
t0=time.time()
try:
    s.sendall(b'GET / HTTP/1.0\r\n\r\n'); time.sleep(3)
    s.sendall(b'GET / HTTP/1.0\r\n\r\n'); r=s.recv(10)
    open('/tmp/d.txt','w').write('D3 established_conn_survives_disconnect=%r' % bool(r))
except Exception as e:
    open('/tmp/d.txt','w').write('D3 established_conn_after_disconnect=broken: %s' % type(e).__name__)
"
sleep 1; docker network disconnect $T-net $T-g && echo "D2 disconnect_with_open_conn=ok"; sleep 4
docker exec $T-g cat /tmp/d.txt; echo
docker rm -f $T-g $T-n $T-idx >/dev/null 2>&1; docker network rm $T-net >/dev/null && echo "cleanup=ok"
