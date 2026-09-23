"""复证来源fixture未读取stderr导致Moto阻塞；对照只改变服务日志去向。"""

import json
from pathlib import Path
import subprocess

ROOT = Path('/work/env_recipe_repair_20260919/moto_log_backpressure_probe_v5')
PY = '/opt/miniconda3/envs/testbed/bin/python'
PROBE = r'''
import array, fcntl, importlib.metadata, json, os, pathlib, socket, subprocess, termios, time, urllib.request
import boto3

def run(file_log):
    # 与来源fixture一样，父进程保持stderr管道打开且不消费；wrapper内部重定向到普通文件。
    cmd=['/opt/miniconda3/envs/testbed/bin/moto_server','s3','-p','5976']
    path=pathlib.Path('/tmp/rh2-moto-backpressure.log')
    if file_log:
        wrapper=pathlib.Path('/tmp/moto_server_file_log')
        wrapper.write_text('#!/bin/sh\nexec /opt/miniconda3/envs/testbed/bin/moto_server "$@" 2>>/tmp/rh2-moto-backpressure.log\n')
        wrapper.chmod(0o755)
        cmd[0]=str(wrapper)
    proc=subprocess.Popen(cmd,stdout=subprocess.DEVNULL,stderr=subprocess.PIPE)
    record={'mode':'file_log' if file_log else 'unread_pipe','uid':os.getuid(),'moto':importlib.metadata.version('moto')}
    try:
        url='http://127.0.0.1:5976/'
        for _ in range(100):
            try:
                urllib.request.urlopen(url,timeout=.2).close()
                break
            except OSError:
                if proc.poll() is not None:
                    raise RuntimeError('moto exited before ready')
                time.sleep(.05)
        else:
            raise TimeoutError('server startup')
        completed=0
        for i in range(4096):
            try:
                with urllib.request.urlopen(url,timeout=1) as response:
                    assert response.status==200
                    response.read()
                completed+=1
            except (TimeoutError,socket.timeout) as exc:
                record['request_timeout']=repr(exc)
                break
        record['completed_requests']=completed
        # CPython3.9未导出该常量；本探针只在Linux运行，1032是Linux F_GETPIPE_SZ。
        record['pipe_capacity']=fcntl.fcntl(proc.stderr.fileno(),getattr(fcntl,'F_GETPIPE_SZ',1032))
        available=array.array('i',[0]);fcntl.ioctl(proc.stderr.fileno(),termios.FIONREAD,available)
        record['pipe_unread_bytes']=available[0]
        record['server_status']=pathlib.Path('/proc',str(proc.pid),'status').read_text()
        if file_log:
            client=boto3.client('s3',endpoint_url=url,aws_access_key_id='testing',aws_secret_access_key='testing',region_name='us-east-1')
            client.create_bucket(Bucket='rh2-backpressure-probe')
            payload=b'actual-object-roundtrip-after-4096-requests\n'
            client.put_object(Bucket='rh2-backpressure-probe',Key='test',Body=payload)
            assert client.get_object(Bucket='rh2-backpressure-probe',Key='test')['Body'].read()==payload
            record['actual_object_roundtrip']=True
            record['server_log_bytes']=path.stat().st_size
            assert completed==4096 and record['server_log_bytes']>record['pipe_capacity'],record
        else:
            assert completed<4096 and 'request_timeout' in record,record
            # 小探针内只排空日志，验证同一服务恢复；不干预正在评分的容器。
            assert record['pipe_unread_bytes']>0
            record['drained_bytes']=len(os.read(proc.stderr.fileno(),record['pipe_unread_bytes']))
            with urllib.request.urlopen(url,timeout=2) as response:
                assert response.status==200
                response.read()
            record['recovered_after_log_drain']=True
    finally:
        proc.terminate()
        try:
            _,err=proc.communicate(timeout=10)
        except subprocess.TimeoutExpired:
            proc.kill();_,err=proc.communicate(timeout=10)
        record['server_returncode']=proc.returncode
        record['stderr_tail']=err[-600:].decode(errors='replace')
    return record

print(json.dumps({'results':[run(False),run(True)]}))
'''


def main():
    ROOT.mkdir(exist_ok=False)
    (ROOT/'probe_script.py').write_text(Path(__file__).read_text())
    image = json.loads((ROOT.parent/'modin_s3_compat_v1/tasks/modin-project__modin-6937/image.json').read_text())['image_id']
    name = 'rh2-er19-moto-log-backpressure'
    subprocess.run(['docker','run','-d','--name',name,'--init','--network','none','--memory','2g',
                    '--cpus','1','--pids-limit','512',image,'sleep','infinity'],check=True,stdout=subprocess.DEVNULL)
    result = None
    try:
        with (ROOT/'install.log').open('w') as stream:
            subprocess.run(['docker','exec',name,PY,'-I','-m','pip','install','--no-index',
                            '--find-links=/opt/rh2/compat-wheels','--no-deps','moto==4.2.14'],
                           check=True,stdout=stream,stderr=subprocess.STDOUT,timeout=120)
        result = subprocess.run(['docker','exec','--user','54322','-e','AWS_EC2_METADATA_DISABLED=true',
                                 name,PY,'-I','-c',PROBE],text=True,capture_output=True,timeout=150)
        (ROOT/'probe.stdout').write_text(result.stdout)
        (ROOT/'probe.stderr').write_text(result.stderr)
        subprocess.run(['docker','cp',name+':/tmp/rh2-moto-backpressure.log',str(ROOT/'server.log')],check=False)
        result.check_returncode()
    finally:
        subprocess.run(['docker','rm','-f','-v',name],check=True,stdout=subprocess.DEVNULL)
        assert not subprocess.check_output(['docker','ps','-aq','--filter','name=^/'+name+'$'],text=True).strip()
    (ROOT/'result.json').write_text(json.dumps({
        'image_id':image,'scope':'service logging only, not complete SWE scoring','probe':PROBE,
        'result':json.loads(result.stdout),'container_removed':True,
    },ensure_ascii=False,indent=2)+'\n')
    print(result.stdout)


if __name__ == '__main__':
    main()
