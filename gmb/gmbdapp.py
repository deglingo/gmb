#

import queue, socket, signal, threading


# Server
#
class Server :


    # __init__:
    #
    def __init__ (self, event_queue) :
        self.event_queue = event_queue
        self.host = ''
        self.port = 5555

        
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
            self.event_queue.put(('connect', addr))
            while True:
                data = conn.recv(1024)
                if not data: break
                conn.sendall(data)
            conn.close() # [FIXME]


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
        print('gmbd: hello')
        self.event_queue = queue.Queue()
        self.main_thread = threading.Thread(target=self.__main_T)
        self.server = Server(event_queue=self.event_queue)
        self.main_thread.start()
        self.server.start()
        signal.pause()


    # __main_T:
    #
    def __main_T (self) :
        while True :
            event = self.event_queue.get()
            print('event: %s' % repr(event))


# exec
if __name__ == '__main__' :
    GmbdApp.main()
