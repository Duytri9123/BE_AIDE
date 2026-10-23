import subprocess,sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
root=Path(__file__).resolve().parents[1]
def run(ident):
 log=root/'tmp'/('step-project-'+ident.replace('/','-')+'.log')
 with log.open('w',encoding='utf8') as f:
  result=subprocess.run([sys.executable,str(root/'scripts/project_ls_step_views.py'),ident,'--poly'],cwd=root,stdout=f,stderr=subprocess.STDOUT,creationflags=subprocess.CREATE_NO_WINDOW)
 print(ident,result.returncode,flush=True)
if __name__=='__main__':
 with ThreadPoolExecutor(max_workers=1) as pool:
  for _ in pool.map(run,sys.argv[1:] or ['55500','55490','55497','55498']):pass
