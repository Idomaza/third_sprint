import time
from sprites import *
from config import *
import threading
import socket
import queue
import sys
import pickle


class Game:
    def __init__(self):
        pygame.init()
        self.screen = pygame.display.set_mode((WIN_WIDTH, WIN_HEIGHT))
        self.background = pygame.image.load('img/map6.png')

        self.serial = 0

        self.clock = pygame.time.Clock()
        self.running = True

        self.client = ThreadedClient('192.168.173.219', 5000)
        self.client.start()
        self.client.start_listen()

        time.sleep(0.5)

    def new(self):
        try:
            self.playing = True

            self.all_sprites = pygame.sprite.LayeredUpdates()
            self.all_shots = pygame.sprite.LayeredUpdates()
            self.other_shots = pygame.sprite.LayeredUpdates()

            self.player = Player(self, self.client.pos)
        except Exception as error:
            print(error)
            self.client.exit = True
            exit(1)

    # noinspection PyArgumentList
    def events(self):
        # if error
        if type(self.client.massage) == str:
            if self.client.massage == 'exit':
                self.playing = False
                self.running = False
        # game loop event
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.playing = False
                self.running = False
                self.client.exit = True
            if event.type == pygame.MOUSEBUTTONDOWN:
                if pygame.mouse.get_pressed()[0]:
                    Shot(self, [self.player.x, self.player.y], [pygame.mouse.get_pos()[0], pygame.mouse.get_pos()[1]])
                    self.serial += 1

    def update(self):
        # game loop update
        self.all_sprites.update()

    def draw(self):
        self.screen.blit(self.background, (0, 0), (self.player.pos[0] - 320, self.player.pos[1] - 240, WIN_WIDTH, WIN_HEIGHT))
        if type(self.client.massage) == list:
            for pos in self.client.massage:
                self.create_enemy(pos)
            self.other_shots.draw(self.screen)
            hits = self.player.collide()
            if hits:
                self.client.exit = True
                exit(1)
            self.other_shots = pygame.sprite.LayeredUpdates()
        self.all_sprites.draw(self.screen)
        self.clock.tick(FPS)
        pygame.display.update()

    def main(self):
        # game loop
        while self.playing:
            start = time.perf_counter()

            self.events()
            self.update()
            self.draw()

            player_pos = self.player.get_pos()
            player_pos = player_pos[:-1:]
            positions = [player_pos]

            for shot in self.all_shots:
                pos = shot.get_pos()
                positions.append(pos)
            self.client.add_message([positions, (self.client.host, self.client.port)])

            end = time.perf_counter()
            while end - start < 1/60:
                end = time.perf_counter()
        self.running = False

    def create_enemy(self, pos):
        x = 32
        y = 32
        if pos[1] < 0:
            x = 32 + pos[1]
        if pos[2] < 0:
            y = 32 + pos[2]
        if pos[0] == 'p':
            image = pygame.Surface([x, y])
            rect = image.get_rect()
            rect.x = pos[1]
            rect.y = pos[2]
            self.screen.fill(GREEN, rect)
            return image
        else:
            Other_Shot(self, pos[1], pos[2])

    def game_over(self):
        pass

    def intro_screen(self):
        pass


class ThreadedClient(threading.Thread):
    def __init__(self, host, port):
        threading.Thread.__init__(self)
        # set up queues
        self.send_q = queue.Queue()
        # declare instance variables
        self.host = host
        self.port = port
        # connect to socket
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        # get port
        self.add_message(['what is the port?', (self.host, self.port)])
        # massage received
        self.massage = None
        # if player exit
        self.exit = False

    # LISTEN
    def listen(self):
        while True:  # loop forever
            try:
                if self.exit:
                    self.add_message([b'exit', (self.host, self.port)])
                    return
                # stops listening if there's a message to send
                if not self.send_q.empty():
                    self.send_message()
                message = pickle.loads(self.socket.recvfrom(4096)[0])
                if type(message) == str:
                    self.port = int(message)
                else:
                    if message[0] == 'pos':
                        self.pos = message[1]
                    else:
                        message.pop(0)
                        self.massage = message

            except Exception as error:
                print(error)
                self.add_message([b'exit', (self.host, self.port)])
                self.massage = 'exit'
                return

    def start_listen(self):
        t = threading.Thread(target=self.listen)
        t.start()

    # ADD MESSAGE
    def add_message(self, msg):
        # put message into the send queue
        if msg[0] != '':
            self.send_q.put(msg)
            self.send_message()

    # SEND MESSAGE
    def send_message(self):
        # send message
        msg = self.get_send_q()
        # send all hte position to the server
        self.socket.sendto(pickle.dumps(msg), msg[1])
        # restart the listening

    # SAFE QUEUE READING
    # if nothing in q, prints "empty" instead of stalling program
    def get_send_q(self):
        if self.send_q.empty():
            return "empty!"
        else:
            msg = self.send_q.get()
            return msg


if __name__ == '__main__':
    g = Game()
    g.new()
    while g.running:
        g.main()
    pygame.quit()
    sys.exit()
