"""Compress saved analysis detail without buffering live progress streams."""
from starlette.middleware.gzip import GZipMiddleware


class SavedAnalysisCompression:
    def __init__(self, app, prefix):
        self.app = app
        self.prefix = prefix
        self.compressed = GZipMiddleware(app, minimum_size=1024, compresslevel=3)

    async def __call__(self, scope, receive, send):
        if (scope['type'] == 'http' and scope.get('method') == 'GET'
                and scope.get('path', '').startswith(self.prefix)):
            await self.compressed(scope, receive, send)
        else:
            await self.app(scope, receive, send)
