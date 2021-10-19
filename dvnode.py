import json
import sys
import os.path
from os import path
import time
import socket
from socket import *
import threading
from threading import *
import math

graph = {}
tables = {}
lock = threading.Lock()

class RoutingTable:
    global graph, tables
    def __init__(self, node):
        self.name = node
        self.routing_table = {}
        adj_nodes = []
        for neighbors in graph[node]:
            self.routing_table[neighbors[0]] = neighbors[1]
            adj_nodes.append(neighbors[0])
        self.routing_table[node] = 0
        nonAdjNodes = list(set(graph.keys())-set(adj_nodes)-set([node]))
        for nan in nonAdjNodes:
            self.routing_table.update({nan: float('inf')})
        self.routing_table[node] = 0

    def update_edge(self, node, loss_rate):
        self.routing_table.update({node: loss_rate})

def init_tables():
    global tables
    for node in graph.keys():
        table = RoutingTable(node)
        tables[node] = table.routing_table

def run_node(port):
    global tables
    sock = socket(AF_INET, SOCK_DGRAM)
    sock.bind(("", port))
    ts = time.time()
    init_tables()
    for dest_port in tables[port]:
        if dest_port != port:
            table_thread = threading.Thread(target=recv_table, args=(port, dest_port, tables))
            table_thread.start()
            nodeAddr = ("", dest_port)
            t = json.dumps(tables[port])
            print("[{t}] Message sent from Node {n1} to Node {n2}".format(t=ts, n1=port, n2=dest_port))
            sock.sendto(t.encode(), nodeAddr)

def recv_table(src, dest, tables):
    sock = socket(AF_INET, SOCK_DGRAM)
    sock.bind(("", dest))
    with lock:
        ts = time.time()
        d, addr = sock.recvfrom(1028)
        print("[{t}] Message received at Node {n1} from Node {n2}".format(t=ts, n1=dest, n2=src))
        port = addr[1]
        table = json.loads(d)
        new_table = run_bellmanford(dest)
        print("[{t}] Node {n} Routing Table".format(t=ts, n=dest))
        for n,d in new_table.items():
            print("({v}) -> Node {k}".format(k=n, v=d))

def run_bellmanford(src_node):
    global graph, tables
    node = src_node
    for adjNode in graph[node]:
        src_adj_dist = tables[node][adjNode[0]]
        for dest in tables[adjNode[0]]:
            src_dest_dist = tables[node][dest]
            adj_dest_dist = tables[adjNode[0]][dest]
            if src_adj_dist + adj_dest_dist < src_dest_dist:
                newDist = round(src_adj_dist + adj_dest_dist, 2)
            else:
                newDist = src_dest_dist
            tables[node].update({dest: newDist})
    return tables[node]

def main():
    global graph
    try:
        with open('graph.txt', 'r') as nodes_file:
            file_nodes = nodes_file.read()
            temp_graph = json.loads(file_nodes)
            for k, v in temp_graph.items():
                graph[int(k)] = v
    except:
        open('graph.txt', 'w')
    
    args = sys.argv
    args.pop(0)
    if len(args) < 3:
        print("usage: srnode.py <local-port> <neighbor-port> <loss-rate-1> ... [last]")
    
    local_port = int(args[0])
    if local_port not in graph:
        graph[local_port] = list()

    for i in range(1, len(args)-1, 2):
        neighbor = int(args[i])
        loss_rate = float(args[i+1])
        if neighbor not in graph:
            graph[neighbor] = list()
            graph[local_port].append([neighbor, loss_rate])
        else:
            graph[local_port].append([neighbor, loss_rate])

    #print(graph)
    
    if args[-1] == "last":
        run_node(local_port)
    else:
        with open('graph.txt', 'w') as nodes_file:
            nodes_file.write(json.dumps(graph))

if __name__ == "__main__":
    main()