"""Exercise real project/catalog/auth APIs and the new gateway without mocks."""
import asyncio
import json
import os
from pathlib import Path
import httpx


async def main():
    audit = Path('../AIDE/outputs/package-audit-20261023')
    fixture = json.loads((audit / 'system-fixture.json').read_text(encoding='utf-8'))
    result = {}
    async with httpx.AsyncClient(timeout=150) as client:
        response = await client.post('http://127.0.0.1:8000/api/v1/auth/login', json={
            'email':'cad-agent-audit-20261023-01@tests.elquote.local', 'password':os.environ['CAD_AUDIT_PASSWORD']})
        response.raise_for_status()
        headers = {'Authorization': 'Bearer ' + response.json()['access_token']}
        base = 'http://127.0.0.1:8000/api/v1'
        project_id = fixture['project_id']
        for label, route in [('project', f'/projects/{project_id}'), ('latest_analysis', f'/analyze/project/{project_id}/latest'),
                             ('catalog','/equipment-library/browse?q=MCCB&brand=LS&record_type=priced_variant&limit=1')]:
            reply = await client.get(base + route, headers=headers)
            result[label] = {'status': reply.status_code}
        files = await client.get(f'{base}/projects/{project_id}/files', headers=headers)
        files.raise_for_status()
        if not any(row['filename'] == 'cad-agent-audit.dxf' for row in files.json()):
            drawing = (audit / 'cli/Untitled.dxf').read_bytes()
            upload = await client.post(f'{base}/projects/{project_id}/upload', headers=headers,
                files={'file':('cad-agent-audit.dxf', drawing, 'application/dxf')})
            result['upload_dxf'] = {'status':upload.status_code}
            upload.raise_for_status()
        else: result['upload_dxf'] = {'status':200,'existing_test_file':True}
        agent_base = 'http://127.0.0.1:8001/api/v1/cad-agent'
        response = await client.get(agent_base + '/providers', headers=headers)
        response.raise_for_status()
        providers = response.json()
        result['system_providers'] = providers
        if providers:
            provider = providers[0]
            response = await client.get(f'{agent_base}/providers/{provider["id"]}/models?refresh=true', headers=headers)
            response.raise_for_status()
            listing = response.json()
            result['model_discovery'] = listing
            if listing['models']:
                model = next((row['model_key'] for row in listing['models'] if row['model_key'] == 'gemini-3.8-flash-high'), listing['models'][0]['model_key'])
                if provider['protocol'] == 'antigravity':
                    payload = {'model':model,'request':{'contents':[{'role':'user','parts':[{'text':'Kiểm tra kết nối AIDE. Chỉ trả lời: AIDE OK'}]}],
                        'generationConfig':{'maxOutputTokens':256,'temperature':0.1}},
                        'userAgent':'antigravity','requestType':'agent'}
                else:
                    payload = {'messages':[{'role':'user','content':'Chỉ trả lời AIDE OK'}],'max_tokens':128}
                reply = await client.post(f'{agent_base}/providers/{provider["id"]}/inference', headers=headers,
                    json={'model':model,'payload':payload,'stream':False})
                result['real_inference'] = {'status':reply.status_code,'provider':provider['id'],'model':model,'response':reply.text[:2000]}
    (audit / 'system-live-results.json').write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps(result, ensure_ascii=True))


if __name__ == '__main__': asyncio.run(main())
