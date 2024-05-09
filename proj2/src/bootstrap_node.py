from kademlia.network import Server
import asyncio
import logging

BOOTSTRAP_IP = '127.0.0.1'
BOOTSTRAP_PORT = 8469

handler = logging.StreamHandler()
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s'
                              ' - %(message)s')
handler.setFormatter(formatter)
log = logging.getLogger('kademlia')
log.addHandler(handler)
log.setLevel(logging.DEBUG)


class BootstrapNode:
    def __init__(self, bootstrap_ip, bootstrap_port) -> None:
        self.bootstrap_ip = bootstrap_ip
        self.bootstrap_port = bootstrap_port
        self.server = Server()

    def serve(self):
        loop = asyncio.get_event_loop()

        loop.run_until_complete(
            self.server.listen(self.bootstrap_port, interface=self.bootstrap_ip))

        try:
            loop.run_forever()
        except KeyboardInterrupt:
            pass
        finally:
            self.server.stop()
            loop.close()


if __name__ == '__main__':
    bootstrap_node = BootstrapNode(BOOTSTRAP_IP, BOOTSTRAP_PORT)
    bootstrap_node.serve()
