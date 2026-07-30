"""FastAPI 应用入口"""
from pathlib import Path
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware

from backend.database import init_db
from backend.routers import router as api_router

app = FastAPI(title="全国家电选购指南 API", version="1.0.0")

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 静态文件：serve index.html
static_dir = Path(__file__).resolve().parent.parent  # backend/ 的父目录
app.mount("/static", StaticFiles(directory=str(static_dir), html=True), name="static")

# API 路由
app.include_router(api_router, prefix="/api")


@app.on_event("startup")
def on_startup():
    """启动时初始化数据库"""
    init_db()


@app.get("/")
def root():
    """重定向到 index.html"""
    from fastapi.responses import FileResponse
    return FileResponse(str(static_dir / "index.html"))
