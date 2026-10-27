"""Evaluate the supplied fabrication workbook in Excel without running macros."""
import hashlib
import json
import math
import os
from pathlib import Path
import subprocess
import tempfile
from threading import Lock

WORKBOOK = Path('storage/cost_templates/Bao gia v6.0 - 2021.xlsm')
_LOCK = Lock()


def _positive(value, field, allow_zero=False):
    if isinstance(value, bool) or not isinstance(value, (int,float)) or not math.isfinite(value) or value < 0 or (not allow_zero and value == 0):
        raise ValueError(f'{field} phải là số hợp lệ' + (' không âm.' if allow_zero else ' lớn hơn 0.'))


def calculate_design_cost(payload, *, workbook_path=None):
    enclosure = payload.get('enclosure')
    segments = payload.get('busbar_segments')
    if enclosure is None and segments is None:
        return {'status':'needs_design','enclosure':None,'busbar':None}
    if enclosure is not None:
        if not isinstance(enclosure, dict): raise ValueError('Thông số vỏ tủ phải là một đối tượng.')
        for field in ('height_mm','width_mm','depth_mm','thickness_mm'):
            _positive(enclosure.get(field), field)
        for field in ('price_per_kg','plinth_height_mm'):
            if enclosure.get(field) is not None: _positive(enclosure[field],field,True)
        if enclosure.get('construction')=='Tủ khung':
            for field in ('compartments','side_panels'):
                _positive(enclosure.get(field),field,field=='side_panels')
        choices = {'location':{'Trong nhà','Ngoài trời'}, 'construction':{'Tủ dựng, quây','Tủ khung'},
                   'door_layers':{'1 lớp cánh','2 lớp cánh'}, 'compartmented':{'Có','Không'},
                   'accessories':{'Panel','Thanh gá'}}
        for field, allowed in choices.items():
            if enclosure.get(field) is not None and enclosure[field] not in allowed:
                raise ValueError(f'{field} không hợp lệ.')
    if segments is not None:
        if not isinstance(segments,list) or len(segments)>40:
            raise ValueError('Bảng đồng thanh cái nhận tối đa 40 nhóm thanh theo workbook.')
        for segment in segments:
            if not isinstance(segment, dict): raise ValueError('Thông số thanh đồng phải là một đối tượng.')
            for field in ('width_mm','thickness_mm','length_mm','quantity'):
                _positive(segment.get(field),field)
            if not isinstance(segment['quantity'], int): raise ValueError('Số thanh phải là số nguyên.')
    if payload.get('copper_price_per_kg') is not None:
        _positive(payload['copper_price_per_kg'],'copper_price_per_kg',True)
    source = Path(workbook_path or WORKBOOK).resolve()
    if not source.is_file():
        return {'status':'calculator_unavailable','reason':'Chưa cấu hình workbook tính giá vỏ tủ và đồng.', 'enclosure':None,'busbar':None}
    if os.name != 'nt':
        return {'status':'calculator_unavailable','reason':'Máy tính giá cần Microsoft Excel trên Windows.', 'enclosure':None,'busbar':None}
    digest = hashlib.sha256(source.read_bytes()).hexdigest()
    request = {**payload,'workbook_path':str(source)}
    with _LOCK, tempfile.TemporaryDirectory(prefix='aide-cost-') as folder:
        file = Path(folder)/'request.json'
        file.write_text(json.dumps(request,ensure_ascii=False),encoding='utf-8')
        script = Path(__file__).with_suffix('.ps1')
        try:
            completed = subprocess.run(['powershell.exe','-NoProfile','-NonInteractive','-ExecutionPolicy','Bypass','-File',str(script),'-RequestPath',str(file)],
                capture_output=True,timeout=90,creationflags=subprocess.CREATE_NO_WINDOW)
        except subprocess.TimeoutExpired as error:
            raise TimeoutError('Excel chưa tính xong trong thời gian cho phép.') from error
        if completed.returncode:
            raise RuntimeError('Không tính được workbook trong Excel: ' + completed.stderr.decode('utf-8',errors='replace')[-800:])
        result=json.loads(completed.stdout.decode('utf-8-sig'))
    if hashlib.sha256(source.read_bytes()).hexdigest()!=digest:
        raise RuntimeError('Workbook nguồn đã thay đổi trong khi tính.')
    for kind, requested in (('enclosure',enclosure is not None),('busbar',segments is not None)):
        if not requested:
            result[kind]=None
        else:
            _positive(result[kind]['unit_price'],kind+'.unit_price',True)
            _positive(result[kind]['mass_kg'],kind+'.mass_kg',True)
    return {'status':'calculated','engine':'Microsoft Excel','source_sha256':digest,
            'inputs':payload,**result}
