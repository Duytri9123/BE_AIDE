"""DMPi integrated terminal/penetration sources verified against LS dimension drawings."""
import re
from import_ls_step_family import import_family
if __name__=='__main__':
 for sid,connection,page in [('45871','S',23),('45873','T',24)]:
  models=['DMP06i-'+connection,'DMP65i-'+connection]
  import_family(sid,'RELAY',models,None,lambda r:r.get('category')=='RELAY' and bool(re.match(r'DMP(?:06|65)i-'+connection,r['sku'])),name='LS · Rơ le bảo vệ động cơ DMPi · '+' / '.join(models)+' · Màn hình liền · '+('Đầu nối vít' if connection=='S' else 'Luồn dây'),spec={'Kiểu kết nối':'Đầu nối vít' if connection=='S' else 'Luồn dây','Kiểu màn hình':'Liền thân; không áp dụng bản màn hình rời'},evidence={'catalog_url':'https://www.ls-electric.com/upload/customer/download/91cf9847-cd71-40cc-b85c-9902e721e9d4/DMPi_E_1905%280%29.pdf','pdf_page':page,'checked':'Integrated terminal type (S) / integrated penetration type (T); manufacturer front/side/top dimensions and mounting orientation','ordering_options':'06i/65i and electrical suffixes require configuration check; no split-display geometry substitution'})
