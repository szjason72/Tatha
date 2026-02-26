#!/usr/bin/env python3
"""
征信文本解析本地测试：直接调用 run_credit_analysis，不依赖 API 服务。
用法: uv run python scripts/test_credit_analysis.py [可选：自定义文本或文件路径]
需配置 .env 中 DEEPSEEK_API_KEY（或 OPENAI_API_KEY）与 TATHA_DEFAULT_MODEL。
"""
import sys
from pathlib import Path

# 示例征信/信用报告摘要（个人 + 企业各一）
SAMPLE_PERSON = (
    "主体：个人张三；报告类型：个人信用报告；"
    "摘要：近24个月还款记录正常，无逾期。"
)
SAMPLE_ENTERPRISE = (
    "主体名称某某科技有限公司，报告类型企业信用报告，"
    "摘要说明截至2024年末无不良记录，信用等级A。"
)


def main():
    if len(sys.argv) > 1:
        arg = sys.argv[1].strip()
        if Path(arg).exists():
            text = Path(arg).read_text(encoding="utf-8", errors="replace")
            print(f"从文件读取: {arg}\n")
        else:
            text = arg
            print("使用命令行传入文本\n")
    else:
        text = SAMPLE_ENTERPRISE
        print("使用默认企业信用示例文本\n")

    print("=== 输入文本（前 300 字）===")
    print(text[:300] + ("..." if len(text) > 300 else ""))
    print()

    print("=== run_credit_analysis 结果 ===")
    try:
        from tatha.agents import run_credit_analysis

        result = run_credit_analysis(text)
        print(f"entity_name: {result.entity_name!r}")
        print(f"report_type: {result.report_type!r}")
        print(f"summary:     {result.summary!r}")
        print()
        print("model_dump:", result.model_dump())
    except Exception as e:
        print(f"失败: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

    print("\n=== 完成 ===")


if __name__ == "__main__":
    main()
