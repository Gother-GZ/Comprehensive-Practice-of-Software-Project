from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, RedirectResponse

from app.api.v1 import api_router
from app.common.exceptions import AppException
from app.common.response import error_response, success_response
from app.db.init_db import initialize_database

OPENAPI_TAGS = [
    {"name": "auth", "description": "登录、刷新和注销。"},
    {"name": "users", "description": "用户与鉴权管理。"},
    {"name": "vsp", "description": "VSP 查询，包括机场、程序、跑道、频率和 Navaid。"},
    {"name": "system", "description": "系统配置、队列观测、失败/死信查询、导出与 consumer 管理。"},
    {"name": "integration", "description": "A-1/A-2/A-3/A-4 协商接入与治理接口。"},
]


@asynccontextmanager
async def lifespan(_app: FastAPI):
    initialize_database()
    yield


app = FastAPI(
    title="Alpha A-5 Service",
    version="0.1.0",
    description="Alpha A-5 backend for auth, VSP, integration governance, and Redis-list middleware operations.",
    openapi_tags=OPENAPI_TAGS,
    lifespan=lifespan,
)
app.include_router(api_router, prefix="/api/v1")


@app.get("/", include_in_schema=False)
def root():
    return RedirectResponse(url="/docs")


@app.get("/health")
def health():
    return success_response(data={"status": "ok"})


@app.exception_handler(AppException)
async def app_exception_handler(_request: Request, exc: AppException):
    return JSONResponse(status_code=exc.status_code, content=error_response(message=exc.message, code=exc.code))


@app.exception_handler(Exception)
async def unhandled_exception_handler(_request: Request, exc: Exception):
    return JSONResponse(status_code=500, content=error_response(message=str(exc), code=50000))
