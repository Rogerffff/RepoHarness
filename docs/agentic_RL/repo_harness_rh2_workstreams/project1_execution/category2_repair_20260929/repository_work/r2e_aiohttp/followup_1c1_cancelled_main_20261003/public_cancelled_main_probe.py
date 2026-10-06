"""只调用公开run_app(coroutine)，观察自身取消后的资源收尾。

在原固定Python3.9/aiohttp公开环境执行；不替换库函数，不读隐藏材料，
不计算reward。after_run_app是在观察者补清理之前保存的原始事实。
"""
import argparse
import asyncio
import hashlib
import json
import os
from pathlib import Path
import sys

import aiohttp
from aiohttp import web

ap = argparse.ArgumentParser()
ap.add_argument('--label', required=True, choices=['baseline', 'coder_full_frozen', 'qwen_full_frozen'])
ap.add_argument('--expected-web-sha256', required=True)
ns = ap.parse_args()
web_path = Path(web.__file__).resolve()
web_sha = hashlib.sha256(web_path.read_bytes()).hexdigest()
assert sys.version_info[:2] == (3, 9), sys.version
assert os.getuid() == 54321, os.getuid()
assert str(web_path) == '/testbed/aiohttp/web.py', str(web_path)
assert web_sha == ns.expected_web_sha256.removeprefix('sha256:'), web_sha

loop = asyncio.new_event_loop()
state = {'events': [], 'loop_handler': []}
loop.set_exception_handler(lambda _loop, context: state['loop_handler'].append({
    'message': context.get('message'),
    'exception_type': type(context['exception']).__name__ if context.get('exception') is not None else None,
}))

async def pending_worker():
    state['events'].append('worker_started')
    try:
        await asyncio.Event().wait()
    finally:
        state['events'].append('worker_cleanup')

async def open_generator():
    state['events'].append('generator_started')
    try:
        yield 'armed'
    finally:
        state['events'].append('generator_cleanup')

async def cancelled_app_factory():
    # run_app公开接受Awaitable[Application]；取消发生在真正的_run_app await中。
    state['main_task'] = asyncio.current_task()
    state['worker'] = loop.create_task(pending_worker())
    await asyncio.sleep(0)  # 确认worker进入finally对应的try，不只创建未启动任务。
    state['generator'] = open_generator()  # 保持强引用，避免gc先替库做关闭。
    assert await state['generator'].__anext__() == 'armed'
    state['events'].append('main_self_cancel')
    state['main_task'].cancel()
    await asyncio.sleep(0)
    raise AssertionError('self cancellation did not propagate')

caller_exception = None
try:
    web.run_app(cancelled_app_factory(), loop=loop, handle_signals=False, print=None)
except BaseException as error:
    caller_exception = {'type': type(error).__name__, 'message': str(error)}

main = state.get('main_task')
worker = state.get('worker')
generator = state.get('generator')
after = {
    'caller_exception': caller_exception,
    'main_done': None if main is None else main.done(),
    'main_cancelled': None if main is None else main.cancelled(),
    'worker_done': None if worker is None else worker.done(),
    'worker_cancelled': None if worker is None else worker.cancelled(),
    'generator_closed': None if generator is None else generator.ag_frame is None,
    'loop_closed': loop.is_closed(),
    'pending_task_count': len(asyncio.all_tasks(loop)),
    'events': list(state['events']),
    'loop_handler': list(state['loop_handler']),
}

# 观察结束后只为本进程回收资源；绝不把这段动作计成run_app清理。
observer_cleanup = {'needed': not loop.is_closed(), 'error': None}
if not loop.is_closed():
    try:
        tasks = list(asyncio.all_tasks(loop))
        for task in tasks:
            task.cancel()
        if tasks:
            loop.run_until_complete(asyncio.gather(*tasks, return_exceptions=True))
        loop.run_until_complete(loop.shutdown_asyncgens())
    except BaseException as error:
        observer_cleanup['error'] = {'type': type(error).__name__, 'message': str(error)}
    finally:
        loop.close()
asyncio.set_event_loop(None)

print(json.dumps({
    'schema_id': 'rh2.category2.aiohttp.public_cancelled_main_observation.v1',
    'label': ns.label,
    'identity': {'uid': os.getuid(), 'python': sys.version, 'executable': sys.executable,
                 'aiohttp_file': aiohttp.__file__, 'web_file': str(web_path), 'web_sha256': web_sha},
    'after_run_app_before_observer_cleanup': after,
    'observer_cleanup': observer_cleanup,
    'loop_closed_after_observer_cleanup': loop.is_closed(),
    'reward_computed': False,
}, ensure_ascii=False, sort_keys=True))
