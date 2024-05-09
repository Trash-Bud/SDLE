import sys
import time
import asyncio


class InputGetter:
    def __init__(self, loop=None):
        self.loop = loop or asyncio.get_event_loop()
        self.q = asyncio.Queue(loop=self.loop)

    def got_input(self):
        asyncio.ensure_future(self.q.put(sys.stdin.readline()), loop=self.loop)

    async def __call__(self, msg, end=''):
        print(msg, end=end)
        sys.stdout.flush()
        self.loop.add_reader(sys.stdin, self.got_input)
        result = (await self.q.get()).rstrip('\n')
        self.loop.remove_reader(sys.stdin)
        return result
