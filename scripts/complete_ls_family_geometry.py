"""Reviewed common LS bodies; source drawing dimensions and mating scope retained."""
import hashlib,json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
import ezdxf
from ezdxf import bbox
from scripts.complete_ls_remaining_geometry import BASE,CAT,ROWS,outline
from scripts.supplement_ls_pricebook_20261106 import main as publish

def catalogue(folder,url):
 p=CAT/'LS/NguonBenNgoai'/folder/'source.pdf'
 p.with_suffix('.json').write_text(json.dumps({'source_url':url,'sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'checked_on':'2026-11-06','authorship':'LS Electric manufacturer-authored technical catalogue'},indent=2),encoding='utf8')
 return p

def jobs():
 result=[];p=BASE/'METASOL-CATALOG.pdf'
 result.append(('ABS202c-SHARED250',['ABS202c'],'2P',[105,165,86.85],
  [('FRONT',114,(93,252,167,371),105,165),('SIDE',114,(446,252,509,371),86.85,165)],p,
  'Manufacturer Metasol page 9-4 explicitly labels one shared 2,3P dimension drawing for ABN250c/ABS250c/ABH250c/ABL250c. ABS202c is the two-pole member of this case family. The source illustrates three terminal positions on the shared case; the two-pole electrical terminal population is not approved by this schematic. Geometry is a family layout reference only, not a different pole body or transferred breaking-capacity rating.',
  {'name':'LS ABS202c · thân chung khung 250','mounting_type':'Bắt vít lên tấm gá'}))
 for model in ('EBN52c','EBN102c'):
  f=outline(model+'-2P-envelope',50,130)
  result.append((model+'-2P',[model],'2P',[50,130,82],
   [('MOUNTING',119,None,50,130,f),('SIDE',119,(460,240,519,333),82,130)],p,
   'Manufacturer EBN50c/60c/100c dimension sheet 9-9 gives a 130 mm high common body, 50 mm two-pole width (52 mm panel clearance), and 82 mm operating depth. Only the common side drawing and dimension-based two-pole envelope are provided. The illustrated three-pole front is not relabelled as two poles. Earth-leakage settings, terminals and exact contact configuration remain unapproved.',
   {'name':'LS '+model+' · thân hai cực','geometry_representation':'Catalogue side projection and documented two-pole mounting envelope','mounting_type':'Bắt vít lên tấm gá'}))
 p=BASE/'MC-EN.pdf'
 result.append(('MW9bB-22bB',['MW-9bB~22bB'],None,[104,170,114],
  [('MOUNTING',151,(240,192,300,289),104,170),('BOTTOM',151,(426,208,486,274),104,114)],p,
  'Manufacturer English catalogue page 151 explicitly groups MW-9bB~22bB with MW-6aB~18aB in the same 104×170×114 mm enclosure row. Publish the drawn enclosure views, not the internal contactor. Width/height calibrate catalogue artwork. Door controls, coil voltage and installed starter circuit remain price-row options; no automatic cabinet insertion approval.',
  {'name':'LS MW-9bB~22bB · vỏ thép','require_whole_paths':False,'mounting_type':'Bắt vít lên tấm gá'}))
 p=catalogue('METASOL-MMS-CATALOG-202609','https://www.ls-electric.com/ko/cat/%5BMetasol_MMS%5D_KO_C01821-06-202609.pdf')
 folder=CAT/'LS/ThietBi/OFFICIAL-STEP-50481-model-019'
 profile=json.loads((folder/'thong_tin_thiet_bi.json').read_text(encoding='utf8'));views=[]
 for v in profile['cad_don']:
  code=v['id_hinh_goc'].split('model-019-',1)[1];f=folder/v['duong_dan'];bb=bbox.extents(ezdxf.readfile(f).modelspace())
  views.append((code,24,None,bb.size.x,bb.size.y,f))
 result.append(('LA-MMS-FAMILY',['Any Trip Alarm Switch: LA 1NO+1NC'],None,[],views,p,
  'Original manufacturer STEP MMS_ACCESSORY_LX,LA,LAM.stp (SHA256 89705a47ea464be5b9131d09f1ba46b628521b9fd8ae6811b4644231fd3d40f8) explicitly includes LA. Existing six visible-edge projections were axis-reviewed against MMS installation illustrations. This public option is the shared side-mounted accessory body: LA MMS32 and LA MMS63/100 have parent-specific mating details, which must be chosen by the installer. The 1NO+1NC price-row configuration remains unchanged; family geometry does not confirm the exact mating variant. STEP source URL: https://www.ls-electric.com/ko/cat/HPDT/%5BMetasol%20MMS%5D%20MMS_ACCESSORIES_3D%20CAD.zip',
  {'name':'LS LA 1NO+1NC · thân phụ kiện MMS','geometry_representation':'Manufacturer native STEP family projection; mating variant requires host selection','mounting_type':'Gắn bên trái MMS, kiểm tra cơ cấu ghép theo khung'}))
 p=BASE/'MC-EN.pdf'
 result.append(('MC6a-DC-3P',['MC-6a (VDC)'],'3P',[45,73.5,96.6],
  [('FRONT',125,(188,355,246,447),45,73.5),('SIDE',125,(312,355,433,447),96.6,73.5),('REAR',125,(477,355,535,447),36.5,73.5)],p,
  'Manufacturer English catalogue page 125 separately illustrates MC-6a~18a DC, 3-pole, 1NO or 1NC: width 45 mm, height 73.5 mm, DC depth 96.6 mm. The actual DC row is used, not the AC row above or the four-pole page. The uploaded price-row 6A (1a), 3P and DC configuration remains unchanged. Rear mounting face is 36.5 mm wide; only source-illustrated views are published.',
  {'name':'LS MC-6a · cuộn DC · ba cực','require_whole_paths':False,'extra_spec':{'Loại cuộn hút':'DC'},'mounting_type':'Ray DIN hoặc bắt vít theo hãng'}))
 # MC150 uses an AC/DC common coil body, but the quote's auxiliary-contact
 # population differs from the illustrated standard. Retain only the shared
 # mounting face and body envelope, avoiding a false terminal arrangement.
 f=outline('MC150a-DC-common-envelope',119,158)
 result.append(('MC150a-DC-MOUNT',['MC-150a (VDC)'],'3P',[119,158,130.3],
  [('MOUNTING',129,None,119,158,f),('REAR',129,(459,187,507,263),95,158)],p,
  'Manufacturer MC-130a/150a section specifies an AC and DC control in the same physical size (page 36) and page 129 gives 119×158×130.3 mm outer dimensions with a 95 mm rear body face. The quote specifies 1a1b while the illustrated standard front has 2NO2NC. Use only the documented outer envelope and shared rear mounting body; the standard front/auxiliary terminals are deliberately not copied or electrically substituted. Exact auxiliary mating configuration requires installer selection.',
  {'name':'LS MC-150a · gá thân cuộn DC','require_whole_paths':False,'geometry_representation':'Documented common-coil body envelope and catalogue rear mounting projection','extra_spec':{'Loại cuộn hút':'DC'},'mounting_type':'Bắt vít lên tấm gá'}))
 return result

if __name__=='__main__':publish(jobs(),report_name='ls_family_geometry_review.json')
