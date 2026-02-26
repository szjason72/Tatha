#!/usr/bin/env bash
# 改进成果测试：健康检查、单入口意图、文档解析、文档转换、RAG 查询（可选）
# 使用前请确保：1）已配置 .env（如 OPENAI_API_KEY 或 DEEPSEEK_API_KEY）；2）API 已启动：uv run uvicorn tatha.api.app:app --host 127.0.0.1 --port 8010

set -e
BASE="${BASE_URL:-http://127.0.0.1:8010}"

echo "=== 1. 健康检查 ==="
curl -s "$BASE/health" | python3 -m json.tool

echo ""
echo "=== 2. 单入口 /v1/ask - 职位匹配 ==="
curl -s -X POST "$BASE/v1/ask" -H "Content-Type: application/json" \
  -d '{"message":"帮我匹配一下岗位"}' | python3 -m json.tool

echo ""
echo "=== 3. 单入口 /v1/ask - 简历解析（PydanticAI 边界） ==="
curl -s -X POST "$BASE/v1/ask" -H "Content-Type: application/json" \
  -d '{"message":"解析这段简历：张三，本科北京大学计算机系，擅长 Python 与数据分析，有 3 年互联网产品经验。"}' | python3 -m json.tool

echo ""
echo "=== 4. 文档转换（MarkItDown + 提取） ==="
echo "姓名：李四；学历：硕士 清华大学；技能：Java, 架构设计；经历：5年大厂后端。" > /tmp/tatha_test_resume.txt
curl -s -X POST "$BASE/v1/documents/convert" -F "file=@/tmp/tatha_test_resume.txt" -F "document_type=resume" | python3 -m json.tool

echo ""
echo "=== 5. RAG 查询（需先构建索引：见 README「LlamaIndex」节，或先跳过） ==="
curl -s -X POST "$BASE/v1/rag/query" -H "Content-Type: application/json" \
  -d '{"namespace":"resume","query":"总结文档核心观点"}' | python3 -m json.tool

echo ""
echo "=== 测试完成 ==="
