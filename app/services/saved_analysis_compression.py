"""Compress saved analysis detail without buffering live progress streams."""
from starlette.middleware.gzip import GZipMiddleware


class SavedAnalysisCompression:
    def __init__(self, app, prefix):
        self.app = app
        self.prefix = prefix
        self.compressed = GZipMiddleware(app, minimum_size=1024, compresslevel=3)

    async def __call__(self, scope, receive, send):
        path = scope.get('path', '')
        analysis_prefix = self.prefix.rsplit('iteration/', 1)[0]
        saved_read = (path.startswith(self.prefix) or
                      (path.startswith(analysis_prefix + 'project/') and
                       path.endswith(('/latest', '/sessions'))) or
                      (path.startswith(analysis_prefix.removesuffix('analyze/') + 'projects/') and
                       path.endswith('/cabinet-designs')))
        if (scope['type'] == 'http' and scope.get('method') == 'GET' and saved_read):
            await self.compressed(scope, receive, send)
        else:
            await self.app(scope, receive, send)
