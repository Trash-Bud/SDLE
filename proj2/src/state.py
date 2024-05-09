class State:
    def __init__(self, ip, port, username) -> None:
        self.ip = ip
        self.port = port
        self.offline_users = []
        self.followers = []
        self.following = {}
        self.redirects = {}
        self.message_nr = 0
        self.username = username

    def increment_message_counter(self):
        self.message_nr += 1

    def add_offline_users(self, new_offline_user):
        if new_offline_user not in self.offline_users:
            self.offline_users.append(new_offline_user)
            self.followers.remove(new_offline_user)

    def remove_offline_user(self, online_user):

        if online_user in self.offline_users:
            self.offline_users.remove(online_user)
            self.followers.append(online_user)

    def add_follower(self, new_follower):
        self.followers.append(new_follower)

    def remove_follower(self, follower_name):
        self.followers.remove(follower_name)

    def set_following(self, new_following_user, msg_nr):
        self.following[new_following_user] = msg_nr

    def increment_following(self, following_user):
        self.following[following_user] += 1

    def remove_following(self, unfollowing_user):
        self.following.pop(unfollowing_user)

    def get_most_recent_msg_nr(self, user):
        return self.following[user]

    def has_follower(self, new_follower_name):
        return new_follower_name in self.followers

    def add_redirector(self, from_user, to_user):
        if self.redirects.get(from_user):
            self.redirects[from_user].append(to_user)
        else:
            self.redirects[from_user] = [to_user]

    def set_new_state(self, incoming_state):
        self.followers = incoming_state["followers"]
        self.following = incoming_state["following"]
        self.message_nr = incoming_state["msg_nr"]
        self.redirects = incoming_state["redirect"]

    def prepare_new_state(self):
        new_state = {"ip": self.ip, "port": self.port,
                     "followers": self.followers, "following": self.following, "redirect": self.redirects, "msg_nr": self.message_nr}
        return new_state
