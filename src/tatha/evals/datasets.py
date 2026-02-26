"""
Pydantic Evals 回归测试数据集：文档提取（resume / poetry / credit）。

通过预设 Case 验证模型表现，改提示词或模型后跑一遍即可发现退化。
"""
from __future__ import annotations

from pydantic_evals import Case, Dataset


def resume_extract_dataset() -> Dataset:
    """简历解析回归用例：输入简历片段，期望提取出姓名/学历/技能等。"""
    return Dataset(
        name="resume_extract",
        cases=[
            Case(
                inputs="张三，本科北京大学计算机系，擅长 Python 与数据分析，有 3 年互联网产品经验。",
                expected_output="张三",
                name="resume_name",
            ),
            Case(
                inputs="李四，硕士清华大学软件学院，技能：Java, 架构设计；经历：5年大厂后端。",
                expected_output="李四",
                name="resume_name_2",
            ),
        ],
    )


def poetry_extract_dataset() -> Dataset:
    """诗词解析回归用例：输入诗词正文，期望提取标题/作者/主题。"""
    return Dataset(
        name="poetry_extract",
        cases=[
            Case(
                inputs="床前明月光，疑是地上霜。举头望明月，低头思故乡。",
                expected_output="思乡",
                name="poetry_theme",
            ),
            Case(
                inputs="静夜思 李白 唐 床前明月光，疑是地上霜。举头望明月，低头思故乡。",
                expected_output="李白",
                name="poetry_author",
            ),
        ],
    )


def credit_extract_dataset() -> Dataset:
    """征信解析回归用例：输入信用报告摘要，期望提取主体名称/报告类型。"""
    return Dataset(
        name="credit_extract",
        cases=[
            Case(
                inputs="主体名称某某科技有限公司，报告类型企业信用报告，摘要说明截至2024年末无不良记录，信用等级A。",
                expected_output="某某科技有限公司",
                name="credit_entity",
            ),
            Case(
                inputs="主体：个人张三；报告类型：个人信用报告；摘要：近24个月还款记录正常，无逾期。",
                expected_output="张三",
                name="credit_entity_person",
            ),
        ],
    )
