#

import os, sys, glob, getopt, queue, socket, signal, threading, pickle, time

from gmb.base import *
from gmb.sysconf import SYSCONF


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


# Config:
#
class Config :


    # __init__:
    #
    def __init__ (self) :
        self.pkglistdir = os.path.join(SYSCONF['pkgsysconfdir'], 'packages.d')


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
    def __init__ (self, port, event_queue) :
        self.event_queue = event_queue
        self.host = ''
        self.port = port
        self.clid_counter = IDCounter()

        
    # start:
    #
    def start (self) :
        print('starting server on port %d ...' % self.port)
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
            self.event_queue.put(('message', cli.clid, obj))


    # __client_write_T:
    #
    def __client_write_T (self, *args) :
        while True :
            time.sleep(1)


# Scheduler:
#
class Scheduler :


    # start:
    #
    def start (self) :
        self.thread = threading.Thread(target=self.__run_T)
        self.thread.start()


    # __run_T:
    #
    def __run_T (self) :
        trace("scheduler: run")


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
            # setup the logger
            self.__setup_logger()
            trace('hello')
            # create the config
            self.__init_config()
            # parse command line
            shortopts = 'p:'
            longopts = ['port=']
            opts, args = getopt.gnu_getopt(sys.argv[1:], shortopts, longopts)
            port = 5555
            for o, a in opts :
                if o in ('-p', '--port') :
                    port = int(a)
                else :
                    assert 0, (o, a)
            #
            self.event_queue = queue.Queue()
            self.main_thread = threading.Thread(target=self.__main_T)
            self.server = Server(port=port, event_queue=self.event_queue)
            self.scheduler = Scheduler()
            self.main_thread.start()
            self.server.start()
            self.scheduler.start()
            signal.pause()
        finally:
            sys.stdout.flush()
            sys.stderr.flush()


    # __init_config:
    #
    def __init_config (self) :
        self.config = Config()
        trace("reading packages list from '%s'" % self.config.pkglistdir)


    # __setup_logger:
    #
    def __setup_logger (self) :
        log_setup('gmbd')


    # __main_T:
    #
    def __main_T (self) :
        while True :
            event = self.event_queue.get()
            trace('event: %s' % repr(event))
            key = event[0]
            if key == 'connect' :
                trace('connect: %s' % repr(event[1:]))
            elif key == 'message' :
                trace('message: %s' % repr(event[1:]))
            else :
                trace('FIXME: unhandled event: %s' % repr(event[1:]))


# exec
if __name__ == '__main__' :
    GmbdApp.main()
