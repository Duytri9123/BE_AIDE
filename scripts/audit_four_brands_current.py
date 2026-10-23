"""Fresh source/geometry/pricebook coverage audit for the four requested makers."""
import sys
import audit_abb_ls_chint_current as audit
audit.BRANDS={'ABB','LS Electric','CHINT','Schneider Electric'}
audit.FOLDER_BRANDS={'ABB':'ABB','LS':'LS Electric','Chint':'CHINT','Schneider':'Schneider Electric'}
audit.OUT=audit.ROOT/('docs/four-brands-audit-2026-10-22-after' if '--after' in sys.argv else 'docs/four-brands-audit-2026-10-22')
if '--after' in sys.argv:audit.DXF_CACHE_PATH=audit.ROOT/'docs/four-brands-audit-2026-10-22/dxf-files.json'
if __name__=='__main__':
 if '--publish' in sys.argv:
  import json
  original=audit._build_browser_data;payload={}
  def build():
   global payload
   payload=original();return payload
  audit._build_browser_data=build
 audit.main()
 if '--publish' in sys.argv:
  report=json.loads((audit.OUT/'summary.json').read_text(encoding='utf8'));assert not report['active_issue_counts']
  p=audit.CAT/'_agent_index/browser_display_v5.json';pending=p.with_suffix('.pending');pending.write_text(json.dumps(payload,ensure_ascii=False),encoding='utf8');pending.replace(p)
  print('Published source-checked full browser snapshot',flush=True)
