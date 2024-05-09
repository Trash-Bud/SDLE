import threading
import json
import os
from snowflake import SnowflakeGenerator
from datetime import datetime

from colorama import Fore
from colorama import Style

class Post:
    def __init__(self, posted_by, post_content, message_nr, id=0, time=0, seen=False):
        self.posted_by = posted_by
        if time == 0:
            time = datetime.timestamp(datetime.now())
        self.time = time
        self.post_content = post_content
        if id == 0:
            id = next(SnowflakeGenerator(10, timestamp=self.time))
        self.id = id
        self.message_nr = message_nr
        self.seen = seen

    def to_json(self):
        return {
            "posted_by": self.posted_by, 
            "post_content": self.post_content, 
            "message_nr":self.message_nr,
            "id": self.id,
            "time": self.time, 
            "seen": self.seen
        }

    def from_json(jsonObj):
        new_post = Post(
            jsonObj["posted_by"],
            jsonObj["post_content"],
            jsonObj["message_nr"],
            jsonObj["id"],
            jsonObj["time"],
            jsonObj["seen"]
        )
        return new_post


class Timeline:
    def __init__(self, username, state) -> None:
        self.lock = threading.RLock()
        self.username = username
        self.state = state
        self.posts = []
        self.missing_posts = {}
        self.get_local_stored_posts()

    def display_timeline(self):
        self.sort_timeline()
        print(f"{self.username}'s TIMELINE: ")
        print("")
        for post in self.posts:
            
            if not post.seen:
                print(f"{Fore.GREEN}Posted by: ", post.posted_by)
                print(f"Tweet: ", post.post_content)
                print(f"{Style.RESET_ALL}")
            else:
                print("Posted by: ", post.posted_by)
                print("Tweet: ", post.post_content)
                print("")
            post.seen = True
        self.save_current_timeline()

    def get_posts_from_user(self, user):
        return list(filter(lambda post: post.posted_by == user, self.posts))

    def get_timeline_messages_from_user(self, user, latest_seen_id):
        def check_user(post):
            if post.posted_by == user and post.message_nr > latest_seen_id:
                return True
            return False

        posts_to_return = filter(check_user, self.posts)
        posts_json = []
        for post in posts_to_return:
            posts_json.append(post.to_json())
        return posts_json

    def add_post(self, new_post, latest_msg_id=None):
        if "time" in new_post and "id" in new_post:
            new_post_entry = Post(
                new_post["posted_by"], new_post["post_content"], message_nr=new_post["message_nr"], 
                id=new_post["id"], time=new_post["time"])
        else: 
            new_post_entry = Post(
                new_post["posted_by"], new_post["post_content"], message_nr=new_post["message_nr"])
        self.lock.acquire()

        if not latest_msg_id or latest_msg_id + 1 == new_post_entry.message_nr:
            self.posts.append(new_post_entry)
            if new_post_entry.posted_by != self.username:
                self.state.increment_following(new_post_entry.posted_by)

            # clear the waiting messages, since we have just received the most recent one
            if self.missing_posts.get(new_post_entry.posted_by, 0) != 0:
                self.missing_posts[new_post_entry.posted_by].clear()

        elif latest_msg_id + 1 < new_post_entry.message_nr:
            # add this post to the entries of messages we need from the user
            user_msgs_ids = self.missing_posts.get(
                new_post_entry.posted_by, [])
            user_msgs_ids.append(new_post_entry.message_nr)
            self.missing_posts[new_post_entry.posted_by] = user_msgs_ids
        elif latest_msg_id == new_post_entry.message_nr:
            # we have already seen this post
            pass
        self.lock.release()
        self.save_current_timeline()

    def delete_posts(self, username):
        self.posts = list(filter(lambda p: p.posted_by != username, self.posts))
        self.save_current_timeline()

    def save_current_timeline(self):
        # saves the current posts to a local file

        with open(f"posts/{self.username}.json", "w+") as f:
            postObj = {"posts": []}
            for post in self.posts:
                postObj["posts"].append(post.to_json())

            json.dump(postObj, f)

    def get_local_stored_posts(self):
        # get the posts stored in the local file. done when initializing the timeline

        if not os.path.exists("posts"):
            os.mkdir("posts")

        try:
            f = open(f"posts/{self.username}.json", "r+")
            data = json.load(f)
            for post in data["posts"]:
                new_post = Post.from_json(post)
                self.posts.append(new_post)

            users_posts = self.get_posts_from_user(self.username)
            self.state.message_nr = users_posts[-1].message_nr

        except:
            pass

    def sort_timeline(self):
        self.posts.sort(key=lambda p: p.time, reverse=True)
