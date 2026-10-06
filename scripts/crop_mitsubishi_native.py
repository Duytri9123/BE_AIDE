"""Crop whitespace around Mitsubishi AutoCAD WMF previews."""
from pathlib import Path
from PIL import Image

base=Path(__file__).resolve().parents[2]/'Tudien/CATALOG_PHU_KIEN_DOC_LAP/MITSUBISHI_D04_DU_LIEU_MOI/native'
for path in base.glob('MIT-D04-*.png'):
    if path.stem.endswith('-crop'): continue
    image=Image.open(path).convert('RGB')
    dark=image.point(lambda value:255 if value<245 else 0)
    box=dark.getbbox()
    if not box: continue
    pad=round(max(box[2]-box[0],box[3]-box[1])*.035)
    region=(max(0,box[0]-pad),max(0,box[1]-pad),min(image.width,box[2]+pad),min(image.height,box[3]+pad))
    image.crop(region).save(base/(path.stem+'-crop.png'))
