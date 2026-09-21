import json,sys,subprocess
M='runs/env_overnight_20260916/L1_pydantic/mat'
R='runs/env_overnight_20260916/repos/pydantic'
tid,path=sys.argv[1],sys.argv[2]
c=json.load(open(f'{M}/{tid}/grading.json'))['base_commit']
r=subprocess.run(['git','-C',R,'show',f'{c}:{path}'],capture_output=True,text=True)
if r.returncode: print('ERR',r.stderr); sys.exit(1)
lines=r.stdout.split('\n')
if len(sys.argv)>3:
    import re
    pat=sys.argv[3]
    if '-' in pat and pat.replace('-','').isdigit():
        a,b=pat.split('-'); a,b=int(a),int(b)
        for i in range(max(0,a-1),min(len(lines),b)): print(f'{i+1}\t{lines[i]}')
    else:
        for i,l in enumerate(lines,1):
            if re.search(pat,l): print(f'{i}\t{l}')
else:
    for i,l in enumerate(lines,1): print(f'{i}\t{l}')
