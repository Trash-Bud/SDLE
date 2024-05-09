from message_handler import MessageListener
from message_sender import MessageSender
from timeline import Timeline
from state import State
import asyncio
from menu_item import MenuItem
from menu import Menu
from kademlia_DHT import DHT
from threading import Thread
import sys
from input_getter import InputGetter
from colorama import Fore
from colorama import Style

BOOTSTRAP_IP = '127.0.0.1'
BOOTSTRAP_PORT = 8469


class Node:
    def __init__(self, ip, port) -> None:
        self.username = None
        self.ip = ip
        self.port = port
        self.message_sender = None
        self.timeline = None
        self.main_menu = Menu()
        self.auth_menu = Menu()
        self.DHT = DHT(ip, port)
        self.loop = asyncio.get_event_loop()
        self.server = None

    def build_main_menu(self):
        self.main_menu.add_item(
            MenuItem("Follow someone", self.follow_user, []))
        self.main_menu.add_item(
            MenuItem("Unfollow someone", self.unfollow_user, []))
        self.main_menu.add_item(
            MenuItem("Write a post", self.make_post, []))
        self.main_menu.add_item(
            MenuItem("Show timeline", self.show_timeline, []))
        self.main_menu.add_item(
            MenuItem("Show followers", self.show_followers, []))
        self.main_menu.add_item(
            MenuItem("Show following", self.show_following, []))
        self.main_menu.add_item(MenuItem("Exit", exit, [0]))

    def build_auth_menu(self):
        self.auth_menu.add_item(MenuItem("Register", self.register, []))
        self.auth_menu.add_item(MenuItem("LogIn", self.logIn, []))
        self.auth_menu.add_item(
            MenuItem("Exit", exit, [0]))

    def show_followers(self):
        print(f"{self.state.username} is being followed by: ")
        for follower_name in self.state.followers:
            print(f" - {follower_name}")
        return True

    def show_following(self):
        print(f"{self.state.username} is following: ")
        for following_name in self.state.following.keys():
            print(f" - {following_name}")
        return True

    async def show_timeline(self):
        self.timeline.display_timeline()
        return True

    async def make_post(self):
        print("Write your cringe post, or 'q' to leave")
        post = await self.input_getter("> ")
        if post == 'q':
            return True

        try:
            await self.message_sender.post_message(post)
        except Exception as e:
            print(e)
            return False

        return True

    def cleanup(self):
        if self.server:
            self.server.close()
            self.loop.run_until_complete(self.server.wait_closed())

        self.kademlia_loop.run_until_complete(self.DHT.close_server())
        self.loop.close()

    async def follow_user(self):
        user_to_follow = await self.ask_for_username()
        if user_to_follow == 'q':
            return True
        try:
            await self.message_sender.follow_user(user_to_follow)
        except Exception as e:
            print(e)
            return False
        return True

    async def unfollow_user(self):
        user_to_unfollow = await self.ask_for_username()
        if user_to_unfollow == 'q':
            return True
        try:
            await self.message_sender.unfollow_user(user_to_unfollow)
        except Exception as e:
            print(e)
            return False
        return True

    async def logIn(self):
        print(f"{Fore.YELLOW}===== LOGIN ====={Style.RESET_ALL}")
        login_sucess = False
        initial_state = None
        while not login_sucess:
            self.username = await self.ask_for_username()
            if self.username == 'q':
                return True
            login_sucess, initial_state = await self.DHT.login_function(self.username)

        self.state = State(self.ip, self.port, self.username)
        self.timeline = Timeline(self.username, self.state)
        self.state.set_new_state(initial_state)
        self.message_handler = MessageListener(
            self.ip, self.port, self.DHT, self.kademlia_loop, self.state, self.timeline)
        self.message_handler.daemon = True
        self.message_handler.start()
        self.message_sender = MessageSender(
            self.DHT, self.state, self.timeline, self.kademlia_loop)

        return False

    async def register(self):
        print(f"{Fore.YELLOW}===== REGISTER ====={Style.RESET_ALL}")
        login_sucess = False
        while not login_sucess:
            self.username = await self.ask_for_username()
            login_sucess = await self.DHT.register_function(self.username)
        return True

    async def ask_for_username(self):
        username = None
        while not username:
            print("Please provide a username, or 'q' to leave")
            while not username:
                username = await self.input_getter("> ")
                if (username == 'q'):
                    return 'q'
                if not username:
                    print(
                        f"{Fore.RED}Please provide a valid username to logIn{Style.RESET_ALL}")
                continue

        return username

    def run_node(self):
        self.kademlia_loop = self.DHT.run_kademlia()
        self.input_getter = InputGetter(self.kademlia_loop)
        Thread(target=self.kademlia_loop.run_forever, daemon=True).start()
        self.build_main_menu()
        self.build_auth_menu()
        try:
            while self.auth_menu.run_menu():
                pass
            while self.main_menu.run_menu():
                pass
        except SystemExit:
            pass
        except KeyboardInterrupt:
            pass
        finally:
            pass
            # self.cleanup()


def main():
    ip, port = parse_args()
    node = Node(ip, port)
    node.run_node()


def parse_args():
    if (len(sys.argv) < 5):
        print(f"{Fore.RED}Usage: py node.py -a <ADDRESS> -p <PORT>{Style.RESET_ALL}")
        exit(-1)
    a, ip, p, port = sys.argv[1:]
    if (a != "-a"):
        print(f"{Fore.RED}Usage: py node.py -a <ADDRESS> -p <PORT>{Style.RESET_ALL}")
        exit(-1)
    if (p != "-p"):
        print(f"{Fore.RED}Usage: py node.py -a <ADDRESS> -p <PORT>{Style.RESET_ALL}")
        exit(-1)
    try:
        int(port)
    except ValueError:
        print("<PORT> must be an integer")
        exit(-1)
    return ip, int(port)


if __name__ == '__main__':
    main()
