"""根据配置返回当前使用的职位源。"""
import os
from tatha.jobs.sources.base import JobSource
from tatha.jobs.sources.mock import MockJobSource


def get_job_source(source_id: str | None = None) -> JobSource:
    """
    返回职位源实例。
    source_id 可选：mock（默认）、apify_linkedin。
    不传则从环境变量 TATHA_JOB_SOURCE 读取，默认 mock。
    """
    sid = (source_id or os.getenv("TATHA_JOB_SOURCE") or "mock").strip().lower()
    if sid == "apify_linkedin":
        from tatha.jobs.sources.apify_linkedin import ApifyLinkedInJobSource
        return ApifyLinkedInJobSource()
    return MockJobSource()
