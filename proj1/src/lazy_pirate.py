import zmq
import time

SETTLE_DELAY = 2000


def retry_message(requestMsg, timeout, tries, endpoints, ack_msg_expected):
    server_nbr = 0
    ctx = zmq.Context()
    client = ctx.socket(zmq.REQ)
    client.connect(endpoints[server_nbr])
    poller = zmq.Poller()
    poller.register(client, zmq.POLLIN)

    client.send_string(requestMsg)

    expect_reply = True
    while expect_reply:
        socks = dict(poller.poll(timeout))
        if socks.get(client) == zmq.POLLIN:
            reply = client.recv_string()
            replySplit = reply.split()
            print(reply)
            if replySplit[0] == ack_msg_expected:
                print("[INFO]: server replied OK (%s)" % reply)
                expect_reply = False
                return True
            else:
                print("[ERROR]: Unexpected reply from server: %s" % reply)
                return False
        else:
            print("[WARNING]: no response from server, failing over")
            time.sleep(SETTLE_DELAY / 1000)
            poller.unregister(client)
            client.close()
            if tries == 0:
                print(
                    "[ERROR]: Exceeded the maximum number of tries - giving up on this request ")
                return False
            tries -= 1
            server_nbr = (server_nbr + 1) % 2
            print("[INFO]: connecting to server at %s.." %
                  endpoints[server_nbr])
            client = ctx.socket(zmq.REQ)
            poller.register(client, zmq.POLLIN)
            # reconnect and resend request
            client.connect(endpoints[server_nbr])
            client.send_string(requestMsg)
