import asyncio

from jarvis.background.jobs import InProcessJobQueue, JobStatus


def test_background_job_executes() -> None:
    async def scenario() -> None:
        queue = InProcessJobQueue(workers=1)
        await queue.start()

        async def work():
            return {"ok": True}

        job = await queue.submit("demo", work)
        await queue.queue.join()
        assert job.status is JobStatus.SUCCEEDED
        assert job.result == {"ok": True}
        await queue.stop()

    asyncio.run(scenario())
