# SDLE Second Assignment

SDLE Second Assignment of group T03G11.

Group members:

1. Miguel Freitas (up201906159@up.pt)
2. Carolina Figueira (up201906845@up.pt)
3. Joana Mesquita (up201907878@up.pt)
4. Afonso Monteiro (up201907284@up.pt)

# How To Run

The project was implemented using the Python language.
In order to run it you require the `kademlia` and `colorama` packages:

`pip install kademlia`

`pip install colorama`

All other packages belong to the Python standard library.

All commands presented bellow should be run inside the src folder

## Bootstrap

As this project uses a distributed hash table to map the peers, there needs to be a 'first node' in the network for the program to function correctly. Bootstrap is a silent node and is required to be running in the background.
We can start it using the following command:

`py bootstrap_node.py`

## Node

To create a connection to the network it is required to provide an address and a port. Each node must be initialized using the following command:

`py node.py -a <ADDRESS> -p <PORT>`

### Operations

All operations regarding the 'Decentralized Timeline' user interaction with the platform are performed in the running prompt of the node, with the assistance of a menu. Such operations include:
    - Following other users
    - Unfollowing users
    - Writing posts
    - Seeing their timeline
    - Seeing their followers
    - Seeing the users they follow