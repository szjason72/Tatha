"""
Apify LinkedIn 职位源：通过 Apify LinkedIn Job Scraper 拉取职位。
需配置 APIFY_API_KEY；可选指定 actor 或使用默认。
参考 DailyJobMatch / JobMatchAI 的用法。
"""
import os
from tatha.jobs.schemas import JobInfo
from .base import JobSource


# Apify 默认 LinkedIn Jobs Scraper actor（按结果付费的常见选择）
DEFAULT_ACTOR_ID = "bHzefUZlZRKWxkTck"  # 示例 ID，实际以 Apify 控制台为准


class ApifyLinkedInJobSource(JobSource):
    """
    从 Apify 拉取 LinkedIn 职位。
    若未配置 APIFY_API_KEY 或 apify-client 未安装，fetch_jobs 返回空列表。
    """

    def __init__(
        self,
        api_key: str | None = None,
        actor_id: str | None = None,
        search_keywords: str = "Python developer",
        max_items: int = 20,
    ):
        self.api_key = (api_key or os.getenv("APIFY_API_KEY") or "").strip()
        self.actor_id = (actor_id or os.getenv("APIFY_LINKEDIN_ACTOR_ID") or DEFAULT_ACTOR_ID).strip()
        self.search_keywords = search_keywords
        self.max_items = max_items

    def fetch_jobs(self, limit: int = 50) -> list[JobInfo]:
        if not self.api_key:
            return []
        try:
            from apify_client import ApifyClient
        except ImportError:
            return []
        client = ApifyClient(self.api_key)
        run_input = {
            "searchKeywords": self.search_keywords,
            "maxItems": min(limit, self.max_items),
        }
        try:
            run = client.actor(self.actor_id).call(run_input=run_input)
            items = list(client.dataset(run["defaultDatasetId"]).iterate_items())
        except Exception:
            return []
        jobs: list[JobInfo] = []
        for item in items:
            title = (item.get("title") or item.get("position") or "未知职位")
            company = (item.get("companyName") or item.get("company") or "未知公司")
            url = item.get("url") or item.get("link")
            location = item.get("location") or item.get("place")
            desc = item.get("description") or item.get("jobDescription") or ""
            jobs.append(
                JobInfo(
                    title=title,
                    company=company,
                    url=url,
                    location=location,
                    description=desc[:2000] if desc else None,
                    source="apify_linkedin",
                )
            )
        return jobs
