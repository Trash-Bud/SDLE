import zmq
import sys
import threading
from lazy_pirate import retry_message
import signal

signal.signal(signal.SIGINT, signal.SIG_DFL)

client_port = "5556"

msg_prefix = "REQUEST: "
if len(sys.argv) > 1:
    client_port = sys.argv[1]
    client_port = int(client_port)

print("CLIENT %s is now ONLINE" % client_port)

# we are the broker's client, so use socket.connect
BROKER_ENDPOINTS = ["tcp://localhost:5001", "tcp://localhost:5002"]

context = zmq.Context()
socket_test_client = context.socket(zmq.PAIR)
socket_test_client.connect("tcp://localhost:%s" % client_port)

subscribed_topics = []


def get_from_topic(topic):
    if topic not in subscribed_topics:
        print("TRYING TO DO GET ON NON SUBSCRIBED TOPIC: CANCELLING")
        return

    msgFromTopic = "GET FROM %s ON TOPIC : %s" % (client_port, topic)
    TIMEOUT = 2500
    REQUEST_TRIES = 3
    retry_message(
        msgFromTopic, TIMEOUT, REQUEST_TRIES, BROKER_ENDPOINTS, "ACK")


def subscribe_a_topic(topic):
    TIMEOUT = 2500
    REQUEST_TRIES = 3
    subMsg = "SUBSCRIBE %s FROM SUBSCRIBER %s" % (topic, client_port)
    got_SUCCESS_response = retry_message(
        subMsg, TIMEOUT, REQUEST_TRIES, BROKER_ENDPOINTS, "ACK")
    if got_SUCCESS_response:
        subscribed_topics.append(topic)
    else:
        print("Something went OOPSIE in broker's side")


def unsubscribe_a_topic(topic):
    TIMEOUT = 2500
    REQUEST_TRIES = 3
    unsubMsg = "UNSUBSCRIBE %s FROM SUBSCRIBER %s" % (topic, client_port)
    got_SUCCESS_response = retry_message(
        unsubMsg, TIMEOUT, REQUEST_TRIES, BROKER_ENDPOINTS, "ACK")
    if got_SUCCESS_response and topic in subscribed_topics:
        subscribed_topics.remove(topic)
    else:
        print("Something went OOPSIE in broker's side")


def PUT_TOPIC(topic, messagedata):
    putMsg = "PUT %s %s" % (topic, messagedata)
    TIMEOUT = 2500
    REQUEST_TRIES = 3
    retry_message(putMsg, TIMEOUT, REQUEST_TRIES, BROKER_ENDPOINTS, "ACK")


# main thread listens from test_client and creates threads to satisfy requests
active_threads = []


while True:
    msg = socket_test_client.recv_string()
    print("FROM TEST_CLIENT: ", msg)
    msgWithoutPrefix = msg.replace(msg_prefix, "")
    msg_args = msgWithoutPrefix.split()
    x = None
    socket_test_client.send_string("ACK recv: %s " % msg)
    if msg_args[0] == "PUT":
        x = threading.Thread(target=PUT_TOPIC, args=msg_args[1:], daemon=True)
    elif msg_args[0] == "GET":
        x = threading.Thread(target=get_from_topic,
                             args=msg_args[1:], daemon=True)
    elif msg_args[0] == "SUBSCRIBE":
        x = threading.Thread(target=subscribe_a_topic,
                             args=msg_args[1:], daemon=True)
    elif msg_args[0] == "UNSUBSCRIBE":
        x = threading.Thread(target=unsubscribe_a_topic,
                             args=msg_args[1:], daemon=True)
    else:
        print("UNRECOGNIZED CLIENT REQUEST ")
        socket_test_client.send_string(
            "ACK : CLIENT has no such REQUEST : " + msg_args[0])
    if x:
        x.start()
        active_threads.append(x)
