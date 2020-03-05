import asyncio


def maybeAsync(callable, *args):
    if asyncio.iscoroutine(callable):
        return callable

    return asyncio.coroutine(callable)(*args)


def fire(callable, *args, **kwargs):
    return asyncio.ensure_future(maybeAsync(callable, *args))


async def _call_later(delay, callable, *args, **kwargs):
    await asyncio.sleep(delay)
    fire(callable, *args, **kwargs)


def call_later(delay, callable, *args, **kwargs):
    fire(_call_later, delay, callable, *args, **kwargs)