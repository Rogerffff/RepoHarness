"""仅在获分CPU主机自己的包目录和统一作业槽内执行三候选窄诊断。"""
import argparse
import base64
import datetime
import hashlib
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import tarfile
import threading
import time

ap=argparse.ArgumentParser();ap.add_argument('--out',required=True);a=ap.parse_args()
here=Path(__file__).resolve().parent;root=Path('/work/rh2-category2-20261003/packages/swe_pydantic')
out=Path(a.out).resolve();assert out.is_relative_to(root/'fieldinfo_retention_v1/outputs')
out.mkdir(parents=True,exist_ok=False)
spec=json.loads((here/'inputs.json').read_text());job=out.name
state={'schema':'swe_pydantic8511.fieldinfo_retention_actual.v1','job':job,'started_at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'status':'running','formal_reward_produced':False,'model_calls':0,'variants':{},'input_sha256':hashlib.sha256((here/'inputs.json').read_bytes()).hexdigest(),'runner_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest()}
def save(): (out/'results.json').write_text(json.dumps(state,ensure_ascii=False,indent=2)+'\n')
def stop(sig,_):raise SystemExit(128+sig)
signal.signal(signal.SIGTERM,stop);signal.signal(signal.SIGINT,stop)
for item in spec['files']:
 b=(here/item['path']).read_bytes();assert len(b)==item['bytes'] and hashlib.sha256(b).hexdigest()==item['sha256'],item['path']
manifest=json.loads((here/'baseline_manifest.json').read_text())
with tarfile.open(here/'baseline.tar') as t:
 members={m.name:m for m in t.getmembers() if m.isfile() or m.issym()}
 assert len(members)==len(manifest['entries'])==452
 for e in manifest['entries']:
  assert e['object_type']=='regular' and e['path'] in members and not Path(e['path']).is_absolute() and '..' not in Path(e['path']).parts
  m=members[e['path']];assert m.isfile() and hashlib.sha256(t.extractfile(m).read()).hexdigest()==e['content_digest'].removeprefix('sha256:')
  assert bool(m.mode&0o111)==(e['mode']=='100755')

def call(argv,name,timeout=30,stdin=None):
 started=time.time()
 if stdin is not None:(out/(name+'.stdin')).write_bytes(stdin)
 p=subprocess.run(argv,input=stdin,stdout=subprocess.PIPE,stderr=subprocess.PIPE,timeout=timeout)
 (out/(name+'.stdout')).write_bytes(p.stdout);(out/(name+'.stderr')).write_bytes(p.stderr)
 (out/(name+'.exec.json')).write_text(json.dumps({'argv':argv,'rc':p.returncode,'started':started,'ended':time.time()},ensure_ascii=False,indent=2)+'\n')
 return p
image=call(['docker','image','inspect',spec['image_id']],'image_inspect');assert image.returncode==0
im=json.loads(image.stdout)[0];assert im['Id']==spec['image_id'] and im['Architecture']=='amd64' and im['Os']=='linux'
state['actual_image_id']=im['Id'];save()
py='/opt/miniconda3/envs/testbed/bin/python';source_path='pydantic/dataclasses.py';all_created=[]

try:
 for variant in ['baseline','narrow','qwen_original']:
  vdir=out/variant;vdir.mkdir();name='rh2-pyd8511-retain-'+job[-24:]+'-'+variant
  create=call(['docker','create','--name',name,'--label','rh2.pyd8511.retention.job='+job,'--network','none','--cpus','2','--memory','4g','--memory-swap','4g','--pids-limit','512','--cap-drop','ALL','--cap-add','CHOWN','--cap-add','DAC_OVERRIDE','--security-opt','no-new-privileges','--user','0','--workdir','/testbed','--entrypoint','/bin/sh',spec['image_id'],'-c','sleep 540'],variant+'_create')
  assert create.returncode==0;cid=create.stdout.decode().strip();all_created.append(cid)
  v={'CID':cid,'name':name,'status':'preparing','resource_samples':[]};state['variants'][variant]=v;save()
  done=threading.Event();monitor=None
  try:
   assert call(['docker','start',cid],variant+'_start').returncode==0
   inspect=call(['docker','inspect',cid],variant+'_inspect');assert inspect.returncode==0
   c=json.loads(inspect.stdout)[0];h=c['HostConfig']
   assert c['Image']==spec['image_id'] and h['NetworkMode']=='none' and not c['Mounts'] and not h.get('Binds')
   assert h['NanoCpus']==2000000000 and h['Memory']==h['MemorySwap']==4294967296 and h['PidsLimit']==512
   def sample():
    while not done.is_set():
     try:
      ip=subprocess.run(['docker','inspect',cid],capture_output=True,timeout=3)
      if ip.returncode==0:
       inspected=json.loads(ip.stdout)[0];pid=inspected['State']['Pid'];row={'at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'CID':cid,'PID':pid,'image_ID':inspected['Image']}
       if pid:
        cg=next(x.split(':',2)[2] for x in Path('/proc/'+str(pid)+'/cgroup').read_text().splitlines() if x.startswith('0::'))
        base=Path('/sys/fs/cgroup')/cg.lstrip('/');row['cgroup']=str(base)
        for key in ['memory.current','memory.peak','memory.events','pids.current','pids.peak','pids.events','cpu.stat']:
         path=base/key;row[key]=path.read_text().strip() if path.exists() else None
       v['resource_samples'].append(row)
     except Exception as exc:v['resource_samples'].append({'at':time.time(),'sample_error':repr(exc)})
     done.wait(0.5)
   monitor=threading.Thread(target=sample,daemon=True);monitor.start()
   assert call(['docker','cp',str(here/'baseline.tar'),cid+':/tmp/retention_baseline.tar'],variant+'_copy_baseline').returncode==0
   # 所有路径已在宿主核为452个安全regular成员；只恢复当前自有容器。
   init="import pathlib,shutil,tarfile,os\np=pathlib.Path('/testbed')\nshutil.rmtree(p)\np.mkdir()\nwith tarfile.open('/tmp/retention_baseline.tar') as t:t.extractall('/testbed')\nfor d,ds,fs in os.walk('/testbed'):\n os.chown(d,54321,54321)\n for f in fs:os.chown(os.path.join(d,f),54321,54321)\n"
   assert call(['docker','exec','-i',cid,py,'-I','-'],variant+'_restore',stdin=init.encode()).returncode==0
   src=(here/spec['source_files'][variant]).read_bytes()
   write="from pathlib import Path\nimport base64,os\np=Path('/testbed/pydantic/dataclasses.py')\np.write_bytes(base64.b64decode("+repr(base64.b64encode(src).decode())+"))\nos.chown(p,54321,54321)\n"
   assert call(['docker','exec','-i',cid,py,'-I','-'],variant+'_write',stdin=write.encode()).returncode==0
   env=['docker','exec','--user','54321:54321','--workdir','/testbed','-e','PYTHONDONTWRITEBYTECODE=1','-e','PYTHONPATH=/testbed','-e','HOME=/tmp','-i',cid,py,'-']
   expected={e['path']:{'sha256':e['content_digest'].removeprefix('sha256:'),'execute':e['mode']=='100755'} for e in manifest['entries']};expected[source_path]['sha256']=hashlib.sha256(src).hexdigest()
   check="import hashlib,json,os,sys,pathlib,importlib.metadata,pydantic\nw="+repr(expected)+"\nactual={}\nfor n,e in w.items():\n p=pathlib.Path('/testbed')/n\n actual[n]={'sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'execute':bool(p.stat().st_mode&0o111)}\nprint(json.dumps({'source_identity_mismatches':{n:{'expected':w[n],'actual':actual[n]} for n in w if w[n]!=actual[n]}},sort_keys=True))\nassert actual==w, 'scoreable baseline member mismatch'\nassert os.getuid()==54321 and sys.version.startswith('3.8.19') and importlib.metadata.version('pydantic-core')=='2.14.5'\nassert pydantic.__file__=='/testbed/pydantic/__init__.py'\nprint(json.dumps({'uid':os.getuid(),'python':sys.version,'core':importlib.metadata.version('pydantic-core'),'pydantic':pydantic.__version__,'import_path':pydantic.__file__,'source_files':actual,'caps':pathlib.Path('/proc/self/status').read_text()},sort_keys=True))\n"
   pre=call(env,variant+'_source_identity_before',stdin=check.encode());assert pre.returncode==0
   v['source_before']=json.loads(pre.stdout.splitlines()[-1]);v['status']='diagnostic_running';save()
   run=call(env,variant+'_retention_probe',timeout=120,stdin=(here/'retention_probe.py').read_bytes());assert run.returncode in [0,1]
   observed=json.loads(run.stdout);assert observed['uid']==54321 and observed['core']=='2.14.5' and observed['python'].startswith('3.8.19') and observed['pydantic_path']=='/testbed/pydantic/__init__.py'
   assert len(observed['cases'])==4 and run.returncode==(0 if observed['all_passed'] else 1)
   v['diagnostic_rc']=run.returncode;v['observations']=observed
   post=call(env,variant+'_source_identity_after',stdin=check.encode());assert post.returncode==0
   v['source_after']=json.loads(post.stdout.splitlines()[-1]);assert v['source_before']['source_files']==v['source_after']['source_files']
   v['status']='executed_interpret_behaviors_separately'
  finally:
   done.set()
   if monitor:monitor.join(timeout=5)
   rm=call(['docker','rm','-f',cid],variant+'_rm');v['cleanup_rm_rc']=rm.returncode;assert rm.returncode==0
   q=call(['docker','ps','-a','--filter','id='+cid,'--format','{{.ID}}'],variant+'_cleanup_query');assert q.returncode==0 and not q.stdout.strip()
   v['cleanup_actual_CID_absent']=True;save()
 state['status']='all_three_candidate_diagnostics_executed'
except BaseException as exc:
 state['status']='stopped_infra_or_identity_hold';state['exception']=repr(exc);raise
finally:
 q=call(['docker','ps','-a','--filter','label=rh2.pyd8511.retention.job='+job,'--format','{{.ID}}'],'job_cleanup_query')
 state['job_label_query_rc']=q.returncode;state['job_label_remaining']=q.stdout.decode().splitlines();state['job_cleanup_verified']=q.returncode==0 and not q.stdout.strip()
 state['finished_at']=datetime.datetime.now(datetime.timezone.utc).isoformat();save()
 print(json.dumps({k:state[k] for k in ['status','job_cleanup_verified','job_label_remaining']},ensure_ascii=False),flush=True)
