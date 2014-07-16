#

import sys, queue, socket, signal, threading, pickle, time

from gmb.base import *


# IDCounter:
#
class IDCounter :


    # __init__:
    #
    def __init__ (self) :
        self.counter = 0
        self.lock = threading.Lock()


    # next:
    #
    def next (self) :
        with self.lock :
            self.counter += 1
            c = self.counter
        return c


# Client:
#
class Client :


    # __init__:
    #
    def __init__ (self, clid, sock, addr) :
        self.clid = clid
        self.sock = sock
        self.addr = addr


    # start:
    #
    def start (self, read_T, write_T) :
        self.read_thread = threading.Thread(target=read_T, args=(self,))
        self.write_thread = threading.Thread(target=write_T, args=(self,))
        self.read_thread.start()
        self.write_thread.start()


# Server
#
class Server :


    # __init__:
    #
    def __init__ (self, event_queue) :
        self.event_queue = event_queue
        self.host = ''
        self.port = 5555
        self.clid_counter = IDCounter()

        
    # start:
    #
    def start (self) :
        print('starting server...')
        self.listen_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.listen_sock.bind((self.host, self.port))
        self.listen_sock.listen(1)
        self.listen_thread = threading.Thread(target=self.__listen_T)
        self.listen_thread.start()


    # __listen_T:
    #
    def __listen_T (self) :
        while True :
            conn, addr = self.listen_sock.accept()
            print('Connected by', addr)
            client = Client(self.clid_counter.next(), conn, addr)
            self.event_queue.put(('connect', client.clid))
            client.start(self.__client_read_T, self.__client_write_T)


    # __client_read_T:
    #
    def __client_read_T (self, cli) :
        f = cli.sock.makefile('rb')
        unpickler = pickle.Unpickler(f)
        while True :
            obj = unpickler.load()
            print('OBJ: %s' % repr(obj))


    # __client_write_T:
    #
    def __client_write_T (self, *args) :
        while True :
            time.sleep(1)


# GmbdApp:
#
class GmbdApp :


    # main:
    #
    @classmethod
    def main (cls) :
        app = cls()
        app.run()


    # run:
    #
    def run (self) :
        try:
            self.__setup_logger()
            trace('hello')
            self.event_queue = queue.Queue()
            self.main_thread = threading.Thread(target=self.__main_T)
            self.server = Server(event_queue=self.event_queue)
            self.main_thread.start()
            self.server.start()
            signal.pause()
        finally:
            sys.stdout.flush()
            sys.stderr.flush()


    # __setup_logger:
    #
    def __setup_logger (self) :
        log_setup('gmbd')


    # __main_T:
    #
    def __main_T (self) :
        while True :
            event = self.event_queue.get()
            print('event: %s' % repr(event))


# exec
if __name__ == '__main__' :
    GmbdApp.main()
