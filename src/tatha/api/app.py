"""
Tatha 主仓 HTTP 入口：供 ZeroClaw 助理 Tool 调用。

架构：单入口 + 中央大脑。用户/助理只调用一个入口（POST /v1/ask），
需求由中央大脑解析并分发到内部各能力端口（解析、匹配、诗人 RAG、征信等），
内部实现与端口对用户不可见。
"""
from fastapi import FastAPI

from .schemas import AskRequest
from .central_brain import handle_ask

app = FastAPI(
    title="Tatha API",
    description="Tatha 主仓：单入口 + 中央大脑，简历解析、匹配、诗人/诗词 RAG",
    version="0.1.0",
)


@app.get("/health")
def health():
    """探活：唯一对外端口下的健康检查。"""
    return {"status": "ok", "service": "tatha"}


@app.post("/v1/ask")
def ask(request: AskRequest):
    """单入口：用户需求由此进入，中央大脑解析意图并分发到内部端口，返回统一 JSON。"""
    return handle_ask(request)
