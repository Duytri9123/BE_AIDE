"""Crop AutoCAD WMF raster previews without altering their drawn content."""
from pathlib import Path
from PIL import Image, ImageChops

ROOT = Path(__file__).resolve().parents[2]
BASE = ROOT / 'Tudien/CATALOG_PHU_KIEN_DOC_LAP/LS_D02_DU_LIEU_MOI/native'
for path in BASE.glob('LS-D02-*.png'):
    if path.stem.endswith('-crop'):
        continue
    image = Image.open(path).convert('RGB')
    threshold = image.point(lambda x: 255 if x < 245 else 0)
    box = threshold.getbbox()
    if not box:
        continue
    pad = round(max(box[2]-box[0], box[3]-box[1])*.035)
    box = (max(0,box[0]-pad), max(0,box[1]-pad), min(image.width,box[2]+pad), min(image.height,box[3]+pad))
    image.crop(box).save(BASE / (path.stem+'-crop.png'))
