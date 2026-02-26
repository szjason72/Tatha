"""
Tatha 主仓 HTTP 入口：供 ZeroClaw 助理 Tool 调用。

架构：单入口 + 中央大脑。用户/助理只调用一个入口（POST /v1/ask），
需求由中央大脑解析并分发到内部各能力端口（解析、匹配、诗人 RAG、征信等），
内部实现与端口对用户不可见。
"""
from fastapi import FastAPI

app = FastAPI(
    title="Tatha API",
    description="Tatha 主仓：单入口 + 中央大脑，简历解析、匹配、诗人/诗词 RAG",
    version="0.1.0",
)


@app.get("/health")
def health():
    """探活：唯一对外端口下的健康检查。"""
    return {"status": "ok", "service": "tatha"}


# 单入口：用户需求由此进入，中央大脑解析后分发到内部端口（解析/匹配/诗人推荐/征信等）
# TODO: 实现 POST /v1/ask — 请求体含 message/context，返回统一 JSON
# @app.post("/v1/ask")
# def ask(request: AskRequest):
#     intent = central_brain.parse_intent(request.message)
#     result = central_brain.dispatch(intent, request.context)
#     return {"intent": intent, "result": result}
