"""Mock 职位源：返回固定示例职位，无需外部 API，用于最小闭环与测试。"""
from tatha.jobs.schemas import JobInfo
from .base import JobSource


class MockJobSource(JobSource):
    """内置 5 条示例职位，便于端到端跑通流水线。"""

    def fetch_jobs(self, limit: int = 50) -> list[JobInfo]:
        jobs = [
            JobInfo(
                title="Python 后端工程师",
                company="某科技公司",
                url="https://example.com/job/1",
                location="北京 / 远程",
                description="负责后端服务开发，要求熟悉 Python、FastAPI、数据库，有 AI/LLM 相关经验优先。",
                source="mock",
            ),
            JobInfo(
                title="机器学习工程师",
                company="某 AI 实验室",
                url="https://example.com/job/2",
                location="上海",
                description="参与 NLP/多模态模型研发与落地，要求 PyTorch、Python，有简历解析或 RAG 经验加分。",
                source="mock",
            ),
            JobInfo(
                title="全栈开发工程师",
                company="某创业公司",
                url="https://example.com/job/3",
                location="深圳",
                description="前后端开发，技术栈 React + Python，有自动化/爬虫经验优先。",
                source="mock",
            ),
            JobInfo(
                title="数据工程师",
                company="某互联网公司",
                url="https://example.com/job/4",
                location="杭州",
                description="数据管道与数仓建设，SQL、Spark、Python，有求职/招聘领域数据经验优先。",
                source="mock",
            ),
            JobInfo(
                title="产品经理（AI 方向）",
                company="某 SaaS 公司",
                url="https://example.com/job/5",
                location="远程",
                description="AI 产品规划与需求，懂技术沟通，有 B 端或招聘/HR 产品经验优先。",
                source="mock",
            ),
        ]
        return jobs[: min(limit, len(jobs))]
