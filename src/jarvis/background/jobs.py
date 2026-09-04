from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from enum import StrEnum
from uuid import uuid4


class JobStatus(StrEnum):
    QUEUED = "queued"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"


@dataclass(slots=True)
class Job:
    id: str = field(default_factory=lambda: str(uuid4()))
    name: str = "job"
    status: JobStatus = JobStatus.QUEUED
    result: object | None = None
    error: str | None = None


class InProcessJobQueue:
    """Development queue. Production deployments can replace it with Celery/Arq/RQ."""

    def __init__(self, workers: int = 2) -> None:
        self.queue: asyncio.Queue[tuple[Job, Callable[[], Awaitable[object]]]] = asyncio.Queue()
        self.jobs: dict[str, Job] = {}
        self.workers = workers
        self._tasks: list[asyncio.Task] = []

    async def start(self) -> None:
        if self._tasks:
            return
        self._tasks = [
            asyncio.create_task(self._worker(), name=f"jarvis-worker-{i}") for i in range(self.workers)
        ]

    async def stop(self) -> None:
        for task in self._tasks:
            task.cancel()
        await asyncio.gather(*self._tasks, return_exceptions=True)
        self._tasks.clear()

    async def submit(self, name: str, factory: Callable[[], Awaitable[object]]) -> Job:
        job = Job(name=name)
        self.jobs[job.id] = job
        await self.queue.put((job, factory))
        return job

    async def _worker(self) -> None:
        while True:
            job, factory = await self.queue.get()
            try:
                job.status = JobStatus.RUNNING
                job.result = await factory()
                job.status = JobStatus.SUCCEEDED
            except Exception as exc:  # queue boundary records failures
                job.error = str(exc)
                job.status = JobStatus.FAILED
            finally:
                self.queue.task_done()
