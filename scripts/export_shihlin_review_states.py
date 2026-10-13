"""Export genuine Shihlin dynamic states without modifying source DWGs."""
import json, re, time
from pathlib import Path
import win32com.client
import ezdxf

BASE=Path(__file__).resolve().parents[2]/'Tudien/CATALOG_PHU_KIEN_DOC_LAP/SHIHLIN_D06_DU_LIEU_MOI'
NATIVE=BASE/'native'
OUT=BASE/'reviewed_states';OUT.mkdir(exist_ok=True)
rows=json.loads((NATIVE/'manifest.json').read_text(encoding='utf-8'))
app=win32com.client.GetActiveObject('AutoCAD.Application')
results=[]
def call(fn):
    for n in range(20):
        try:return fn()
        except Exception:
            if n==19:raise
            time.sleep(.5)
for item in rows:
    options=next((p for p in item['dynamic_properties'] if p['name']=='Options'),None)
    choices=options['allowed'] if options else ['Front View']
    doc=None
    try:
        doc=call(lambda:app.Documents.Open(str((NATIVE/(item['id']+'.dwg')).resolve())))
        blocks=call(lambda:[e for e in doc.ModelSpace if e.ObjectName=='AcDbBlockReference'])
        assert len(blocks)==1,(item['id'],len(blocks))
        block=win32com.client.CastTo(blocks[0],'IAcadBlockReference')
        for option in choices:
            sid=item['id']+'-STATE-'+re.sub(r'[^A-Z0-9]+','-',option.upper()).strip('-')
            target=OUT/(sid+'.dxf')
            if not target.exists():
                if options:
                    props=call(lambda:{p.PropertyName:p for p in block.GetDynamicBlockProperties()})
                    call(lambda:setattr(props['Options'],'Value',option))
                    if 'Poles' in props:
                        m=re.match(r'([1-4]P):.*?(Front|Cover)',option,re.I)
                        wanted=m[1].lower()+('/f' if m[2].lower()=='front' else '/c') if m else 'none'
                        allowed=call(lambda:list(props['Poles'].AllowedValues))
                        value=next((v for v in allowed if v.lower()==wanted),None)
                        if value:call(lambda:setattr(props['Poles'],'Value',value))
                    call(lambda:doc.Regen(1))
                call(lambda:doc.SaveAs(str(target.resolve()),65))
            attrs={a['tag'].upper():a['text'] for a in item.get('attributes',[])}
            results.append({'id':sid,'source_id':item['id'],'option':option,'attributes':attrs,
                            'source_group':item['group'],'dxf':target.relative_to(BASE).as_posix()})
        (OUT/'manifest.json').write_text(json.dumps(results,ensure_ascii=False,indent=2),encoding='utf-8')
        print(item['id'],len(results),'states',flush=True)
    finally:
        if doc:call(lambda:doc.Close(False))
print('Exported',len(results),'states')
