import asyncio
import json
from threading import Thread
import os
from random import choices
from message_sender import MessageSender

from colorama import Fore
from colorama import Style


MAX_DIRECT_FOLLOWERS = 2
NUM_REDIRECTING_USERS = 1


class MessageListener(Thread):
    def __init__(self, ip, port, DHT, kademlia_loop, state, timeline) -> None:
        super(MessageListener, self).__init__()
        self.ip = ip
        self.port = port
        self.server = None
        self.DHT = DHT
        self.state = state
        self.timeline = timeline
        self.listener_loop = None
        self.kademlia_loop = kademlia_loop
        self.message_sender = MessageSender(
            self.DHT, self.state, self.timeline, self.kademlia_loop)

    def handle_follow_msg(self, new_follow_username):
        if not self.state.has_follower(new_follow_username):
            if len(self.state.followers) >= MAX_DIRECT_FOLLOWERS:
                # we already establish too many connections of our own - we will tell one of our followers to redirect this message
                future = asyncio.run_coroutine_threadsafe(
                    self.DHT.get_ip_and_port_and_followers(self.state.followers), self.kademlia_loop)
                followers_info = future.result()

                redirect_request = {
                    "redirect": {
                        "from": self.state.username,
                        "to": new_follow_username
                    }
                }

                redirect_request = json.dumps(redirect_request) + "\n"

                users = dict(followers_info)
                usernames = list(users.keys())

                followers_weights = [len(z) for (y, w, z) in users.values()]
                followers_weights = [1.0 / (w) for w in followers_weights]

                # we want the users with the least followers to end up being responsible for redirecting to not overload any one user
                # with too many connections

                redirector_users = choices(usernames,
                                           weights=followers_weights, k=NUM_REDIRECTING_USERS)

                tasks = []
                for user in redirector_users:
                    future = asyncio.run_coroutine_threadsafe(
                        self.DHT.get_user_ip_and_port(user), self.kademlia_loop)
                    ip, port = future.result()

                    tasks.append(self.send_message_to_user(
                        ip, port, redirect_request))

                asyncio.gather(*tasks)

            else:
                self.state.add_follower(new_follow_username)
                new_state_obj = self.state.prepare_new_state()
                asyncio.run_coroutine_threadsafe(
                    self.DHT.set_new_user_state(
                        self.state.username, new_state_obj),
                    self.kademlia_loop)
            return True
        return False

    def handle_unfollow_msg(self, unfollow_username):
        if self.state.has_follower(unfollow_username):
            self.state.remove_follower(unfollow_username)
            new_state_obj = self.state.prepare_new_state()
            asyncio.run_coroutine_threadsafe(
                self.DHT.set_new_user_state(
                    self.state.username, new_state_obj),
                self.kademlia_loop)
            return True
        return False

    async def handle_post_reception(self, post):
        post_sender = post["posted_by"]
        latest_known_msg_id = self.state.get_most_recent_msg_nr(post_sender)
        if latest_known_msg_id + 1 < post["message_nr"]:
            await self.message_sender.request_missed_messages()
            return
        self.timeline.add_post(post, latest_known_msg_id)
        # Redirect posts to the people we are responsible for
        post_string = json.dumps(post) + '\n'
        if post_sender in self.state.redirects:
            for user in self.state.redirects[post_sender]:
                future = asyncio.run_coroutine_threadsafe(
                    self.DHT.get_user_ip_and_port(user), self.kademlia_loop)

                ip, port = future.result()
                self.message_sender.send_message_to_user(ip, port, post_string)

        value = self.state.prepare_new_state()

        asyncio.run_coroutine_threadsafe(
            self.DHT.set_new_user_state(
                self.state.username, value),
            self.kademlia_loop)

    def handle_messages_request(self, user, latest_seen_id):
        messages = self.timeline.get_timeline_messages_from_user(
            user, latest_seen_id)
        return messages

    def handle_redirect(self, to_user, from_user):
        self.DHT.add_redirector(from_user, to_user)
        asyncio.run_coroutine_threadsafe(
            self.DHT.set_new_user_state(),
            self.kademlia_loop)

    def handle_online_msg(self, online_user):
        self.state.remove_offline_user(online_user)

    async def handle_messages(self, reader, writer):
        while True:
            data = await reader.readline()
            addr = writer.get_extra_info('peername')
            if not data:
                break
            json_string = data.decode()
            received_msg = json.loads(json_string)
            print(f"Received {data!r} from {addr!r}")

            if "follow" in received_msg:
                new_follow_username = received_msg["follow"]["username"]
                follow_sucess = self.handle_follow_msg(new_follow_username)
                if follow_sucess:
                    print("New follower: ", new_follow_username)
                    posts = self.handle_messages_request(
                        self.state.username, 0)
                    data = {"requested_posts":  posts}
                    json_string = json.dumps(data) + '\n'
                    writer.write(json_string.encode())
                    print("Answered message request: ", json_string)
                else:
                    print(f"User {new_follow_username } already followed you!")
                    writer.write(b"0\n")
                await writer.drain()
            elif "unfollow" in received_msg:
                unfollow_username = received_msg["unfollow"]["username"]
                unfollow_sucess = self.handle_unfollow_msg(unfollow_username)
                if unfollow_sucess:
                    print("Stopped following you: ", unfollow_username)
                    writer.write(b"1\n")
                else:
                    print(
                        f"User {unfollow_username} was not following you! This message should never be printed!")
                    writer.write(b"0\n")
                await writer.drain()
            elif "post" in received_msg:
                post = received_msg["post"]
                await self.handle_post_reception(post)
                writer.write(b"1\n")
                await writer.drain()

            elif "online" in received_msg:
                self.handle_online_msg(received_msg["online"]["username"])

                writer.write(b"1\n")
                await writer.drain()
            elif "msgs_request" in received_msg:
                msgs_from_user = received_msg["msgs_request"]["username"]
                latest_seen_id = received_msg["msgs_request"]["latest_seen_msg"]
                posts = self.handle_messages_request(
                    msgs_from_user, latest_seen_id)
                data = {"requested_posts":  posts}
                json_string = json.dumps(data) + '\n'
                writer.write(json_string.encode())
                print("Answered message request: ", json_string)
                await writer.drain()
            elif "redirect" in received_msg:
                from_user = received_msg["redirect"]["from"]
                to_user = received_msg["redirect"]["to"]
                self.handle_redirect(to_user, from_user)
                print("Added redirector")
            elif "requested_posts" in received_msg:
                new_posts = received_msg["requested_posts"]
                for post in new_posts:
                    self.timeline.add_post(post)
                writer.write(b"1\n")
                print("Handled requested_posts")
                await writer.drain()
        writer.close()

    async def run_server(self):

        await self.message_sender.notify_followings()

        await self.message_sender.request_missed_messages()
        try:
            self.server = await asyncio.start_server(
                self.handle_messages, self.ip, self.port)
        except OSError:
            print(f"{Fore.RED}Port already in use. Aborting...{Style.RESET_ALL}")
            os._exit(1)

        #print(f'Listening for TCP connections on {self.ip}:{self.port}')

        await self.server.serve_forever()

    def run(self):
        self.listener_loop = asyncio.new_event_loop()
        result = self.listener_loop.run_until_complete(self.run_server())

    def close_server(self):
        self.server.close()
