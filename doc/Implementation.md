2.	What it is
Gnutella is a decentralized peer-to-peer system, consisting of hosts connected to one another over TCP and running software that implements the Gnutella protocol. This network allows the participating hosts to share arbitrary resources through queries, replies, and other control messages used to discover nodes. The Gnutella protocol defines the way in which servants communicate over the network.


3.	How it works
The Gnutella protocol works as follows. A node that wishes to participate in the network must join the Gnutella network by connecting to any existing node. The new node opens a TCP connection to the existing node and performs a handshake. If the desired port is used the new client might attempt to listen on another port (optional feature).
Once a node has connected to the network, it communicates with its neighboring nodes by sending and receiving protocol-specific messages and accepts incoming connections from new nodes that wish to join the network. The file transfer process is done directly to the Node that asked for data in an HTTP protocol.
The communication messages are the following:

Type	Purpose
Ping	Used to actively discover hosts on the network.
Pong	The response to a Ping. Includes information about a node.
Push	A mechanism that allows a node to share data
Query	A request for a resource (e.g., searching for a file)
Query Hit	A response identifying an available resource (e.g., a matching file)
Bye	An optional message used to inform the remote host that you are closing the connection.
