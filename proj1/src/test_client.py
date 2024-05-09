import zmq
import random
import sys
import time
import signal

signal.signal(signal.SIGINT, signal.SIG_DFL)

# test_client.py <PORT> <OPERAND> <other_params>

port, operand, *params = sys.argv[1:]


context = zmq.Context()
socket = context.socket(zmq.PAIR)

# connect to a certain publisher/subscriber
socket.bind("tcp://*:%s" % port)
request_string = "REQUEST: %s" % (operand)
for param in params:
    request_string = request_string + " " + param
socket.send_string(request_string)

msg = socket.recv_string()
print(msg)
if msg == "ACK recv: %s " % request_string:
    print("REQUEST RECEIVED CORRECTLY")
