"""
职位源：拉取职位列表，供流水线打分。
- mock：内置几条示例职位，无需 API Key，用于最小闭环与测试。
- apify_linkedin：Apify LinkedIn Job Scraper，需 APIFY_API_KEY。
"""
from .base import JobSource
from .mock import MockJobSource
from .registry import get_job_source

__all__ = ["JobSource", "MockJobSource", "get_job_source"]
