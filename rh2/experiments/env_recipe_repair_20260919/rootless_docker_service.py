"""单题rootless Docker侧车；没有宿主socket/挂载，外层共享指定的无网络namespace。"""
from pathlib import Path
import json
import subprocess
import time

COMMAND=(
    'mkdir -p "$XDG_RUNTIME_DIR" && chmod 700 "$XDG_RUNTIME_DIR" && '
    'exec rootlesskit --net=vpnkit --port-driver=builtin -p 127.0.0.1:2375:2375/tcp '
    '--copy-up=/etc --copy-up=/run --propagation=rslave '
    'dockerd --tls=false --host=tcp://0.0.0.0:2375 --host=unix:///tmp/rootless-runtime/docker.sock '
    '--storage-driver=vfs --iptables=false --ip6tables=false --ip-forward=false --ip-masq=false'
)


def call(args,**kwargs):
    return subprocess.run(args,text=True,capture_output=True,timeout=120,check=True,**kwargs)


def start(name,network,image,evidence):
    evidence.mkdir(parents=True,exist_ok=True)
    args=['docker','run','-d','--name',name,'--user','1000:1000','--cap-drop=ALL','--cap-add=SETUID',
          '--cap-add=SETGID','--security-opt','seccomp=unconfined','--security-opt','apparmor=unconfined',
          '--security-opt','systempaths=unconfined','--memory','2g','--cpus','1','--pids-limit','512',
          '--network',network,'--device','/dev/net/tun','-e','XDG_RUNTIME_DIR=/tmp/rootless-runtime','--entrypoint','sh',image,'-c',COMMAND]
    (evidence/'launch.json').write_text(json.dumps(args,indent=2)+'\n')
    call(args)
    for _ in range(30):
        p=subprocess.run(['docker','exec',name,'docker','-H','tcp://127.0.0.1:2375','info','--format','{{json .}}'],
                         text=True,capture_output=True,timeout=10)
        if p.returncode==0:
            (evidence/'info.json').write_text(p.stdout)
            version=call(['docker','exec',name,'docker','-H','tcp://127.0.0.1:2375','version','--format','{{json .Server}}'])
            (evidence/'version.json').write_text(version.stdout)
            info=json.loads(call(['docker','inspect',name]).stdout)[0]
            assert info['Config']['User']=='1000:1000' and not info['HostConfig']['Privileged']
            assert not info['HostConfig'].get('Binds') and all(m['Type']=='volume' for m in info['Mounts'])
            (evidence/'inspect.json').write_text(json.dumps(info,indent=2)+'\n')
            return
        time.sleep(1)
    raise RuntimeError('isolated Docker daemon did not become ready')


def load(name,archives,evidence):
    for archive in archives:
        with Path(archive).open('rb') as f:
            p=subprocess.run(['docker','exec','-i',name,'docker','-H','tcp://127.0.0.1:2375','load'],
                             stdin=f,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,timeout=180,check=True)
        (evidence/(Path(archive).stem+'.load.log')).write_bytes(p.stdout)


def stop(name,evidence):
    p=subprocess.run(['docker','logs',name],capture_output=True,timeout=20)
    (evidence/'daemon.log').write_bytes(p.stdout+p.stderr)
    subprocess.run(['docker','rm','-f','-v',name],capture_output=True,timeout=30)
    p=subprocess.run(['docker','inspect',name],capture_output=True,timeout=10)
    (evidence/'cleanup.json').write_text(json.dumps({'removed':p.returncode!=0})+'\n')
    if p.returncode==0:raise RuntimeError('isolated Docker sidecar still exists')
