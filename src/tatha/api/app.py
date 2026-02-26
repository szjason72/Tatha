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
from fastapi import FastAPI, File, Form, UploadFile
from fastapi.responses import HTMLResponse, PlainTextResponse

from .schemas import (
    AskRequest,
    AskResponse,
    DocumentConvertResponse,
    JobMatchRequest,
    JobMatchResponse,
    RagQueryRequest,
    RagQueryResponse,
)
from .central_brain import handle_ask

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


@app.get("/demo.html", response_class=HTMLResponse)
def serve_demo():
    """可选演示页：单文件 HTML，调用 /v1/ask 与 /v1/jobs/match 并在页面展示结果。仅用于开发期直观感受。"""
    path = os.path.join(_ROOT, "demo.html")
    if not os.path.isfile(path):
        return PlainTextResponse("demo.html not found", status_code=404)
    with open(path, "r", encoding="utf-8") as f:
        return HTMLResponse(f.read())


@app.post("/v1/ask", response_model=AskResponse)
def ask(request: AskRequest):
    """单入口：用户需求由此进入，中央大脑解析意图并分发到内部端口，返回统一 JSON。"""
    return handle_ask(request)


@app.post("/v1/documents/convert", response_model=DocumentConvertResponse)
async def documents_convert(
    file: UploadFile = File(..., description="待转换文档（PDF/Word/Excel 等）"),
    document_type: str | None = Form("resume", description="文档类型：resume / poetry / credit，用于选择提取器"),
):
    """
    高效解析标准流程：MarkItDown 多格式 → Markdown，再按 document_type 做可选结构化提取。

    支持格式：PDF、Word(.docx)、Excel(.xlsx)、PPT 等；扫描件或复杂图片表格效果会有波动。
    """
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
    dtype = (document_type or "resume").strip().lower() or "resume"
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
def jobs_match(request: JobMatchRequest):
    """
    职位匹配流水线：拉取职位 → 简历 vs 职位 LLM 打分 → 按综合分排序返回 Top-N。
    职位源默认 mock（示例数据）；配置 TATHA_JOB_SOURCE=apify_linkedin 与 APIFY_API_KEY 可使用 LinkedIn 抓取。
    """
    try:
        from tatha.jobs import run_job_match_pipeline

        results, total = run_job_match_pipeline(
            resume_text=request.resume_text,
            top_n=request.top_n,
            source_id=request.source,
        )
        return JobMatchResponse(
            matches=[r.model_dump() for r in results],
            total_evaluated=total,
        )
    except Exception as e:
        return JobMatchResponse(matches=[], total_evaluated=0, error=str(e))


@app.post("/v1/rag/query", response_model=RagQueryResponse)
def rag_query(request: RagQueryRequest):
    """
    对私有索引做 RAG 查询：仅使用已构建的命名空间索引，数据不离开本地。
    需先通过 build_index_from_dir 或 build_index_from_documents 构建对应 namespace 的索引。
    """
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
