"""职位源抽象：拉取职位列表。"""
from abc import ABC, abstractmethod
from tatha.jobs.schemas import JobInfo


class JobSource(ABC):
    """职位源接口：返回可打分的职位列表。"""

    @abstractmethod
    def fetch_jobs(self, limit: int = 50) -> list[JobInfo]:
        """拉取职位，最多返回 limit 条。"""
        ...
