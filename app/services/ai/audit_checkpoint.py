"""Reuse only complete, independently checked evidence for identical source claims."""
import hashlib
import json
import logging
from pathlib import Path

from app.services.ai.cache_policy import ai_cache_enabled
from app.services.ai.takeoff_evidence_completion import evidence_gaps
from app.services.cache_service import cache_service

logger = logging.getLogger(__name__)


def audit_revision():
    folder = Path(__file__).parent
    digest = hashlib.sha256()
    for name in ('audit_checkpoint.py', 'device_crop_audit.py', 'evidence_preview.py',
                 'evidence_crops.py', 'takeoff_evidence_completion.py','material_note_evidence.py','source_crop_repair.py'):
        digest.update((folder / name).read_bytes())
    return digest.hexdigest()


class AuditCheckpoint:
    def __init__(self, image, scope):
        self.enabled = bool(scope) and ai_cache_enabled()
        self.keys = {}
        if self.enabled:
            digest = hashlib.sha256(image.tobytes())
            digest.update(str((image.mode, image.size)).encode())
            self.prefix = json.dumps([scope, digest.hexdigest(), audit_revision()], sort_keys=True, default=str)

    async def get(self, identity, device, proposal):
        if not self.enabled:
            return None
        # IDs depend on extraction ordering; the source pixels, claims and boxes do not.
        claim = device.model_dump(mode='json')
        proposal = {k: v for k, v in proposal.items() if k != 'device_id'}
        content = json.dumps([self.prefix, claim, proposal], sort_keys=True, ensure_ascii=False)
        key = 'elquote:audit-checkpoint:v1:' + hashlib.sha256(content.encode()).hexdigest()
        self.keys[identity] = key
        try:
            raw = await cache_service.get(key)
            box = json.loads(raw) if isinstance(raw, str) else raw
            if isinstance(box, dict) and box.get('audit_observed') and not evidence_gaps(device, box):
                return {**box, 'device_id': identity}
        except Exception:
            logger.warning('Unable to read audit checkpoint; checking source again.', exc_info=True)
        return None

    async def save(self, identity, device, box):
        if not self.enabled or identity not in self.keys:
            return
        if not box.get('audit_observed') or evidence_gaps(device, box):
            return
        try:
            await cache_service.set(self.keys[identity], json.dumps(box, ensure_ascii=False), expire=3600)
        except Exception:
            logger.warning('Unable to save audit checkpoint.', exc_info=True)
