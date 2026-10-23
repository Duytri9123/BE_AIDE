import sys,re,json
sys.path.insert(0,'scripts')
from import_ls_step_family import import_family,ROOT,PRICES
ACB=[('FRONT','SIDE-L',90),('REAR','SIDE',-90),('SIDE-L','TOP',180),('SIDE','BOTTOM',0),('TOP','FRONT',90),('BOTTOM','REAR',90)]
from pathlib import Path
jobs=[('53658','06~16D','3','H','FIXED'),('53670','06~16D','4','H','FIXED'),('53682','20~32E','3','H','FIXED'),('53694','20~32E','4','H','FIXED'),('53692','40E','3','V','FIXED'),('53704','40E','4','V','FIXED'),('53706','06~16D','3','H','WITHDRAW'),('53718','06~16D','4','H','WITHDRAW'),('53730','20~32E','3','H','WITHDRAW'),('53742','20~32E','4','H','WITHDRAW'),('53740','40E','3','V','WITHDRAW'),('53752','40E','4','V','WITHDRAW')]
jobs += [('48321','40~50F','3','H','FIXED'),('48327','40~50F','4','H','FIXED'),('48375','63G','3','H','FIXED'),('48387','63G','4','H','FIXED'),('50256','40~50F','3','H','WITHDRAW'),('48529','40~50F','4','H','WITHDRAW'),('50863','63G','3','H','WITHDRAW'),('48567','63G','4','H','WITHDRAW')]
if __name__=='__main__':
 for sid,frame,poles,terminal,mount in jobs:
  if len(sys.argv)>1 and sid not in sys.argv[1:]:continue
  if not sys.argv[1:] and sid not in ['53658']:continue
  def choose(row,frame=frame,poles=poles,terminal=terminal,mount=mount):
   if row.get('category')!='ACB':return False
   m=re.match(r'^(AN|AS|AH|AV|AW)-(\d{2})([DEFG])([34])-\d{2}([HVA])',row['sku'])
   if not m or m[4]!=poles:return False
   n=int(m[2]);valid={'06~16D':m[3]=='D' and 6<=n<=16,'20~32E':m[3]=='E' and 20<=n<=32,'40E':m[3]=='E' and n==40,'40~50F':m[3]=='F' and 40<=n<=50,'63G':m[3]=='G' and n==63}[frame]
   requested='WITHDRAW' if 'DRAW-OUT' in str(row.get('group') or '').upper() else 'FIXED'
   return valid and requested==mount and (mount=='WITHDRAW' or m[5]==terminal)
  models=sorted(set(re.match(r'([A-Z]+-\d+[DEFG][34])',r['sku'])[1] for r in PRICES if choose(r)))
  import_family(sid,'ACB',models,poles+'P',choose,mapping=ACB,spec={'Kiểu lắp':'Rút kéo' if mount=='WITHDRAW' else 'Cố định','Hướng đầu nối':terminal},name='LS · ACB · '+frame+' · '+poles+'P · '+('Rút kéo' if mount=='WITHDRAW' else 'Cố định')+' · Đầu nối '+terminal)
