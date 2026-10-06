import asyncio


class AsyncioSleepDownloaderMiddleware:
    # Used by ShellTest.test_shell_fetch_async_coroutine_runs: the process_request
    # coroutine awaits asyncio and marks the request only after the await has finished.

    async def process_request(self, request, spider):
        await asyncio.sleep(0.1)
        request.meta['r2e_asyncio_mw_done'] = True
        return None
