"""
Tatha 主仓 HTTP 入口：供 ZeroClaw 助理 Tool 调用。

架构：单入口 + 中央大脑。用户/助理只调用一个入口（POST /v1/ask），
需求由中央大脑解析并分发到内部各能力端口（解析、匹配、诗人 RAG、征信等），
内部实现与端口对用户不可见。

文档上传：POST /v1/documents/convert 使用 MarkItDown 转 Markdown，并可选做结构化提取（如简历）。

可选演示页：GET /demo.html 返回单文件 demo.html（与 API 同源，便于浏览器直接体验匹配结果）。
"""
import io
import os
from fastapi import Depends, FastAPI, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import HTMLResponse, PlainTextResponse

from .auth import AuthContext, get_auth
from .quota import (
    RESOURCE_ASK,
    RESOURCE_JOB_MATCH,
    RESOURCE_RAG,
    RESOURCE_RESUME_PARSE,
    consume,
    clamp_top_n,
)
from .region import get_region_response
from .schemas import (
    AskRequest,
    AskResponse,
    AuthLoginRequest,
    AuthRegisterRequest,
    CheckoutRequest,
    CheckoutResponse,
    DocumentConvertResponse,
    JobMatchRequest,
    JobMatchResponse,
    RagQueryRequest,
    RagQueryResponse,
    StubUpgradeRequest,
)
from .central_brain import handle_ask
from .orders import create_checkout
from .webhooks import handle_payment_webhook, handle_stub_upgrade

app = FastAPI(
    title="Tatha API",
    description="Tatha 主仓：单入口 + 中央大脑，简历解析、匹配、诗人/诗词 RAG",
    version="0.1.0",
)


# 项目根目录（便于同源提供 demo.html，避免 CORS；app.py 在 src/tatha/api/）
_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))


@app.get("/health")
def health():
    """探活：唯一对外端口下的健康检查。"""
    return {"status": "ok", "service": "tatha"}


def _serve_html(filename: str):
    path = os.path.join(_ROOT, filename)
    if not os.path.isfile(path):
        return PlainTextResponse(f"{filename} not found", status_code=404)
    with open(path, "r", encoding="utf-8") as f:
        return HTMLResponse(f.read())


@app.get("/", response_class=HTMLResponse)
@app.get("/index.html", response_class=HTMLResponse)
def serve_index():
    """认证订阅入口页：三档（免费/Basic/Pro），参考 ServBay 定价页形态。"""
    return _serve_html("index.html")


@app.get("/demo.html", response_class=HTMLResponse)
def serve_demo():
    """可选演示页：单文件 HTML，调用 /v1/ask 与 /v1/jobs/match 并在页面展示结果。仅用于开发期直观感受。"""
    return _serve_html("demo.html")


@app.get("/auth.html", response_class=HTMLResponse)
def serve_auth():
    """登录/注册页：Web 端登录注册测试用，当前为演示桩，未对接真实认证。"""
    return _serve_html("auth.html")


@app.get("/v1/region")
def region(request: Request):
    """
    按请求 IP 返回地区与定价，供订阅页展示币种与价格。无需鉴权。
    国内（CN）返回 CNY + pricing_cn，境外返回 USD + pricing_intl。
    """
    return get_region_response(request)


@app.post("/v1/auth/login")
def auth_login(request: AuthLoginRequest):
    """
    登录（演示桩）：接受邮箱+密码，返回 ok + token，供 Web 端登录测试。
    未对接 Zervigo/真实认证，仅用于 V0 验收「登录页可提交并跳转」。
    """
    return {
        "ok": True,
        "message": "登录成功（演示用，未对接真实认证）",
        "token": "demo-token-" + (request.email or "").replace("@", "-at-")[:32],
    }


@app.post("/v1/auth/register")
def auth_register(request: AuthRegisterRequest):
    """
    注册（演示桩）：接受邮箱+密码，返回 ok + token，供 Web 端注册测试。
    未对接 Zervigo/真实认证，仅用于 V0 验收「注册页可提交并跳转」。
    """
    return {
        "ok": True,
        "message": "注册成功（演示用，未对接真实认证）",
        "token": "demo-token-" + (request.email or "").replace("@", "-at-")[:32],
    }


def _quota_exceeded_response():
    return HTTPException(
        status_code=429,
        detail={
            "code": "quota_exceeded",
            "message": "当日配额已用尽，请升级后继续使用。",
        },
    )


@app.post("/v1/ask", response_model=AskResponse)
def ask(request: AskRequest, auth: AuthContext = Depends(get_auth)):
    """单入口：用户需求由此进入，中央大脑解析意图并分发到内部端口，返回统一 JSON。V1 需鉴权与配额。"""
    if not consume(auth.user_id, auth.tier, RESOURCE_ASK):
        raise _quota_exceeded_response()
    return handle_ask(request)


@app.post("/v1/documents/convert", response_model=DocumentConvertResponse)
async def documents_convert(
    file: UploadFile = File(..., description="待转换文档（PDF/Word/Excel 等）"),
    document_type: str | None = Form("resume", description="文档类型：resume / poetry / credit，用于选择提取器"),
    auth: AuthContext = Depends(get_auth),
):
    """
    高效解析标准流程：MarkItDown 多格式 → Markdown，再按 document_type 做可选结构化提取。
    V1 需鉴权与配额（resume 类型计入简历解析配额）。
    """
    dtype = (document_type or "resume").strip().lower() or "resume"
    if dtype == "resume" and not consume(auth.user_id, auth.tier, RESOURCE_RESUME_PARSE):
        raise _quota_exceeded_response()
    try:
        content = await file.read()
    except Exception as e:
        return DocumentConvertResponse(markdown="", error=f"读取文件失败: {e}")
    if not content:
        return DocumentConvertResponse(markdown="", error="文件为空")

    try:
        from tatha.ingest.markitdown_convert import stream_to_markdown

        markdown = stream_to_markdown(
            io.BytesIO(content),
            filename=file.filename or None,
        )
    except Exception as e:
        return DocumentConvertResponse(markdown="", error=f"MarkItDown 转换失败: {e}")

    extracted = None
    if dtype and markdown:
        try:
            from tatha.api.central_brain import _document_analysis
            extracted = _document_analysis(dtype, markdown)
        except Exception as e:
            return DocumentConvertResponse(
                markdown=markdown,
                document_type=dtype,
                error=f"结构化提取失败: {e}",
            )

    return DocumentConvertResponse(
        markdown=markdown,
        document_type=dtype,
        extracted=extracted,
    )


@app.post("/v1/jobs/match", response_model=JobMatchResponse)
def jobs_match(request: JobMatchRequest, auth: AuthContext = Depends(get_auth)):
    """
    职位匹配流水线：拉取职位 → 简历 vs 职位 LLM 打分 → 按综合分排序返回 Top-N。V1 需鉴权与配额。
    top_n 按档位限制（Free≤3，Basic≤5，Pro≤20）；超配额返回 429。
    """
    if not consume(auth.user_id, auth.tier, RESOURCE_JOB_MATCH):
        raise _quota_exceeded_response()
    top_n = clamp_top_n(auth.tier, request.top_n or 5)
    try:
        from tatha.jobs import run_job_match_pipeline

        results, total = run_job_match_pipeline(
            resume_text=request.resume_text,
            top_n=top_n,
            source_id=request.source,
        )
        return JobMatchResponse(
            matches=[r.model_dump() for r in results],
            total_evaluated=total,
        )
    except Exception as e:
        return JobMatchResponse(matches=[], total_evaluated=0, error=str(e))


@app.post("/v1/rag/query", response_model=RagQueryResponse)
def rag_query(request: RagQueryRequest, auth: AuthContext = Depends(get_auth)):
    """
    对私有索引做 RAG 查询：仅使用已构建的命名空间索引，数据不离开本地。V1 需鉴权与配额。
    """
    if not consume(auth.user_id, auth.tier, RESOURCE_RAG):
        raise _quota_exceeded_response()
    try:
        from tatha.retrieval import get_query_engine
        engine = get_query_engine(namespace=request.namespace)
        answer = str(engine.query(request.query))
        return RagQueryResponse(answer=answer, namespace=request.namespace)
    except FileNotFoundError:
        return RagQueryResponse(
            answer="",
            namespace=request.namespace,
            error=f"索引不存在。请先用 build_index_from_dir 或 build_index_from_documents 构建 namespace={request.namespace} 的索引（存储于 .data/indices/<namespace>）。",
        )
    except Exception as e:
        return RagQueryResponse(
            answer="",
            namespace=request.namespace,
            error=str(e),
        )


# ---------- 阶段 7：托管支付开箱用 ----------

@app.post("/v1/orders/checkout", response_model=CheckoutResponse)
def orders_checkout(body: CheckoutRequest, auth: AuthContext = Depends(get_auth)):
    """
    创建托管支付结账：需鉴权，入参 tier/interval/return_url，返回 checkout_url。
    未配置 Lemon Squeezy 时返回 stub URL，便于本地用 stub Webhook 验证档位更新。
    """
    return create_checkout(auth, body)


@app.post("/v1/webhooks/payment")
async def webhooks_payment(request: Request):
    """
    Lemon Squeezy Webhook：校验 X-Signature 后处理 order_created/subscription_created，
    将 meta.custom_data.user_id 对应档位写入 tier_store，下次鉴权生效。
    """
    return await handle_payment_webhook(request)


@app.post("/v1/webhooks/stub-upgrade")
def webhooks_stub_upgrade(body: StubUpgradeRequest) -> dict[str, str]:
    """
    仅未配置 Lemon Squeezy 时可用：本地 stub 模拟支付成功，直接写入档位，用于验证档位更新链路。
    """
    return handle_stub_upgrade(body.user_id, body.tier)
