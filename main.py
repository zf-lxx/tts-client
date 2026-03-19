"""
TTS OPEN 管理平台
支持多种 TTS 渠道接入的统一管理平台
"""

from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

from config.settings import settings
from config.logger import logger
from routers import tts, channels

# 不需要认证的路径前缀
_PUBLIC_PATHS = {"/", "/api/health", "/docs", "/openapi.json", "/redoc", "/kaithhealthcheck", "/kaithheathcheck"}


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    应用生命周期管理
    """
    # 启动时执行
    logger.info("服务正在启动...")
    logger.info(f"配置信息: DEBUG={settings.DEBUG}, HOST={settings.HOST}, PORT={settings.PORT}")
    
    yield
    
    # 关闭时执行
    logger.info("服务正在关闭...")


app = FastAPI(
    title="TTS OPEN 管理平台",
    description="支持多种 TTS 渠道接入的统一管理平台",
    version="1.0.0",
    lifespan=lifespan
)

# CORS 中间件
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def auth_middleware(request: Request, call_next):
    """API Key 认证中间件，仅对 /api/v1/* 生效"""
    path = request.url.path
    # 公开路径直接放行
    if path in _PUBLIC_PATHS or not path.startswith("/api/v1"):
        return await call_next(request)

    # 从 Authorization: Bearer <token> 或 X-API-Key 头中取 token
    token = None
    auth_header = request.headers.get("Authorization", "")
    if auth_header.startswith("Bearer "):
        token = auth_header[7:]
    if not token:
        token = request.headers.get("X-API-Key", "")

    if token != settings.ADMIN_PASSWORD:
        return JSONResponse(status_code=401, content={"detail": "未授权，请提供有效的 API Key"})

    return await call_next(request)

# 挂载静态文件
app.mount("/static", StaticFiles(directory="static"), name="static")

# 模板引擎
templates = Jinja2Templates(directory="templates")

# 注册路由
app.include_router(tts.router, prefix="/api/v1", tags=["TTS"])
app.include_router(channels.router, prefix="/api/v1", tags=["渠道管理"])


@app.get("/")
async def root(request: Request):
    """主页 - 返回前端界面"""
    return templates.TemplateResponse("index.html", {"request": request})


@app.get("/api/health")
@app.get("/kaithhealthcheck")
@app.get("/kaithheathcheck")
async def health_check():
    """健康检查接口"""
    return {
        "status": "healthy",
        "service": "TTS OPEN 管理平台",
        "version": "1.0.0"
    }


if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host=settings.HOST,
        port=settings.PORT,
        #reload=settings.DEBUG
    )
