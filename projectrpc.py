# The Byzantine General’s problem with Consensus
# Solution by Magnus Karlson

import sys
import socket
from threading import Thread
import json
import os
import random
import time
import math

if len(sys.argv) < 2 or int(sys.argv[1]) < 1:
    exit("Number of processes must be atleast 1!")

HOST = '127.0.0.1'
PORT = 17000

total = int(sys.argv[1])

primaryprocess = None
processes = []

# finds most frequent result
def most_freq(orders):
    # not enough for conclusion
    if len(orders) < 3:
        return 'undefined', len(orders)
    half = math.floor(len(orders) / 2)
    result = 'undefined'
    votes= {
        'attack': 0,
        'retreat': 0,
        'undefined': 0
    }
    for order in orders:
        votes[order] += 1
        if votes[order] > half:
            result = order
    return result, votes[result]

class Process(Thread):
    def __init__(self, index):
        Thread.__init__(self)
        self.index = index
        self.primary = False
        self.order = 'undefined'
        self.state = 'NF'
        self.all_orders = []
        Thread(target=self.launch_server).start()

    # if process is non-faulty it will return the correct order
    # if process is faulty it will randomly choose between 'attack' and 'retreat'
    def process_order(self, order):
        if self.state == 'NF':
            return order
        return random.choice(['attack', 'retreat'])


    def launch_server(self):
        s = socket.socket()
        s.bind((HOST, PORT + self.index))
        s.listen(200)
        while True:
            con, addr = s.accept()
            params = json.loads(con.recv(1024).decode())
            if params['action'] == 'primary_order':
                # informing others from given order
                self.store_orders(params['order'])
                for p in processes:
                    # skips self and primary
                    if p.index == self.index or p.index == primaryprocess.index: continue
                    self.send_req(p.index,{
                        'action': 'validate_order',
                        'sender': self.index,
                        'state': self.state,
                        'order': self.process_order(params['order'])
                    })
            # process receives from other porcesses, what order they got
            elif params['action'] == 'validate_order':
                self.store_orders(params['order'])
            con.send('ok'.encode())

    # stores orders for decision making
    def store_orders(self, order):
        self.all_orders.append(order)
        # every order has been recieved
        if len(self.all_orders) == len(processes) - 1:
            most_frequent, _ = most_freq(self.all_orders)
            self.order = most_frequent
            self.all_orders = []
    
    # primary sends order to other processes
    def primary_order(self, order):
        self.order = order
        for p in processes:
            if p.index == self.index: continue
            self.send_req(p.index, {
                'action': 'primary_order',
                'state': self.state,
                'order': self.process_order(order)
            })
            

    # for sending requests
    def send_req(self, target, params):
        s = socket.socket()
        s.connect((HOST, PORT + target))
        s.send(json.dumps(params).encode())
        res = s.recv(1024).decode()
        s.close()
        return res

    def strresult(self, majority=False):
        items = [f'G{self.index}', 'primary' if self.primary else 'secondary']
        if majority: items.append(f'majority={self.order}')
        items.append(f'state={self.state}')
        return ', '.join(items)

def add_process(i):
    global primaryprocess
    p = Process(i+1)
    if primaryprocess == None:
        p.primary = True
        primaryprocess = p
    p.start()
    processes.append(p)

for i in range(total):
    add_process(i)

def find_process(id):
    if not id.isdigit():
        print("Such process doesn't exist!")
        return None
    id = int(id)
    for p in processes:
        if p.index == id:
            return p
    print("Such process doesn't exist!")
    return None

def show_processes(majority=False):
    if len(processes) == 0:
        print('(LIST EMPTY)')
    for p in processes:
        print(p.strresult(majority))

while True:
    try:
        msg = input("Enter command (actual-order attack,retreat | g-state | g-state id faulty,non-faulty | g-kill id | g-add n | exit): ")
    except KeyboardInterrupt:
        os._exit(0)

    parts = msg.split(' ')
    cmd = parts[0].lower()
    p1 = parts[1].lower() if len(parts) > 1 else ''
    p2 = parts[2].lower() if len(parts) > 2 else ''

    if cmd == 'actual-order':
        if p1 not in ['attack', 'retreat']:
            print('Invalid order!')
            continue
        primaryprocess.primary_order(p1)
        time.sleep(0.5)
        show_processes(True)

        # wins order, what has over 50% of votes
        result, count = most_freq([p.order for p in processes[1:]])

        # faulty node counter
        faulty = 0
        for p in processes:
            if p.state == 'F':
                faulty += 1

        if result == 'undefined':
            print(f'Execute order - cannot be determined - not enough generals in the system! {faulty} faulty nodes in the system! {count} out of {len(processes)} not consistent')
        else:
            print(f'Execute order: {result}! {faulty} faulty nodes in the system! {count} out of {len(processes)} suggest {result}')
    
    elif cmd == 'g-state':
        if p1 != '':
            p = find_process(p1)
            if p == None: continue
            if p2 in ['faulty', 'f']:
                p.state = 'F'
            elif p2 in ['non-faulty', 'nf']:
                p.state = 'NF'
            else:
                print('Invalid state!')
                continue
        show_processes()

    elif cmd == 'g-add':
        if not p1.isdigit() or int(p1) < 1:
            print('Invalid amount of processes!')
            continue
        for i in range(int(p1)):
            add_process(total + i)
        total += int(p1)
        show_processes()

    elif cmd == 'g-kill':
        p = find_process(p1)
        if p == None: continue
        processes.remove(p)
        
        # selects new primary process
        if primaryprocess == p and len(processes) > 0:
            primaryprocess = processes[0]
            processes[0].primary = True

        show_processes()

    elif cmd == 'exit':
        os._exit(0)

    