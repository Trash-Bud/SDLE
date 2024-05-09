from socket import close
import zmq
from topic import Topic, Message
import time
import threading
import signal
import json
import sys
from BStarState import *


if(len(sys.argv) < 2):
    print("Must say wheter its primary (PRIMARY) or backup(BACKUP) server !")
    exit(0)

is_primary = True
is_backup = True
if (sys.argv[1] == "PRIMARY"):
    is_backup = False
elif sys.argv[1] == "BACKUP":
    is_primary = False

context = zmq.Context()
statepub = context.socket(zmq.PUB)
statesub = context.socket(zmq.SUB)
statesub.setsockopt_string(zmq.SUBSCRIBE, u"")
frontend = context.socket(zmq.ROUTER)


signal.signal(signal.SIGINT, signal.SIG_DFL)

# read from permanent memory already existing messages
fsm = BStarState(0, 0, 0)
topics = []
PERMA_STORAGE_FILE = "topics.json"


def store_operation():
    with open(PERMA_STORAGE_FILE, "w+") as f:
        topicObj = {"topics": []}
        for topic in topics:
            topicObj["topics"].append(topic.to_json())

        json.dump(topicObj, f)


def store_in_permanent_memory():
    while True:
        time.sleep(5)
        if fsm.state == STATE_ACTIVE or fsm.state == STATE_PRIMARY:
            print(" [INFO : ] Storing current state in permanent memory")
            store_operation()


perma_storage_thread = threading.Thread(
    target=store_in_permanent_memory, daemon=True)


def read_from_permanent_memory():
    topics.clear()
    try:
        f = open(PERMA_STORAGE_FILE, "r")
        data = json.load(f)
        for topic in data["topics"]:

            new_topic = Topic.from_json(topic)
            topics.append(new_topic)
    except:
        print("No permament file has been created - cant read from memory")


active_threads = []


def handle_PUT(topicName, message, ident):

    # read from global topics variable
    topicObj = next((single_topic for single_topic in topics if
                     single_topic.topicName ==
                     topicName), None)

    if not topicObj:
        new_msg = Message(message)
        newTopicObj = Topic(topicName)
        newTopicObj.put(new_msg)
        topics.append(newTopicObj)
    else:
        new_msg = Message(message, topicObj.subscribers)
        topicObj.put(new_msg)

    frontend.send_multipart([ident, b'', b'ACK [SUCCESS]: PUT is DONE'])
    print(topics[0])


def handle_SUBSCRIBE(topicName, subscriberID, ident):

    topicObj = next((single_topic for single_topic in topics if
                     single_topic.topicName ==
                     topicName), None)
    if not topicObj:
        newTopicObj = Topic(topicName)
        newTopicObj.subscribe(subscriberID)
        topics.append(newTopicObj)
    else:
        topicObj.subscribe(subscriberID)
    frontend.send_multipart([ident, b'', b'ACK [SUCCESS]: SUBSCRIBE is DONE'])
    print(topics[0])


def handle_UNSUBSCRIBE(topicName, subscriberID, ident):

    topicObj = next((single_topic for single_topic in topics if
                     single_topic.topicName ==
                     topicName), None)
    if not topicObj:
        frontend.send_multipart(
            [ident, b'', b'ACK [FAILURE]: CANT UNSUBSCRIBE FROM A TOPIC THAT DOESNT EXIST'])
    else:
        if subscriberID in topicObj.subscribers:
            topicObj.unsubscribe(subscriberID)
            frontend.send_multipart(
                [ident, b'',  b'ACK [SUCCESS] : UNSUBSCRIBE is DONE'])
        else:
            frontend.send_multipart(
                [ident, b'', b'ACK [FAILURE] : CANT UNSUBSCRIBE FROM A TOPIC THAT YOU ARENT SUBSCRIBED'])

    print(topics[0])


def handle_GET(topicName, subscriberID, ident):

    topicObj = next((single_topic for single_topic in topics if
                     single_topic.topicName ==
                     topicName), None)
    if topicObj:
        message = topicObj.get(subscriberID).messageContent
        response = "ACK [SUCCESS]: GET RESPONSE ON TOPIC %s: %s" % (
            topicName, message)
        frontend.send_multipart([ident, b'', bytes(response, 'utf-8')])
    else:
        frontend.send_multipart(
            [ident, b'', b'[FAILED] PERFORMING GET ON NON EXISTING TOPIC - CANCELLING'])

    print(topics[0])


def handle_frontend_requests():
    ident, _, msg = frontend.recv_multipart()
    msg = msg.decode("utf-8")
    print("RECEIVED : ", msg)
    msgParts = msg.split()
    x = None
    if msgParts[0] == "PUT":
        topicName = msgParts[1]
        message = msgParts[2]
        x = threading.Thread(target=handle_PUT, args=[
            topicName, message, ident], daemon=True)

    elif msgParts[0] == "GET":
        # GET FROM %d ON TOPIC : %s" % (port, topic)
        subscriberID = msgParts[2]
        topicName = msgParts[-1]
        x = threading.Thread(target=handle_GET, args=[
            topicName, subscriberID, ident], daemon=True)

    elif msgParts[0] == "SUBSCRIBE":
        subscriberID = msgParts[-1]
        topicName = msgParts[1]
        x = threading.Thread(target=handle_SUBSCRIBE, args=[
            topicName, subscriberID, ident], daemon=True)

    elif msgParts[0] == "UNSUBSCRIBE":
        subscriberID = msgParts[-1]
        topicName = msgParts[1]
        x = threading.Thread(target=handle_UNSUBSCRIBE, args=[
            topicName, subscriberID, ident], daemon=True)

    else:
        print("UNKNOWN SERVER REQUEST: CANCELLING")
        frontend.send_string("ACK : BAD REQUEST")

    if x:
        x.start()
        active_threads.append(x)


HEARTBEAT = 5000

perma_storage_thread.start()
if is_primary:
    print("[INFO] BOOTING UP PRIMARY SERVER [5001]")
    frontend.bind("tcp://*:5001")
    statepub.bind("tcp://*:5003")
    statesub.setsockopt(zmq.IMMEDIATE, 1)
    statesub.connect("tcp://localhost:5004")
    read_from_permanent_memory()
    fsm.state = STATE_PRIMARY

elif is_backup:
    print("[INFO] BOOTING UP BACKUP SERVER [5002]")
    frontend.bind("tcp://*:5002")
    statepub.bind("tcp://*:5004")
    statesub.connect("tcp://localhost:5003")
    statesub.setsockopt(zmq.IMMEDIATE, 1)
    fsm.state = STATE_BACKUP

send_state_at = int(time.time() * 1000 + HEARTBEAT)

poller = zmq.Poller()
poller.register(frontend, zmq.POLLIN)
poller.register(statesub, zmq.POLLIN)

while True:
    time_left = send_state_at - int(time.time() * 1000)
    if time_left < 0:
        time_left = 0
    socks = dict(poller.poll(time_left))

    if socks.get(frontend) == zmq.POLLIN:
        fsm.event = CLIENT_REQUEST
        if fsm.state == STATE_PASSIVE or fsm.state == STATE_BACKUP:
            print("[INFO] reading permament file - BACKUP about to become ACTIVE ")
            read_from_permanent_memory()
            for topic in topics:
                print(topic)

        try:
            run_fsm(fsm)
            handle_frontend_requests()
        except BStarException:
            print("[ERROR] INVALID BSTAR STATE")
    if socks.get(statesub) == zmq.POLLIN:
        msg = statesub.recv_string()
        fsm.event = int(msg)
        print("[INFO] RECEIVING STATE: ", fsm.event)
        del msg
        try:
            run_fsm(fsm)
            fsm.peer_expiry = int(time.time() * 1000) + (2 * HEARTBEAT)
        except BStarException:
            break

    if int(time.time() * 1000) >= send_state_at:
        print("[INFO] sending STATE : %d" % fsm.state)
        statepub.send_string("%d" % fsm.state)
        send_state_at = int(time.time() * 1000) + (2 * HEARTBEAT)
