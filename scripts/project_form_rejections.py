import re,unicodedata
CACHE={}
def norm(s):return ''.join(c for c in unicodedata.normalize('NFD',s.upper().replace('Đ','D')) if not unicodedata.combining(c))
def rejection(doc,r):
 key=id(doc)
 if key not in CACHE:
  segments=[];notes=[]
  for e in doc.modelspace():
   t=e.dxftype()
   if t=='LINE':segments.append((e.dxf.start,e.dxf.end))
   elif t=='LWPOLYLINE':
    pts=list(e.get_points('xy'));segments.extend(zip(pts,pts[1:]))
   elif t in ('TEXT','MTEXT'):
    raw=e.dxf.text if t=='TEXT' else e.plain_text();n=norm(raw)
    if re.search(r'KHONG (DUNG|SU DUNG|LAY)|HUY|BO MAU|BO TU|SAI|BAO LOI|LOI THIET KE|CANCEL|NOT USE|REJECT',n):notes.append((e.dxf.insert,raw))
  CACHE[key]=(segments,notes)
 segments,notes=CACHE[key];x0,y0,x1,y1=r;w=x1-x0;h=y1-y0;diags=[]
 for a,b in segments:
  if abs(a[0]-b[0])<w*.7 or abs(a[1]-b[1])<h*.7:continue
  if not all(x0-w*.15<=p[0]<=x1+w*.15 and y0-h*.15<=p[1]<=y1+h*.15 for p in (a,b)):continue
  diags.append(1 if (a[0]-b[0])*(a[1]-b[1])>0 else -1)
 if 1 in diags and -1 in diags:return 'Có hai nét gạch chéo phủ phần lớn mặt tủ; loại khỏi danh mục.'
 for point,text in notes:
  if x0-30<=point[0]<=x1+30 and y0-50<=point[1]<=y1+50:return 'Ghi chú hủy/không dùng/lỗi: '+text
 return None
