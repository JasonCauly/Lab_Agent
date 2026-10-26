import asyncio
from contextlib import asynccontextmanager, suppress
import logging
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.exceptions import RequestValidationError
from fastapi.staticfiles import StaticFiles
from app.config import UPLOAD_DIR, settings
from app.models.user import User
from app.models.lab import Lab
from app.models.equipment import Equipment
from app.models.reservation import Reservation
from app.database import engine, Base
from app.api import api
from app.common.exceptions import (
    BusinessException,
    business_exception_handler,
    http_exception_handler,
    validation_exception_handler,
    global_exception_handler,
)
from app.services import kb_service, reservation_service

Base.metadata.create_all(bind=engine)  # 自动创建数据库表结构

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    if settings.KB_WARMUP_ON_STARTUP:
        try:
            await asyncio.to_thread(kb_service.warmup)
        except Exception:
            logger.exception("知识库预热失败，后端继续启动；请检查本地向量模型缓存")
    task = asyncio.create_task(
        reservation_service.run_expire_scan()
    )  # 启动项目 开启异步的扫描任务
    try:
        yield
    finally:
        task.cancel()  # 关闭项目 同时取消异步任务
        with suppress(asyncio.CancelledError):
            await task


app = FastAPI(lifespan=lifespan)

origins = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,  # 允许的前端源，不要直接写 ["*"]
    allow_credentials=True,  # ✅ 关键：允许前端携带 Authorization token
    allow_methods=["*"],  # 允许所有请求方法 GET POST PUT DELETE OPTIONS
    allow_headers=["*"],  # 允许所有请求头（包含Authorization）
)

app.include_router(api)

# 注册异常处理器
app.add_exception_handler(BusinessException, business_exception_handler)
app.add_exception_handler(HTTPException, http_exception_handler)
app.add_exception_handler(RequestValidationError, validation_exception_handler)
# 全局的异常兜底, 必须放在最后注册!!!
app.add_exception_handler(Exception, global_exception_handler)

# 挂载静态的文件目录 http://127.0.0.1:8000/uploads/xxx.jpg
app.mount("/uploads", StaticFiles(directory=UPLOAD_DIR), name="uploads")


@app.get("/")
def root():
    return {"message": "Hello, World!"}
