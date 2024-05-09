# SDLE First Assignment

SDLE First Assignment of group T03G11.

Group members:

1. Miguel Freitas (up201906159@edu.fe.up.pt)
2. Joana Mesquita (up201907878@edu.fe.up.pt)
3. Carolina Figueira (up201906845@edu.fe.up.pt)
4. Afonso Monteiro (up201907284@edu.fe.up.pt)

# How To Run

The project was implemented using the Python language.
In order to run it you require only the `zmq` package:

`pip install zmq`

All other packages belong to the Python standard library.

All commands presented bellow should be run inside the src folder

## Server

Seeing as we have implemented a Binary Star pattern in order to see it in full display we will need to run a PRIMARY
server as well as a BACKUP one, which should take over for the primary one should it crash or be temporary unavailable.
We can start these servers in any order:

<code>py broker.py PRIMARY</code>
<br>
<code>py broker.py BACKUP </code>

## Client

In order to start our clients we simply give them a port that they will use
to communicate with the test client.

`py client.py <port_number> `

## Test Client

Test Client script is simply a way to call the client's functions, which can be done the following ways

### Put

`py test_client.py <client_port_number> PUT <topic_name> <message> `

## Get

`py test_client.py <client_port_number> GET <topic_name> `

## Subscribe

`py test_client.py <client_port_number> SUBSCRIBE <topic_name> `

## Unsubscribe

`py test_client.py <client_port_number> UNSUBSCRIBE <topic_name> `
