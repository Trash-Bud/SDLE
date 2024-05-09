import logging
import asyncio
import json

from kademlia.network import Server

BOOTSTRAP_IP = '127.0.0.1'
BOOTSTRAP_PORT = 8469

""" 
handler = logging.StreamHandler()
formatter = logging.Formatter(
    '%(asctime)s - %(name)s - %(levelname)s - %(message)s')
handler.setFormatter(formatter)
log = logging.getLogger('kademlia')
log.addHandler(handler)
log.setLevel(logging.DEBUG)
"""


class DHT:
    def __init__(self, ip, port) -> None:
        self.ip = ip
        self.port = port
        self.server = Server()
        self.loop = None

    def close_server(self):
        self.server.stop()

    async def get_user_ip_port_and_msg_nr(self, username):
        user_data = await self.server.get(username)
        if user_data:
            user_entry = json.loads(user_data)
            return user_entry["ip"], user_entry["port"], user_entry["msg_nr"]
        else:
            return None

    async def get_user_ip_and_port(self, username):
        user_data = await self.server.get(username)

        if user_data:
            user_entry = json.loads(user_data)
            return user_entry["ip"], user_entry["port"]
        else:
            return None

    async def get_ip_and_port_and_followers(self, usernames):
        res = {}
        for username in usernames:
            result = await self.server.get(username)
            result = json.loads(result)

            if result is not None:
                res[username] = (result["ip"],
                                 result["port"],
                                 result["followers"])

        return res

    async def set_new_user_state(self, username, new_state):
        value_to_set = json.dumps(new_state)
        await self.server.set(username, value_to_set)

    async def login_function(self, username):
        result = await self.server.get(username)
        print(result)
        if not result:
            print("This user is not registered! ")
            return False, None
        user_entry = json.loads(result)

        return True, user_entry

    async def get_user_following(self, username):
        result = await self.server.get(username)
        user_entry = json.loads(result)
        return user_entry["following"]

    async def register_function(self, new_username):
        result = await self.server.get(new_username)
        if result:
            print("This user is already registered")
            self.DHT = json.loads(result)

        else:
            initial_state = {"ip": self.ip, "port": self.port,
                             "followers": [], "following": {}, "redirect": {}, "msg_nr": 0}
            initial_state = json.dumps(initial_state)
            await self.server.set(new_username, initial_state)
        return True

    def run_kademlia(self):
        self.loop = asyncio.get_event_loop()

        self.loop.run_until_complete(
            self.server.listen(self.port, interface=self.ip))
        bootstrap_node = (BOOTSTRAP_IP,  BOOTSTRAP_PORT)
        self.loop.run_until_complete(self.server.bootstrap([bootstrap_node]))

        return self.loop
