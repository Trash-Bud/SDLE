from menu_item import MenuItem
from colorama import Fore
from colorama import Style


class Menu:
    def __init__(self) -> None:
        self.option = -1
        self.items = []

    def add_item(self, item):
        self.items.append(item)

    def display_options(self):
        print(f"{Fore.YELLOW}===== OPTIONS ====={Style.RESET_ALL}")
        for index, items in enumerate(self.items):
            print(f"{index + 1} - {items.name}")

    def read_option(self):
        option = None
        while not option or type(option) != int or option > len(self.items) or option < 1:
            option = input("> ")
            try:
                option = int(option)
            except ValueError:
                print(
                    f"{Fore.RED}Please choose one of the valid options{Style.RESET_ALL}")
                continue
            if option > len(self.items) or option < 1:
                print(
                    f"{Fore.RED}Please choose one of the valid options{Style.RESET_ALL}")

        self.option = int(option)

    def run_menu(self):
        self.display_options()
        self.read_option()
        
        return self.items[self.option - 1].run()
