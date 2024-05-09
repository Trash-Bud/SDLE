import asyncio
import json


class MessageSender:
    def __init__(self, DHT, state, timeline, kademlia_loop) -> None:
        self.DHT = DHT
        self.state = state
        self.timeline = timeline
        self.kademlia_loop = kademlia_loop

    async def notify_followings(self):
        online_msg = {"online":  {"username":  self.state.username}}
        online_msg = json.dumps(online_msg) + "\n"
        tasks = []
        for following_username in self.state.following.keys():
            # HERE: get ip and port from kademlia - NO GUARANTEE OUR INTERNAL IP AND PORT ARE UPDATED
            future = asyncio.run_coroutine_threadsafe(
                self.DHT.get_user_ip_and_port(following_username), self.kademlia_loop)
            ip, port = future.result()

            tasks.append(self.send_message_to_user(ip, port, online_msg))

        await asyncio.gather(*tasks)

    async def request_missed_messages(self):
        tasks = []
        for following_username in self.state.following.keys():
            latest_msg_id = self.state.following[following_username]
            request_msg = {"msgs_request": {
                "username": following_username, "latest_seen_msg": latest_msg_id}}
            request_msg = json.dumps(request_msg) + "\n"
            future = asyncio.run_coroutine_threadsafe(
                self.DHT.get_user_ip_and_port(following_username), self.kademlia_loop)
            ip, port = future.result()
            tasks.append(self.send_message_to_user(ip, port, request_msg))

        finished_tasks_result = await asyncio.gather(*tasks)
        for task in finished_tasks_result:
            if not task[0]:
                continue
            new_posts = json.loads(task[1])["requested_posts"]
            for post in new_posts:
                post_in_timeline = {}
                post_in_timeline["posted_by"] = post["posted_by"]
                post_in_timeline["post_content"] = post["post_content"]
                post_in_timeline["id"] = post["id"]
                post_in_timeline["message_nr"] = post["message_nr"]
                post_in_timeline["time"] = post["time"]
                post_in_timeline["id"] = post["id"]

                self.timeline.add_post(post_in_timeline)
        value = self.state.prepare_new_state()

        await self.DHT.set_new_user_state(self.state.username, value)

    async def send_message_to_user(self, ip, port, message):
        message_sent_sucess = True
        return_data = None
        try:
            try:
                reader, writer = await asyncio.open_connection(
                    ip, port, loop=asyncio.get_event_loop())

                writer.write(message.encode())

                # get the response (either 0 or 1)
                return_data = (await reader.readline()).strip().decode()

                await writer.drain()

                writer.close()

                return message_sent_sucess, return_data
            except ConnectionResetError:  # try again
                reader, writer = await asyncio.open_connection(
                    ip,
                    port,
                    loop=asyncio.get_event_loop())

                writer.write(message.encode())

                # get the response (either 0 or 1)
                return_data = (await reader.readline()).strip().decode()

                await writer.drain()
                writer.close()

                return message_sent_sucess, return_data
        except Exception as e:
            print(e)
            message_sent_sucess = False

        return message_sent_sucess, return_data

    async def post_message(self, message):
        self.state.increment_message_counter()
        
        data = {"post": {"posted_by": self.state.username,
                         "post_content": message, "message_nr": self.state.message_nr}}

        # add the post to the timeline
        self.timeline.add_post(data["post"])

        data = json.dumps(data) + "\n"
        tasks = []
        for follower in self.state.followers:
            # HERE: get ip and port from kademlia - NO GUARANTEE OUR INTERNAL IP AND PORT ARE UPDATED
            print("get user ip and PORT for: ", follower)

            ip, port = await self.DHT.get_user_ip_and_port(follower)
            tasks.append(self.send_message_to_user(ip, port, data))

        finished = await asyncio.gather(*tasks)

        # establishing a connection with these users proves unsucessful
        for i in range(len(finished)):
            if not finished[i][0]:
                self.state.add_offline_users(self.state.followers[i])
        value = self.state.prepare_new_state()

        await self.DHT.set_new_user_state(self.state.username, value)

    async def unfollow_user(self, user_to_unfollow):
        if user_to_unfollow not in self.state.following:
            print("You do not follow this user!")
            return
        query_result = await self.DHT.get_user_ip_port_and_msg_nr(user_to_unfollow)
        print(query_result)
        if not query_result:
            print("This user does not exist! You cannot unfollow them! ")
            return
        (new_following_ip, new_following_port,
         msg_nr) = query_result
        # send the unfollow message

        unfollow_message = {"unfollow": {"username": self.state.username}}
        unfollow_message = json.dumps(unfollow_message) + "\n"

        response_status, answer = await self.send_message_to_user(
            new_following_ip, new_following_port, unfollow_message)
        if not response_status:
            print("It's not possible to unfollow that user right now!"
                  "(user offline)")
        elif answer == '1':
            print("You unfollowed %s successfully" % user_to_unfollow)

            self.state.remove_following(user_to_unfollow)
            value = self.state.prepare_new_state()
            self.timeline.delete_posts(user_to_unfollow)

            await self.DHT.set_new_user_state(self.state.username, value)

    async def follow_user(self, user_to_follow):
        if user_to_follow == self.state.username:
            print("You can't follow yourself! ")
            return
        if user_to_follow in self.state.following:
            print("You already follow this user!")
            return
        query_result = await self.DHT.get_user_ip_port_and_msg_nr(user_to_follow)
        print(query_result)
        if not query_result:
            print("This user does not exist! You cannot follow them! ")
            return

        (new_following_ip, new_following_port,
         msg_nr) = query_result

        # send the follow message

        follow_message = {"follow": {"username": self.state.username}}
        follow_message = json.dumps(follow_message) + "\n"

        response_status, answer = await self.send_message_to_user(
            new_following_ip, new_following_port, follow_message)
        if not response_status:
            print("It's not possible to follow that user right now!"
                  "(user offline)")
        elif answer == '0':
            print("It's not possible to follow %s (already followed)" % user_to_follow)
        else:
            print("You followed %s successfully" % user_to_follow)
            self.state.set_following(user_to_follow, 0)

            new_posts = json.loads(answer)["requested_posts"]

            for post in new_posts:
                print(post)
                self.timeline.add_post(post)

            print("Handled requested_posts")
            value = self.state.prepare_new_state()
            await self.DHT.set_new_user_state(self.state.username, value)
