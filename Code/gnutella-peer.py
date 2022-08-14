# Gnutella peer - Juan Armijos 7897968
import sys
import json
import socket
import socket
import threading
import time
import json
import traceback
import uuid
import select
import signal


#
# Class: Contains a list of 'messages' objects that will timeout eventually
#
class timeoutQueue:

    def __init__ (self):
        self.queue = []

    def addMessage(self, myMessage ):
        self.queue.append(myMessage)
    
    def removeByID( self, obj):
        for i in range(len(self.queue) - 1, -1, -1):
            req = self.queue[i]
            if req.msg["id"] == obj["id"]:
                del self.queue[i]

    def getNextTimeout( self):
        now = time.time()
        out = 30
        for r in self.queue:
            if r.timeout < now+out:
                out = r.timeout - now
        return max (0.0001, out)


    def checkTimeouts(self):    
        for i in range(len(self.queue) - 1, -1, -1):
            req = self.queue[i]
            #print("{} {}" .format(req.timeout, time.time()))
            if req.timeout <= time.time():
                req.handleDidTimeout()
                del self.queue[i]

#
#Class message
#
class message:

    def __init__ (self, msg):
        self.msg = msg
        self.type = self.msg["type"]
        if self.type == "PING":
            #10 seconds is reasonable because it may be th ecase that it is taking
            # long time to decide on a directory
            self.timeout = time.time() + 10
        elif self.type == "QUERY":
            self.timeout = time.time() + 1

    def handleDidTimeout( self ):
        if self.type == "PING":
            print("Timeout: PONG was never recieved.")
        elif self.type == "QUERY":
            print("Timeout: QUERY-HIT was never recieved")


# bind the socket to a public host, and a well-known port
HOST = socket.gethostname()
PORT = int(sys.argv[1])
isFirst = True

#Messages
ping = {"type": "PING", "host": HOST, "port": PORT, "id": None}
pong = {"type": "PONG", "host": HOST, "port": PORT, "id": None}
query ={"type": "QUERY","host": HOST, "port": PORT, "file": None, "id": None}
queryHit = {"type": "QUERY-HIT", "host": HOST, "port": PORT, "hasFile": None, "id": None}
bye = {"type": "BYE", "host": HOST, "port": PORT}

#Lists
messages = timeoutQueue()
myPeers = []
dirPath = ""
myThreads = []
myQueries = []

# UDP socket - File Transfering
udpSocket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
udpSocket.bind( (HOST, PORT) )

# TCP socket - Peer communication
mainSocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
mainSocket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
mainSocket.bind((HOST, PORT))
mainSocket.listen()
mainSocket.setblocking(0)

# Ask for the directory name
def assignDirectory():
    global dirPath
    dirPath = input("Enter your directory:")
    print("Your directory is "+ dirPath + "\n")

# Look for the requested file 
def retireveData (msg):
    print("Looking for {}..." .format(msg["file"]), end="")
    found = True
    try:
        f = open("{}/{}" .format(dirPath, msg["file"]))
        print("Found it! Sending it via UDP")
        content = f.read()
        #send via UDP.
        udpSocket.sendto(content.encode(), (msg["host"], msg["port"]))

    except FileNotFoundError:
        found = False
        print("Not found")
    return found


#
# Join the network and start listening for requests
#
def joinNetwork():
    try:
        while True:
            timeout = messages.getNextTimeout()
            (readable, writable, error) = select.select([mainSocket, ] + myPeers, [], [], timeout)
            for s in readable:
                if s is mainSocket:
                    conn, addr = s.accept()
                    conn.setblocking(0)
                    myPeers.append(conn)

                elif s in myPeers:
                    try:
                        data = s.recv(1024).decode('utf-8')
                        msg = json.loads(data)

                        if msg["type"] == "PING":
                            print("PING received, sending PONG")
                            pong["id"] = msg["id"]
                            s.sendall(json.dumps(pong).encode())
                        
                        elif msg["type"] == "PONG":
                            print("PONG received, connection established successfully with peer on port: {}".format(msg["port"]))
                            messages.removeByID(msg)

                        elif msg["type"] == "QUERY":
                            if msg not in myQueries:
                                print("\nGot a query for {}" .format(msg["file"]))
                                myQueries.append(msg)
                                
                                #Look if I have the file
                                queryHit["hasFile"] = retireveData(msg)
                                if not queryHit["hasFile"]:
                                    for peer in myPeers:
                                        #do not send to the peer that sent it
                                        if s is not peer:
                                            #replicate query to all peers
                                            print("Passing query to another peer.")
                                            peer.sendall(json.dumps(msg).encode())
                                            messages.addMessage( message (msg) )
                                
                                print("\n")
                                queryHit["id"] = msg["id"]
                                s.sendall(json.dumps(queryHit).encode())


                        elif msg["type"] == "QUERY-HIT":
                            messages.removeByID(msg)
                        
                        elif msg["type"] == "BYE":
                            print("A peer has closed the connection")
                            s.close()
                            myPeers.remove(s)

                    except json.decoder.JSONDecodeError:
                        print("Problem with the JSON")

                    except Exception as e:
                        traceback.print_exc()
                        print(e)
                        

            messages.checkTimeouts()
    except KeyboardInterrupt as e:
        terminatePeer()
    except Exception as e:
        print("General Exception")
        traceback.print_exc()
        print(e)
        exit()

#Clean up the peer when program ends. Send BYE messages.
def terminatePeer(signum, frame):
    print("\n\nOk exiting\n")
    for p in myPeers:
        p.sendall(json.dumps(bye).encode())
    exit()

#Set a handler for recieving input from the user
def sendQuery(signum, frame):
    print("\n - Asking for file...")
    file = input("Filename: ")
    query["file"] = file
    query["id"] = str(uuid.uuid1())
    #add to queries so if when I recieve do not process again
    myQueries.append(query)

    for p in myPeers:
        #send
        p.sendall(json.dumps(query).encode())
        messages.addMessage( message( query ))
    
    #start the thread for listening to data in th udp socket
    for t in myThreads:
        if not t.is_alive():
            myThreads.remove(t)
    udpThread = threading.Thread(target=listenData)
    udpThread.start()
    myThreads.append(udpThread)
    
    

# This code will be executed by the thread
def listenData():
    try:
        udpSocket.settimeout(5)
        data11, addr11 = udpSocket.recvfrom(2048)
        print("\nContent of requested file:")
        print("{}\n".format(data11.decode('utf-8')))
    except socket.timeout:
        print("TIMEOUT! It seems that the file does not exist")
    except Exception as e:
        print(e)
                        
                        

if __name__ == '__main__':
    print("\nWorking on {}:{}" .format(HOST, PORT))
    #Assign handler for ctrl-Z (requesting files)
    signal.signal(signal.SIGTSTP, sendQuery)
    signal.signal(signal.SIGINT, terminatePeer)

    #Get arguments and do error checking
    listArgs = sys.argv
    if (len(listArgs)<2):
        print( "Not enough arguments passed, exiting program")
        sys.exit()
    elif len(listArgs) == 3:
        arr = sys.argv[2].split(":")
        arr[1] = int(arr[1])
        peersInfo = arr
        isFirst = False
    #ask for a directory
    assignDirectory()
    
    #when it is not the first peer in the network
    if not isFirst:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try: 
            s.connect((peersInfo[0], peersInfo[1]))
        except ConnectionRefusedError:
            print("The peer you are trying to connect seems to be offline.\nTry again later or a different peer.")
            exit()

        print("Sending PING")
        ping["id"] = str(uuid.uuid3)
        s.sendall(json.dumps(ping).encode())
        messages.addMessage( message(ping) )
        myPeers.append(s)

    #join the Network
    joinNetwork()

