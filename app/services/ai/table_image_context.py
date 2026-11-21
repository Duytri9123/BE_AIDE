"""Keep photographed circuit rows together without counting overlap twice."""
import re


def row_slope(image):
    """Project long, near-horizontal source wires into normalized coordinates."""
    import cv2
    import numpy as np
    canvas=image.copy();canvas.thumbnail((1600,1600))
    gray=cv2.cvtColor(np.asarray(canvas.convert('RGB')),cv2.COLOR_RGB2GRAY)
    lines=cv2.HoughLinesP(cv2.Canny(gray,50,150),1,np.pi/1800,60,
                          minLineLength=canvas.width*.4,maxLineGap=30)
    values=[]
    for x1,y1,x2,y2 in lines.reshape(-1,4) if lines is not None else []:
        if x1!=x2 and abs((y2-y1)/(x2-x1))<.15:
            values.append((y2-y1)/(x2-x1)*canvas.width/canvas.height)
    if len(values)<5 or np.quantile(values,.9)-np.quantile(values,.1)>.08:
        return None
    return float(np.median(values))


def owns_symbol(box, ownership, slope):
    if box and isinstance(ownership,dict):
        cy,cx=(box[0]+box[2])/2,(box[1]+box[3])/2
        upper,lower=ownership['upper'],ownership['lower']
        return upper[0]+upper[1]*(cx-250)<=cy<lower[0]+lower[1]*(cx-250)
    if not box or not ownership or slope is None:return True
    # Same circuit, common reference column: a supply at the load side can be
    # lower in the photo than its breaker. Raw y-only filtering loses that row.
    y=max(0,min(1000,(box[0]+box[2])/2-slope*((box[1]+box[3])/2-250)))
    return ownership[0]<=y<ownership[1] or ownership[1]==1000 and y==1000


def circuit_bands(image, slope):
    """Use source wire baselines for small reads; never infer device counts."""
    import cv2
    import numpy as np
    canvas=image.copy();canvas.thumbnail((1600,1600));w,h=canvas.size
    gray=cv2.cvtColor(np.asarray(canvas.convert('RGB')),cv2.COLOR_RGB2GRAY)
    lines=cv2.HoughLinesP(cv2.Canny(gray,50,150),1,np.pi/1800,50,
                          minLineLength=w*.2,maxLineGap=50)
    observations=[]
    for x1,y1,x2,y2 in lines.reshape(-1,4) if lines is not None else []:
        if x1==x2 or abs((y2-y1)/(x2-x1))>.15:continue
        if min(x1,x2)>w*.45 or max(x1,x2)<w*.5:continue
        x=(x1+x2)/2/w*1000
        own_slope=(y2-y1)/(x2-x1)*w/h
        y=(y1+y2)/2/h*1000-own_slope*(x-250)
        if 0<y<1000:observations.append((float(y),float(own_slope)))
    groups=[]
    for observation in sorted(observations):
        if groups and observation[0]-float(np.median([r[0] for r in groups[-1]]))<12:groups[-1].append(observation)
        else:groups.append([observation])
    centers=[(float(np.median([r[0] for r in g])),float(np.median([r[1] for r in g]))) for g in groups]
    if not 6<=len(centers)<=24:return []
    edges=[(0,0)]+[((a[0]+b[0])/2,(a[1]+b[1])/2) for a,b in zip(centers,centers[1:])]+[(1000,0)]
    i=1
    while i<len(edges)-1:
        if edges[i][0]-edges[i-1][0]<30:edges.pop(i)
        else:i+=1
    bands=[{'box_2d':[max(0,min(a[0]-a[1]*250,a[0]+a[1]*750)-10),0,
                       min(1000,max(b[0]-b[1]*250,b[0]+b[1]*750)+10),1000],
             'ownership_y':{'upper':a,'lower':b}, 'wire_band':True,'rotation_degrees':0,
             'label':'Hàng dây nguồn '+str(i+1)} for i,(a,b) in enumerate(zip(edges,edges[1:]))]
    # Keep up to three complete neighbours in a bounded-height source crop.
    # This retains wire context without a separate remote request per row.
    result=[];index=0
    while index<len(bands):
        first=bands[index]
        end=index
        while end+1<min(index+3,len(bands)) and bands[end+1]['box_2d'][2]-first['box_2d'][0]<=220:
            end+=1
        last=bands[end]
        result.append({**first,'box_2d':[first['box_2d'][0],0,last['box_2d'][2],1000],
            'ownership_y':{'upper':first['ownership_y']['upper'],'lower':last['ownership_y']['lower']}})
        index=end+1
    return result


def crop_band(image, bounds, ownership, slope):
    """Keep the original pixel frame while hiding neighbouring sloped rows."""
    import numpy as np
    from PIL import Image
    left,top,right,bottom=bounds
    pixels=np.asarray(image.crop(bounds)).copy()
    if isinstance(ownership,dict):
        y=np.arange(top,bottom)[:,None]*1000/image.height
        x=np.arange(left,right)[None,:]*1000/image.width
        upper,lower=ownership['upper'],ownership['lower']
        pixels[(y<upper[0]+upper[1]*(x-250)-10)|(y>lower[0]+lower[1]*(x-250)+10)]=255
    elif ownership and slope is not None:
        y=np.arange(top,bottom)[:,None]*1000/image.height
        x=np.arange(left,right)[None,:]*1000/image.width
        projected=y-slope*(x-250)
        pixels[(projected<ownership[0]-10)|(projected>ownership[1]+10)]=255
    return Image.fromarray(pixels)


def shared_source_references(parts, references):
    from app.schemas.ai import ExtractedDeviceSchema
    from app.services.ingestion.cad_source_evidence import plain
    for reference in references:
        if not isinstance(reference,dict):continue
        text=str(reference.get('text') or '');spec=str(reference.get('spec') or '')
        label_ratios={re.sub(r'\s+','',v) for v in re.findall(r'\d+\s*/\s*\d+\s*V',plain(text))}
        spec_ratios={re.sub(r'\s+','',v) for v in re.findall(r'\d+\s*/\s*\d+\s*V',plain(spec))}
        if reference.get('category')!='POWER_SUPPLY' or not spec_ratios or not spec_ratios.issubset(label_ratios):
            continue
        try:
            header=ExtractedDeviceSchema.normalize_evidence_box(reference.get('box_2d'))
            group=ExtractedDeviceSchema.normalize_evidence_box(reference.get('applies_to_box_2d'))
        except (TypeError,ValueError,OverflowError):continue
        if not header or not group:continue
        for part in parts:
            by_id={str(b.get('device_id')):b for b in part['boxes']}
            for index,row in enumerate(part['devices']):
                kind=plain(' '.join(str(row.get(k) or '') for k in ('name','category')))
                if not re.search(r'BO (?:DOI )?NGUON|POWER.?SUPPLY',kind):continue
                box=by_id.get(str(index));symbol=(box or {}).get('symbol_box_2d')
                if not symbol:continue
                cy,cx=(symbol[0]+symbol[2])/2,(symbol[1]+symbol[3])/2
                if not (group[0]<=cy<=group[2] and group[1]<=cx<=group[3]):continue
                if not row.get('spec'):row['spec']=spec
                observed=row.get('source_observations') or {}
                row['source_observations']={**observed,'source_shared_label':reference}
                # The overview supplies a narrow common symbol column. Retain
                # its full width so a coarse locator cannot cut off one winding.
                box['symbol_box_2d']=[max(0,symbol[0]-8),max(0,group[1]-5),
                                      min(1000,symbol[2]+8),min(1000,group[3]+5)]
                box.update(text_box_2d=header,shared_label=True,group_reference_box_2d=group,
                    relationship_evidence=reference.get('relationship_evidence') or 'Đối chiếu tiêu đề nguồn với cột ký hiệu và dây nối chung trên ảnh gốc.')


def propose_branch_tags(parts):
    """Copy an explicitly read common circuit label, never synthesize a tag.

    Unique load identity only proposes the association. The exported tag and
    complete source wire context still go through independent pixel checking.
    """
    from app.services.ingestion.cad_source_evidence import plain
    branches={}
    for part in parts:
        boxes={str(b.get('device_id')):b for b in part['boxes']}
        for i,row in enumerate(part['devices']):
            box=boxes.get(str(i)) or {};load=re.sub(r'\W+','',plain(row.get('connected_load')))
            if load and row.get('tag') and box.get('tag_box_2d'):
                branches.setdefault(load,[]).append((row['tag'],box['tag_box_2d']))
    for part in parts:
        boxes={str(b.get('device_id')):b for b in part['boxes']}
        for i,row in enumerate(part['devices']):
            if row.get('tag') or row.get('category') not in {'CONTACTOR','POWER_SUPPLY','BỘ NGUỒN','BỘ ĐỔI NGUỒN'}:continue
            anchors=branches.get(re.sub(r'\W+','',plain(row.get('connected_load')))) or []
            if len({tag for tag,_ in anchors})!=1 or str(i) not in boxes:continue
            tag,box=anchors[0];row['tag']=tag
            row['location']=row.get('location') or 'Lộ '+tag
            boxes[str(i)]['tag_box_2d']=box
