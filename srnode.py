import socket
from socket import *
import sys
import time
from time import sleep
import json
import threading
from threading import *
import queue
import traceback
import signal
import random

lock = threading.Lock()

def try_port(port):
    tempSock = socket(AF_INET, SOCK_DGRAM)
    try:
        tempSock.bind(("", port))
        return True
    except:
        return False
    return result

def concat(args):
    message = ""
    for i in range(0, len(args)):
        if i == len(args)-1:
            message = message + args[i]
            break
        message = message + args[i] + " "
    return message

def is_float(x):
    try:
        a = float(x)
    except (TypeError, ValueError):
        return False
    else:
        return True

def is_int(x):
    try:
        a = float(x)
        b = int(a)
    except (TypeError, ValueError):
        return False
    else:
        return a == b

#for sender
recv_ackNo = 0
seqNo = 0
exp_ackNo = 0
timeout = False
end_seqNo = 0
sender_drops = 0
total_acks = 0

#for receiver
nxt_ackNo = 0
recvr_drops = 0
final_msg = ""
total_pkts = 0

def run_sender(s_port, p_port, w_sz, drop_val):
    
    recvrAddr = ("", p_port)
    window = [None] * w_sz
    send_buf = set()

    prob = False
    if is_float(drop_val) and "." in drop_val:
        prob = True
        p = float(drop_val)
    else:
        d = int(drop_val)

    senderSock = socket(AF_INET, SOCK_DGRAM)
    senderSock.setsockopt(SOL_SOCKET, SO_REUSEADDR, 1)
    senderSock.bind(("", s_port))


    while True:
        sender_input = input("node> ")
        args = sender_input.split()
        if len(args) != 2 or args[0] != "send":
            print("usage: node> send <message>")
            continue
        else:
            msg = concat(args[1:])
            end_seqNo = len(msg)-1
            break

    def handle_timeout(signum, frame):
        global exp_ackNo, recv_ackNo, seqNo, end_seqNo
        ts = time.time()
        try:
            print("[{t}] packet{n} timeout, resending".format(t=ts, n=exp_ackNo))
            packet = json.dumps([list(send_buf)[0], msg[list(send_buf)[0]]])
            senderSock.sendto(packet.encode(), recvrAddr)
            if end_seqNo>recv_ackNo:
                seqNo = recv_ackNo
        except:
            exit()
        
        signal.setitimer(signal.ITIMER_REAL, 0.5)

    signal.signal(signal.SIGALRM, handle_timeout)

    if prob:
        recv_ack_thread = threading.Thread(target=receive_ack_sender, args=(senderSock, send_buf, prob, p))
        recv_ack_thread.start()
    else:
        recv_ack_thread = threading.Thread(target=receive_ack_sender, args=(senderSock, send_buf, prob, d))
        recv_ack_thread.start()

    while recv_ackNo < end_seqNo+1:
        global seqNo, exp_ackNo
        with lock:
            while seqNo - recv_ackNo < w_sz:
                if seqNo == end_seqNo+1:
                    break
                pkt = [seqNo,msg[seqNo]]
                send_buf.add(seqNo)
                packet = json.dumps(pkt)
                ts = time.time()
                print("[{t}] packet{n} {s} sent".format(t=ts, n=seqNo, s=pkt[1]))
                seqNo = seqNo + 1
                senderSock.sendto(packet.encode(), recvrAddr)
                signal.setitimer(signal.ITIMER_REAL, 0.5)
        continue

    senderSock.sendto(msg.encode(), recvrAddr)
    lossrate = float(sender_drops/recv_ackNo)
    print("[Summary] {n1}/{n2} ACKS dropped, lossrate = {n3}".format(n1=sender_drops, n2=recv_ackNo, n3=lossrate))
    recv_ack_thread.join()
    exit()

def receive_ack_sender(senderSock, send_buf, prob, pd):
    global recv_ackNo, exp_ackNo, seqNo, sender_drops, total_acks
    while True:
        d, servAddr = senderSock.recvfrom(2048)
        ts = time.time()
        data = int(d.decode())
        rand = random.random()
        if prob and rand <= pd:
            print("[{t}] ACK{n} dropped".format(t=ts, n=data))
            sender_drops = sender_drops + 1
            total_acks = total_acks + 1
            continue
        # if not prob and (recv_ackNo+1) % pd == 0:
        #     print("[{t}] ACK{n} dropped".format(t=ts, n=data))
        #     sender_drops = sender_drops + 1
        #     continue
        if data == end_seqNo and not send_buf:
            break
        if data == exp_ackNo:
            print("[{t}] ACK{n} received, window starts at {w}".format(t=ts, n=data, w=exp_ackNo+1))
            exp_ackNo = exp_ackNo + 1
            recv_ackNo = recv_ackNo + 1
            total_acks = total_acks + 1
            send_buf.pop()
            signal.setitimer(signal.ITIMER_REAL, 0.5)
        elif data > exp_ackNo:
            print("[{t}] ACK{n} received, window starts at {w}".format(t=ts, n=data, w=exp_ackNo))
            total_acks = total_acks + 1
            send_buf.add(data)

def run_recvr(s_port, p_port, w_sz, drop_val):

    prob = False
    if is_float(drop_val) and "." in drop_val:
        prob = True
        p = float(drop_val)
    else:
        d = int(drop_val)
    
    recvrSock = socket(AF_INET, SOCK_DGRAM)
    recvrSock.setsockopt(SOL_SOCKET, SO_REUSEADDR, 1)
    recvrSock.bind(("", s_port))

    recv_buf = set()
    if prob:
        recv_seg_thread = threading.Thread(target=receive_seg_recvr, args=(recvrSock, recv_buf, prob, p))
        recv_seg_thread.start()
    else:
        recv_seg_thread = threading.Thread(target=receive_seg_recvr, args=(recvrSock, recv_buf, prob, d))
        recv_seg_thread.start()


def receive_seg_recvr(recvrSock, recv_buf, prob, pd):
    global nxt_ackNo, final_msg, total_pkts, recvr_drops
    while True:
        d, senderAddr = recvrSock.recvfrom(2048)
        try:
            ts = time.time()
            rand = random.random()
            loaded_data = json.loads(d)
            segNo, data = loaded_data
            if prob and rand<=pd:
                print("[{t}] packet{n} {d} dropped".format(t=ts, n=segNo, d=data))
                recvr_drops = recvr_drops + 1
                continue
            # if not prob and (total_pkts+1)%pd==0:
            #     print("[{t}] packet{n} {d} dropped".format(t=ts, n=segNo, d=data))
            #     recvr_drops = recvr_drops + 1
            #     continue
            else:
                if segNo < nxt_ackNo:
                    total_pkts = total_pkts + 1
                    print("[{t}] duplicate packet{n} {s} received, discarded".format(t=ts, n=segNo, s=data))
                    print("[{t}] ACK{n} sent, window starts at {w}".format(t=ts, n=segNo, w=nxt_ackNo))
                    ackPacket = str(segNo)
                    recvrSock.sendto(ackPacket.encode(), senderAddr)
                elif segNo == nxt_ackNo:
                    total_pkts = total_pkts + 1
                    print("[{t}] packet{n} {s} received".format(t=ts, n=segNo, s=data))
                    print("[{t}] ACK{n} sent, window starts at {w}".format(t=ts, n=segNo, w=nxt_ackNo+1))
                    final_msg = final_msg + data
                    ackPacket = str(nxt_ackNo)
                    recvrSock.sendto(ackPacket.encode(), senderAddr)
                    nxt_ackNo = nxt_ackNo + 1
                    continue
                elif segNo > nxt_ackNo:
                    total_pkts = total_pkts + 1
                    print("[{t}] packet{n} received {s} out of order, buffered".format(t=ts, n=segNo, s=data))
                    print("[{t}] ACK{n} sent, window starts at {w}".format(t=ts, n=segNo, w=nxt_ackNo+1))
                    recv_buf.add(segNo)
                    ackPacket = str(segNo)
                    if recv_buf:
                        ackPacket = str(recv_buf.pop())
                    recvrSock.sendto(ackPacket.encode(), senderAddr)
        except Exception as e:
            #print(e)
            print("[{t}] Message received: {s}".format(t=ts, s=final_msg))
            break
        
    lossrate = float(recvr_drops/total_pkts)
    print("[Summary] {n1}/{n2} packets dropped, lossrate = {n3}".format(n1=recvr_drops, n2=total_pkts, n3=lossrate))

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
    ports = [None] * 2
    args.pop(0)
    if len(args) != 5 or not is_valid_port(args[0]) or not is_valid_port(args[1]) or args[3] not in ["-d", "-p"]:
        print("usage: srnode.py <self-port> <peer-port> <window-size> [ -d <value-of-n> | -p <value-of-p>]")
    else:
        s_port, p_port, w_sz, drop_val = int(args[0]), int(args[1]), int(args[2]), args[4]
        if try_port(s_port) and try_port(p_port):
            run_sender(s_port, p_port, w_sz, drop_val)
        elif try_port(s_port) and not try_port(p_port):
            run_recvr(s_port, p_port, w_sz, drop_val)   


if __name__ == "__main__":
    main()