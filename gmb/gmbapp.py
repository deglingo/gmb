#

import socket, time


# GmbApp:
#
class GmbApp :


    # main:
    #
    @classmethod
    def main (cls) :
        app = cls()
        app.run()


    # run:
    #
    def run (self) :
        print('gmb: hello')
        host = 'localhost'
        port = 5555
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        ntries = 0
        while True :
            try:
                s.connect((host, port))
            except ConnectionRefusedError:
                if ntries > 10 :
                    raise
                else :
                    print('connection refused, retry...')
                    time.sleep(0.1)
            break
        s.sendall(b'Hello, world')
        data = s.recv(1024)
        s.close()
        print('Received', repr(data))


# exec
if __name__ == '__main__' :
    GmbApp.main()
