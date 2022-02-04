import socket
import threading
import queue
import pickle
import time
import random
from config import *

outgoingQ = queue.Queue()


class ThreadedServer(threading.Thread):
    def __init__(self, host, port, q):
        super(ThreadedServer, self).__init__()
        self.plist = []
        self.pos_list = []
        self.host = host
        self.port = port
        self.q = q
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

        self.sock.bind((self.host, self.port))

        p = sendToClient(self.q)
        p.start()

    def run(self):
        while True:
            data = self.sock.recvfrom(1024)
            address = data[1]

            client = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

            while True:
                try:
                    port = random.randint(10000, 65535)
                    client.bind((self.host, port))
                    break
                except Exception as error:
                    print(error)

            self.q.put([str(port), address, self.sock])

            success = False
            while not success:
                success = self.give_pos()

            p = listenToClient(client, address, self.plist, self.pos_list, self.q)
            self.plist.append(p)
            p.start()

    def give_pos(self):
        # position = [random.randint(0, WIN_WIDTH * 8), random.randint(0, WIN_HEIGHT * 8)]
        # for pos in self.pos_list:
        #     if position == pos:
        #         return False
        if len(self.plist) == 0:
            position = [640, 480]
        else:
            position = [1000, 801]
        self.pos_list.append(position)
        return True


class listenToClient(threading.Thread):
    def __init__(self, client, address, plist, pos_list, q):
        super(listenToClient, self).__init__()
        self.massage = None
        self.client = client
        self.address = address
        self.plist = plist
        self.pos_list = pos_list
        self.pos = self.pos_list[-1]
        self.size = 1024
        self.q = q

        self.calc_thread = get_pos(self.pos, self.pos_list, self.plist, self, self.client, self.address, self.q)

    def run(self):
        print('running ', self.address)
        # thread that calculate the positions
        self.q.put([['pos', self.pos], self.address, self.client])
        self.calc_thread.start()
        while True:
            try:
                data = self.client.recvfrom(self.size)
                data = pickle.loads(data[0])
                massage = data[0]
                if massage == b'exit':
                    var = massage - 1
                for msg in massage:
                    self.calc_thread.massage.put(msg)
            except Exception as error:
                if str(error) == "unsupported operand type(s) for -: 'bytes' and 'int'":
                    print('client disconnected')
                else:
                    print('There was an error: ' + str(error))
                for i in range(len(self.plist)):
                    if self == self.plist[i]:
                        self.plist[i] = ''
                        self.pos_list[i] = ['', '']
                self.client.close()
                return


class get_pos(threading.Thread):
    def __init__(self, pos, pos_list, plist, player, client, address, q):
        super(get_pos, self).__init__()
        self.pos = pos
        self.pos_list = pos_list
        self.plist = plist
        self.player = player
        self.shot_dict = {}
        self.client = client
        self.address = address
        self.q = q
        self.massage = queue.Queue()

    def run(self):
        while True:
            self.change_location()
            self.calc_other_players()

    def change_location(self):
        while not self.massage.empty():
            move = self.massage.get()
            if type(move) == str:
                movement = move.split(' ')

                for move in movement:
                    if move == 'l':
                        self.pos[0] -= PLAYER_SPEED
                    if move == 'r':
                        self.pos[0] += PLAYER_SPEED
                    if move == 'u':
                        self.pos[1] -= PLAYER_SPEED
                    if move == 'd':
                        self.pos[1] += PLAYER_SPEED
            else:
                if move[1] != -1 and move[2] != -1:
                    dx = abs(320 - move[1])
                    dy = abs(240 - move[2])
                    if 320 > move[1]:
                        x = self.pos[0] - dx
                    else:
                        x = self.pos[0] + dx
                    if 240 > move[2]:
                        y = self.pos[1] - dy
                    else:
                        y = self.pos[1] + dy
                    self.shot_dict[move[0]] = [x, y]
                else:
                    if self.shot_dict.get(move[0]):
                        self.shot_dict.pop(move[0])

    def calc_other_players(self):
        personal_pos = ['positions']
        for pos in self.pos_list:
            if pos != ['', '']:
                if pos != self.pos:
                    dx = abs(self.pos[0] - pos[0])
                    dy = abs(self.pos[1] - pos[1])
                    if self.pos[0] > pos[0]:
                        x = 320 - dx
                    else:
                        x = 320 + dx
                    if self.pos[1] > pos[1]:
                        y = 240 - dy
                    else:
                        y = 240 + dy
                    if -32 < y < 480 and -32 < x < 640:
                        personal_pos.append(['p', x, y])
        for player in self.plist:
            if player != self.player and player != '':
                for shot in player.calc_thread.shot_dict:
                    pos = player.calc_thread.shot_dict[shot]
                    dx = abs(self.pos[0] - pos[0])
                    dy = abs(self.pos[1] - pos[1])
                    if self.pos[0] > pos[0]:
                        x = 320 - dx
                    else:
                        x = 320 + dx
                    if self.pos[1] > pos[1]:
                        y = 240 - dy
                    else:
                        y = 240 + dy
                    if -32 < y < 480 and -32 < x < 640:
                        personal_pos.append(['s', x, y])
        self.q.put([personal_pos, self.address, self.client])
        time.sleep(0.01)


class sendToClient(threading.Thread):
    def __init__(self, q):
        super(sendToClient, self).__init__()
        self.size = 1024
        self.q = q

    def run(self):
        print('start send process')
        while True:
            try:
                if not self.q.empty():
                    message = self.q.get()
                    client = message[2]
                    client.sendto(pickle.dumps(message[0]), message[1])
            except Exception:
                pass


if __name__ == "__main__":
    Ts = ThreadedServer('0.0.0.0', 5000, outgoingQ)
    Ts.start()
    Ts.join()
