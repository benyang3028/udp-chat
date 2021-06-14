import socket
from socket import *
import sys
import time
from time import sleep
import datetime
import json
import threading
from threading import *
import queue

terminated = False
stop_event = Event()

def reg(name, servIP, servPort, clientPort, clients):
    clientSock = socket(AF_INET, SOCK_DGRAM)
    if not clientSock:
        print("socket failed")
    if name in clients:
        print("username already exists")
        exit()
    res = clientSock.sendto(name.encode(), (servIP, int(servPort)))
    return clientSock

def run_server(port):
    clients = {}
    offline_msg = {}
    servSock = socket(AF_INET, SOCK_DGRAM)
    servIP = gethostbyname(gethostname())
    #servIP = "35.245.120.90"
    try:
        servSock.bind((servIP, int(port)))
        print("UDP server started and listening on port {a} : {b}".format(a=port,b=servIP))
    except:
        print("bind failed")
        exit()
    segments = queue.Queue()
    t = threading.Thread(target=receive_data_server, args=(servSock, segments))
    t.start()
    while True:
        while not segments.empty():
            d, clientAddr, ts = segments.get()
            #sends message to receiver specified [sender, recvr-name, message]
            try:
                data = json.loads(d)
                #server receives data to send to receiving client
                if isinstance(data, list) and data[0] in ["send", "save-message"] and data[1] in clients:
                    request = data[0]
                    sender = data[1]
                    receiver = data[2]
                    msg = data[3]
                    recvrAddr = clients[receiver][0]
                    #if receiver is online
                    if request == "send" and clients[receiver][1] == 1:
                        out = json.dumps([clientAddr, sender, receiver, msg])
                        servSock.sendto(out.encode(), recvrAddr)
                    #if client is offline, save offline messages
                    if request in ["send", "save-message"] and clients[receiver][1] == 0:
                        if request == "send":
                            servSock.sendto("[No ACK from {}, message sent to server.]".format(receiver).encode(), clientAddr)
                        else:                      
                            servSock.sendto("[Messages received by the server and saved]".encode(), clientAddr)
                        if receiver not in offline_msg:
                            offline_msg[receiver] = []
                            offline_msg[receiver].append("{n}: {t} {m}".format(n=sender, t=ts, m=msg))
                        else:
                            offline_msg[receiver].append("{n}: {t} {m}".format(n=sender, t=ts, m=msg))

                #update status after client reg/dereg
                if isinstance(data, list) and data[0] == 'ack':
                    senderAddr = tuple(data[1])
                    receiver = data[2]
                    servSock.sendto("[Message received by {}]".format(receiver).encode(), senderAddr)

                if isinstance(data, list) and data[0] in ["dereg", "reg"] and data[1] in clients:
                    request, name = data[0], data[1]
                    if request == "dereg":
                        clients[name][1] = 0
                        servSock.sendto("[You are Offline. Bye.]".encode(), clientAddr)
                    if request == "reg":
                        clients[name][1] = 1
                        if name in offline_msg and offline_msg[name]:
                            messages = json.dumps(offline_msg[name])
                            print(messages)
                            res1 = servSock.sendto("[You have messages.]".encode(), clientAddr)
                            res2 = servSock.sendto(messages.encode(), clientAddr)
                            offline_msg[name] = []
                    clients_table = json.dumps(clients)
                    for name, vals in clients.items():
                        if vals[1] == 1:
                            res = servSock.sendto(clients_table.encode(), tuple(vals[0])) 
            except:
                pass
            data = d.decode()
            # if data is a nick-name (just registered)
            if data not in clients and len(data.split()) == 1 and data != "ack":
                s = "[Welcome, You are registered.]"
                res = servSock.sendto(s.encode(), clientAddr)
                clients[data] = [clientAddr, 1]
                clients_table = json.dumps(clients)
                #send updated dictionary to other online clients
                print(clients_table)
                for name in clients:
                        res = servSock.sendto(clients_table.encode(), clients[name][0])
    servSock.close()

def run_client(name, servIP, servPort, clientPort):
    clients = {}  # {nick-name:[(ip, port number), online-status]}
    if name not in clients:
        clientSock = reg(name, servIP, servPort, clientPort, clients)
    else:
        print("username already exists")
    servAddr = (servIP, int(servPort))
    segments = queue.Queue()
    client_thread = threading.Thread(target=receive_data_client, args=(clientSock,segments,clients))
    timeout_thread = threading.Thread(target=run_time)
    timeout_thread.setDaemon(True)
    client_thread.start()
    timeout_thread.start()
    tries = 0
    #c = input(">>> ")

    while True:
        if tries == 5:
            print(">>> [Server not responding]")
            print(">>> [Exiting]")
            exit()
        while not segments.empty():
            clients = json.loads(segments.get())
        c = input(">>> ")
        if c == "" or len(c.split())<2:
            continue
        args = c.split()
        #send/save-message request to server
        if len(args) >= 3 and args[0] in ["send", "save-message"] and args[1] in clients:
            receiver = args[1]
            message = concat(args[2:])
            if args[0] == "send":
                    msg = json.dumps(["send", name, receiver, message])
                    timeout_thread.join(0.5)
                    res = clientSock.sendto(msg.encode(), servAddr)
                    if res and timeout_thread.is_alive():
                        print("[No ACK from {}, message sent to server.]".format(receiver))
            else:
                if clients[receiver][1] == 0:
                    msg = json.dumps(["save-message", name, receiver, message])
                    res = clientSock.sendto(msg.encode(), servAddr)
                else:
                    print(">>> [Client {} exists!]".format(receiver))
        #dereg/reg request to send to server
        if len(args) == 2 and args[0] in ["dereg", "reg"]:
            cmd, name = args
            request = [cmd, name]
            req = json.dumps(request)
            res = clientSock.sendto(req.encode(), servAddr)
            if terminated:
                tries = tries + 1

#method to runtime for multithreading
def run_time():
    time.sleep(1)
    stop_event.set()

#method to receive data from server socket for multithreading
def receive_data_client(clientSock, segments, clients):
    while True:
        d, servAddr = clientSock.recvfrom(2048)
        try:
            data = json.loads(d)
            #update client table when received from server
            if isinstance(data, dict):
                segments.put(d)
                print(">>> [Client table updated.]")
            #if message is received from another user
            if isinstance(data, list) and isinstance(data[0], list):
                
                ack = json.dumps(["ack", data[0], data[2]])
                clientSock.sendto(ack.encode(), servAddr)
                print("{s}: {m}".format(s=data[1], m=data[3]))
            #print offline messages
            if isinstance(data, list) and not isinstance(data[0], list):
                for msg in data:
                    print(msg)
        except:
            print("{}".format(d.decode()))

#method receive data from the client socket for multithreading
def receive_data_server(servSock, segments):
    while True:
        data, clientAddr = servSock.recvfrom(2048)
        ts = datetime.datetime.now()
        segments.put((data, clientAddr, ts))

#method to concatenate messages
def concat(args):
    message = ""
    for i in range(0, len(args)):
        if i == len(args)-1:
            message = message + args[i]
            break
        message = message + args[i] + " "
    return message

#checks if port is valid
def is_valid_port(p):
    return str(int(p)) == p and (1024 <= int(p) <= 65535)

#checks if ip is valid
def is_valid_ip(ip):
    if ip.count(".") != 3:
        return False
    nums = ip.split(".")
    for n in nums:
        if str(int(n)) != n or not (0 <= int(n) <= 255):
            return False
    return True

def main():
    args = sys.argv
    args.pop(0)
    if len(args) not in [2, 5]:
        print("usage: UdpChat -s <portnum> or UdpChat -c <nick-name> <server-ip> <server-port><client-port>")
    if len(args) == 2 and args[0] == "-s" and is_valid_port(args[1]):
        run_server(args[1])
    if len(args) == 5 and args[0] == "-c" and is_valid_ip(args[2]) and is_valid_port(args[3]) and is_valid_port(args[4]):
        run_client(args[1], args[2], args[3], args[4])


if __name__ == "__main__":
    main()
