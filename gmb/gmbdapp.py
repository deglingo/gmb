#

import socket, signal, threading


# Server
#
class Server :


    # __init__:
    #
    def __init__ (self) :
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
            # while True:
            #     data = conn.recv(1024)
            #     if not data: break
            #     conn.sendall(data)
            # conn.close() # [FIXME]


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
        self.server = Server()
        self.server.start()
        signal.pause()


# exec
if __name__ == '__main__' :
    GmbdApp.main()
