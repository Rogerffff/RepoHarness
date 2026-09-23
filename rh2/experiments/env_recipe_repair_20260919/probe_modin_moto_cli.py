"""只验证旧S3 fixture需要的CLI与真实本地对象读写；不冒充题目评分。"""
from pathlib import Path
import hashlib
import json
import subprocess

ROOT = Path('/work/env_recipe_repair_20260919/modin_moto_cli_probe')
PY = '/opt/miniconda3/envs/testbed/bin/python'
PROBE = r'''
import boto3, importlib.metadata as m, json, subprocess, time, urllib.request
server = ['/opt/miniconda3/envs/testbed/bin/moto_server', 's3', '-p', '5975']
with subprocess.Popen(server, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True) as proc:
    try:
        for _ in range(100):
            if proc.poll() is not None:
                raise RuntimeError('moto CLI exited: ' + proc.stderr.read())
            try:
                urllib.request.urlopen('http://127.0.0.1:5975', timeout=0.2).close()
                break
            except OSError:
                time.sleep(0.1)
        else:
            raise TimeoutError('local server did not become ready')
        client = boto3.client('s3', endpoint_url='http://127.0.0.1:5975',
                             aws_access_key_id='testing', aws_secret_access_key='testing',
                             region_name='us-east-1')
        client.create_bucket(Bucket='rh2-fixture-probe')
        payload = b'fixture-control-bytes\n'
        client.put_object(Bucket='rh2-fixture-probe', Key='control', Body=payload)
        actual = client.get_object(Bucket='rh2-fixture-probe', Key='control')['Body'].read()
        assert actual == payload
        client.delete_object(Bucket='rh2-fixture-probe', Key='control')
        client.delete_bucket(Bucket='rh2-fixture-probe')
        print(json.dumps({'moto':m.version('moto'),'roundtrip_ok':True,'uid':__import__('os').getuid(),
                          'scope':'service capability only; not original S3 data or grading proof'}))
    finally:
        if proc.poll() is None:
            proc.terminate()
        try:
            _, stderr = proc.communicate(timeout=10)
        except subprocess.TimeoutExpired:
            proc.kill()
            _, stderr = proc.communicate(timeout=10)
        print(json.dumps({'server_returncode':proc.returncode,'stderr_tail':stderr[-2000:]}))
'''


def main():
    ROOT.mkdir(exist_ok=False)
    assets = ROOT/'assets'
    assets.mkdir()
    image = json.loads((ROOT.parent/'resources_v1/tasks/modin-project__modin-6937/image.json').read_text())['image_id']
    with (ROOT/'download.log').open('w') as f:
        subprocess.run(['docker','run','--rm','--init','--memory','1g','--cpus','1',
                        '-v',str(assets)+':/cache',image,PY,'-I','-m','pip','download',
                        '--index-url','https://pypi.org/simple','--no-deps','--only-binary=:all:',
                        '-d','/cache','moto==4.2.14'],check=True,timeout=180,stdout=f,stderr=subprocess.STDOUT)
    name = 'rh2-er19-modin-moto-cli-probe'
    subprocess.run(['docker','run','-d','--name',name,'--init','--network','none','--memory','2g','--cpus','1',
                    '-v',str(assets)+':/cache:ro',image,'sleep','infinity'],check=True,stdout=subprocess.DEVNULL)
    results = []
    try:
        for version in ['original','4.2.14']:
            if version != 'original':
                with (ROOT/'install.log').open('w') as f:
                    subprocess.run(['docker','exec',name,PY,'-I','-m','pip','install','--no-index',
                                    '--find-links=/cache','--no-deps','moto==4.2.14'],check=True,timeout=120,
                                   stdout=f,stderr=subprocess.STDOUT)
            r = subprocess.run(['docker','exec','--user','54322','-e','AWS_EC2_METADATA_DISABLED=true',
                                name,PY,'-I','-c',PROBE],text=True,capture_output=True,timeout=90)
            (ROOT/(version+'.stdout')).write_text(r.stdout)
            (ROOT/(version+'.stderr')).write_text(r.stderr)
            results.append({'version':version,'rc':r.returncode,'stdout':r.stdout,'stderr':r.stderr})
    finally:
        subprocess.run(['docker','rm','-f','-v',name],check=True,stdout=subprocess.DEVNULL)
    manifest = [{'name':p.name,'bytes':p.stat().st_size,'sha256':hashlib.sha256(p.read_bytes()).hexdigest()}
                for p in assets.iterdir() if p.is_file()]
    (ROOT/'result.json').write_text(json.dumps({'base_image':image,'assets':manifest,'probe':PROBE,
                                              'results':results},indent=2)+'\n')
    print(json.dumps([{'version':r['version'],'rc':r['rc']} for r in results]))


if __name__ == '__main__':
    main()
