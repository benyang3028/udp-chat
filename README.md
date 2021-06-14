# UdpChat (Ben Yang, yy3028)

UdpChat is a Python chat application that allows users to send and receive messages via UDP protocol

## Usage

(Testing done using localhost)

```bash
python3 UdpChat.py -s <server-port>
python3 UdpChat.py -c <username> <server-ip> <server-port> <client-port>
```

## Functions

-registered user gets put into a dictionary of clients with the username as key
-send messages to user by specifying their username and message
-save messages to users who are offline and will be displayed when the user regs back in with proper timestamps
-dereg to go offline and server will update your status for other active users
-reg to go back online and server will update your status for other active users

```bash
send <recvr-username> <message>
save-message <recvr-username> <message>
dereg <username>
reg <username>
```

## Implementation
-Used the Python json library to send over dictionaries that keeps track of user information, including username, ip, portnum, and status.
-Used the socket library for UDP protocol for bind, sendto, recvfrom
-Used the threading library to create multiple threads for the clients to interact
In order to send messages across the server, I used json.dumps() and json.loads() in order to maintain relevant information about the sender and receiver. It was also used to send over the tables that kept track of the client's information. I also used threading to fix the issue of having to press enterand wait for the input, rather than the server's response being printed immediately.

## Bugs
After a user receives a message sent from the server, there is a newline. User needs to press enter to be prompted for the input ">>> ".

##Test Cases
###Test Case 1

Server:
python3 UdpChat.py -s 5005

Client 1:
python3 UdpChat.py -c jean 160.39.192.153 5005 4030
>>> [Welcome, You are registered.]
>>> [Client table updated.]
>>> [Client table updated.]
>>> [Client table updated.]
>>> send jae hello world
>>> [Message received by jae]

>>> jae: goodbye world

>>> send john suns in 4
>>> [Message received by john]
john: cool

>>> dereg jean
>>> [You are Offline. Bye.]

>>> reg jean
>>> [You have messages.]
john: 2021-06-08 13:42:51.784745 you are offline
jae: 2021-06-08 13:43:13.287005 whered you go
>>> [Client table updated.]

Client 2:
python3 UdpChat.py -c john 160.39.192.153 5005 4055
>>> [Welcome, You are registered.]
>>> [Client table updated.]
>>> [Client table updated.]
jean: suns in 4
>>> send jean cool
>>> [Message received by jean]
>>> [Client table updated.]
>>> save-message jean you are offline
>>> [Messages received by the server and saved]
>>> [Client table updated.]

Client 3:
python3 UdpChat.py -c jae 160.39.192.153 5005 4000
>>> [Welcome, You are registered.]
>>> [Client table updated.]
jean: hello world
>>> send jean goodbye world
>>> [Message received by jean]
>>> [Client table updated.]
>>> save-message jean whered you go
>>> [Messages received by the server and saved]
>>> [Client table updated.]

###Test Case 2
Server:
python3 UdpChat.py -s 5003

Client 1:
python3 UdpChat.py -c john 160.39.192.153 5003 4055
>>> [Welcome, You are registered.]
>>> [Client table updated.]
>>> [Client table updated.]
>>> [Client table updated.]
ben: whats good
jae: ni hao

>>> send ben im good
>>> [Message received by ben]

>>> send jae ni hao back
>>> [Message received by jae]

>>> dereg john
>>> [You are Offline. Bye.]

>>> reg john
>>> [You have messages.]
jae: 2021-06-08 14:08:48.126166 hihihihi
ben: 2021-06-08 14:09:16.116619 did you dereg
>>> [Client table updated.]

Client 2:
python3 UdpChat.py -c jae 160.39.192.153 5003 4000
>>> [Welcome, You are registered.]
>>> [Client table updated.]
>>> [Client table updated.]
ben: hello world

>>> send ben whats up  
>>> [Message received by ben]

>>> send john ni hao
>>> [Message received by john]
john: ni hao back
>>> [Client table updated.]

>>> send john hihihihi
>>> [No ACK from john, message sent to server.]

>>> [Client table updated.] 

Client 3:
python3 UdpChat.py -c ben 160.39.192.153 5003 4030
>>> [Welcome, You are registered.]
>>> [Client table updated.]

>>> send jae hello world
>>> [Message received by jae]
jae: whats up

>>> send john whats good
>>> [Message received by john]
john: im good
>>> [Client table updated.]

>>> send john did you dereg
>>> [No ACK from john, message sent to server.]

>>> [Client table updated.]

