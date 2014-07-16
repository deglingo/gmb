#

import socket, time, pickle

from gmb.base import *


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
        log_setup('gmb')
        trace('hello')
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
        print('connected!')
        fout = s.makefile('wb')
        fin = s.makefile('rb')
        # send
        msg = ('command', 'arg1', 'arg2')
        pickle.dump(msg, fout)
        fout.flush()
        fout.close()
        # recv
        while True :
            obj = pickle.load(fin)
            print('MSG: %s' % repr(obj))
        assert 0, "bye"

# exec
if __name__ == '__main__' :
    GmbApp.main()
