from pathlib import Path
from fastapi import FastAPI, Header
from pydantic import BaseModel, Field
from .server import handle

class RpcRequest(BaseModel):
    jsonrpc: str = '2.0'
    id: int | str | None = None
    method: str
    params: dict = Field(default_factory=dict)

def create_app(root: Path) -> FastAPI:
    app = FastAPI(title='Skein MCP Server')

    @app.post('/mcp')
    def mcp(req: RpcRequest, x_skein_identity: str | None = Header(default=None)):
        payload = req.model_dump()
        if x_skein_identity:
            payload.setdefault('params', {})['identity'] = x_skein_identity
        return handle(payload, root)

    @app.get('/health')
    def health():
        return {'status': 'ok', 'service': 'skein-mcp'}

    return app
