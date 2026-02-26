#!/usr/bin/env bash
# 改进成果测试：健康检查、单入口意图、文档解析、文档转换、RAG 查询（可选）
# 使用前请确保：1）已配置 .env（如 DEEPSEEK_API_KEY）；2）API 已启动：uv run uvicorn tatha.api.app:app --host 127.0.0.1 --port 8010

set -e
BASE="${BASE_URL:-http://127.0.0.1:8010}"

echo "=== 1. 健康检查 ==="
HEALTH=$(curl -s -o /dev/null -w "%{http_code}" "$BASE/health" 2>/dev/null || echo "000")
if [ "$HEALTH" != "200" ]; then
  echo "失败: 无法访问 $BASE/health (HTTP $HEALTH)。请先启动 API："
  echo "  uv run uvicorn tatha.api.app:app --host 127.0.0.1 --port 8010"
  exit 1
fi
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
echo "=== 5. 单入口 /v1/ask - 诗词/陪伴（poetry 意图） ==="
curl -s -X POST "$BASE/v1/ask" -H "Content-Type: application/json" \
  -d '{"message":"推荐一句诗"}' | python3 -m json.tool

echo ""
echo "=== 6. 单入口 /v1/ask - 诗词解析（带正文，PydanticAI PoetryAnalysis） ==="
curl -s -X POST "$BASE/v1/ask" -H "Content-Type: application/json" \
  -d '{"message":"解析这首词：床前明月光，疑是地上霜。举头望明月，低头思故乡。"}' | python3 -m json.tool

echo ""
echo "=== 7. RAG 查询 resume（需先构建索引，见 README） ==="
curl -s -X POST "$BASE/v1/rag/query" -H "Content-Type: application/json" \
  -d '{"namespace":"resume","query":"总结文档核心观点"}' | python3 -m json.tool

echo ""
echo "=== 8. RAG 查询 poetry（可选，需先 build_poetry_index.py 或 build_index_from_documents namespace=poetry） ==="
curl -s -X POST "$BASE/v1/rag/query" -H "Content-Type: application/json" \
  -d '{"namespace":"poetry","query":"推荐一句思乡的诗"}' | python3 -m json.tool

echo ""
echo "=== 9. 文档转换 - 征信（document_type=credit） ==="
echo "主体：个人张三；报告类型：个人信用报告；摘要：近24个月还款记录正常，无逾期。" > /tmp/tatha_test_credit.txt
R9=$(curl -s -X POST "$BASE/v1/documents/convert" -F "file=@/tmp/tatha_test_credit.txt" -F "document_type=credit")
echo "$R9" | python3 -m json.tool
echo "$R9" | python3 -c "import sys,json; d=json.load(sys.stdin); assert d.get('markdown') is not None or d.get('error') is not None, 'convert 应返回 markdown 或 error'" || exit 1

echo ""
echo "=== 10. 单入口 /v1/ask - 征信/信用（credit 意图，无正文） ==="
R10=$(curl -s -X POST "$BASE/v1/ask" -H "Content-Type: application/json" -d '{"message":"查一下征信"}')
echo "$R10" | python3 -m json.tool
echo "$R10" | python3 -c "import sys,json; d=json.load(sys.stdin); assert d.get('intent')=='credit', '意图应为 credit'" || exit 1

echo ""
echo "=== 11. 单入口 /v1/ask - 征信解析（带正文，PydanticAI CreditAnalysis） ==="
R11=$(curl -s -X POST "$BASE/v1/ask" -H "Content-Type: application/json" \
  -d '{"message":"解析这段信用报告摘要：主体名称某某科技有限公司，报告类型企业信用报告，摘要说明截至2024年末无不良记录，信用等级A。"}')
echo "$R11" | python3 -m json.tool
echo "$R11" | python3 -c "
import sys, json
d = json.load(sys.stdin)
r = d.get('result') or {}
if r.get('status') == 'ok':
    assert r.get('extracted') is not None, 'status=ok 时应有 extracted'
    e = r['extracted']
    # 业务流程：匹配后查该公司征信，主体明确，不应缺失
    assert e.get('entity_name'), '匹配后查征信场景下 extracted 应有 entity_name'
    assert e.get('report_type') or e.get('summary'), '企业信用报告应有 report_type 或 summary'
" || exit 1

echo ""
echo "=== 12. E2E Resume → Job → Company（三阶段流程）==="
RESUME_JSON=$(python3 -c "
import json
print(json.dumps({
    'resume_text': '张三，本科北京大学计算机系，擅长 Python、FastAPI、数据分析，3 年互联网产品经验。',
    'top_n': 3
}))
")
R_JOB=$(curl -s -X POST "$BASE/v1/jobs/match" -H "Content-Type: application/json" -d "$RESUME_JSON")
echo "Job 匹配响应（前 500 字）:"
echo "$R_JOB" | head -c 500
echo ""
echo "$R_JOB" | python3 -c "
import sys, json
d = json.load(sys.stdin)
matches = d.get('matches') or []
total = d.get('total_evaluated') or 0
assert len(matches) > 0, 'E2E 应有至少一条职位匹配'
company = (matches[0].get('job') or {}).get('company') or ''
assert company, '第一条匹配应含 job.company'
print('First company:', company)
# 写临时文件供下一步 ask 使用
with open('/tmp/tatha_e2e_company.txt', 'w') as f:
    f.write(company)
" || exit 1
COMPANY=$(cat /tmp/tatha_e2e_company.txt)
ASK_CREDIT_JSON=$(python3 -c "
import json, sys
company = open('/tmp/tatha_e2e_company.txt').read().strip()
msg = f'解析这家公司的征信：主体名称{company}，报告类型企业信用报告，摘要说明经营正常。'
print(json.dumps({'message': msg}))
")
R_CREDIT=$(curl -s -X POST "$BASE/v1/ask" -H "Content-Type: application/json" -d "$ASK_CREDIT_JSON")
echo "征信解析响应（前 400 字）:"
echo "$R_CREDIT" | head -c 400
echo ""
echo "$R_CREDIT" | python3 -c "
import sys, json
d = json.load(sys.stdin)
assert d.get('intent') == 'credit', 'E2E 第三步应为 credit 意图'
r = d.get('result') or {}
if r.get('status') == 'ok':
    e = r.get('extracted') or {}
    assert e.get('entity_name'), '匹配后查该公司征信应有 entity_name'
" || exit 1

echo ""
echo "=== 测试完成 ==="
