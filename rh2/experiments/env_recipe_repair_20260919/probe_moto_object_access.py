"""核对来源本地S3资产的真实读取，区分双侧同报403和成功读取。"""

import json
from pathlib import Path
import subprocess

ROOT = Path('/work/env_recipe_repair_20260919/moto_object_access_probe_v1')
PY = '/opt/miniconda3/envs/testbed/bin/python'
PROBE = r'''
import hashlib, importlib.metadata, json, os, pathlib, subprocess, time, urllib.request
import boto3
from botocore import UNSIGNED
from botocore.config import Config
from botocore.exceptions import ClientError

path=pathlib.Path('/testbed/modin/pandas/test/data/test_data.json')
data=path.read_bytes()
url='http://127.0.0.1:5978/'
log=pathlib.Path('/tmp/rh2-moto-object-access.log')
record={'uid':os.getuid(),'moto':importlib.metadata.version('moto'),
        'source_asset':str(path),'source_bytes':len(data),'source_sha256':hashlib.sha256(data).hexdigest()}
with log.open('wb') as stream:
    proc=subprocess.Popen(['/opt/miniconda3/envs/testbed/bin/moto_server','s3','-p','5978'],
                          stdout=subprocess.DEVNULL,stderr=stream)
    try:
        for _ in range(100):
            try:
                urllib.request.urlopen(url,timeout=.2).close();break
            except OSError:
                if proc.poll() is not None:raise RuntimeError('moto exited before ready')
                time.sleep(.05)
        else:raise TimeoutError('server startup')
        common={'endpoint_url':url,'region_name':'us-west-2'}
        signed=boto3.client('s3',**common,aws_access_key_id='foobar_key',aws_secret_access_key='foobar_secret')
        unsigned=boto3.client('s3',**common,config=Config(signature_version=UNSIGNED))
        different=boto3.client('s3',**common,aws_access_key_id='123',aws_secret_access_key='123')
        bucket='rh2-source-fixture-probe';key='modin-bugs/test_data.json'
        signed.create_bucket(Bucket=bucket,CreateBucketConfiguration={'LocationConstraint':'us-west-2'})
        signed.put_object(Bucket=bucket,Key=key,Body=data)
        def read(client):
            try:
                response=client.get_object(Bucket=bucket,Key=key)
                content=response['Body'].read()
                return {'http_status':response['ResponseMetadata']['HTTPStatusCode'],
                        'actual_bytes':len(content),'equal_source_bytes':content==data}
            except ClientError as exc:
                return {'http_status':exc.response['ResponseMetadata']['HTTPStatusCode'],
                        'error_code':exc.response['Error']['Code'],'equal_source_bytes':False}
        record['private_object']={'signed':read(signed),'anonymous':read(unsigned),'other_dummy_key':read(different)}
        signed.put_object_acl(Bucket=bucket,Key=key,ACL='public-read')
        record['public_read_object']={'signed':read(signed),'anonymous':read(unsigned),'other_dummy_key':read(different)}
        record['acl']=signed.get_object_acl(Bucket=bucket,Key=key)['Grants']
        assert record['private_object']['signed']['equal_source_bytes']
        assert record['private_object']['anonymous']['http_status']==403
        assert all(x['equal_source_bytes'] for x in record['public_read_object'].values())
    finally:
        proc.terminate()
        try:proc.wait(timeout=10)
        except subprocess.TimeoutExpired:proc.kill();proc.wait(timeout=10)
        record['server_returncode']=proc.returncode
record['server_log_bytes']=log.stat().st_size
print(json.dumps(record))
'''


def main():
    ROOT.mkdir(exist_ok=False)
    (ROOT/'probe_script.py').write_text(Path(__file__).read_text())
    image=json.loads((ROOT.parent/'modin_s3_compat_v3/tasks/modin-project__modin-6937/image.json').read_text())['image_id']
    name='rh2-er19-moto-object-access'
    subprocess.run(['docker','run','-d','--name',name,'--init','--network','none','--memory','2g',
                    '--cpus','1','--pids-limit','128',image,'sleep','infinity'],check=True,stdout=subprocess.DEVNULL)
    result=None
    try:
        with (ROOT/'install.log').open('w') as f:
            subprocess.run(['docker','exec',name,PY,'-I','-m','pip','install','--no-index',
                            '--find-links=/opt/rh2/compat-wheels','--no-deps','moto==4.2.14'],
                           check=True,stdout=f,stderr=subprocess.STDOUT,timeout=120)
        result=subprocess.run(['docker','exec','--user','54322','-e','AWS_EC2_METADATA_DISABLED=true',
                               name,PY,'-I','-c',PROBE],text=True,capture_output=True,timeout=120)
        (ROOT/'probe.stdout').write_text(result.stdout)
        (ROOT/'probe.stderr').write_text(result.stderr)
        subprocess.run(['docker','cp',name+':/tmp/rh2-moto-object-access.log',str(ROOT/'server.log')],check=False)
        result.check_returncode()
    finally:
        subprocess.run(['docker','rm','-f','-v',name],check=True,stdout=subprocess.DEVNULL)
        assert not subprocess.check_output(['docker','ps','-aq','--filter','name=^/'+name+'$'],text=True).strip()
    (ROOT/'result.json').write_text(json.dumps({
        'image_id':image,'scope':'source fixture object access microprobe; not complete task scoring',
        'result':json.loads(result.stdout),'container_removed':True,
    },indent=2)+'\n')
    print(result.stdout)


if __name__ == '__main__':
    main()
