#

import sys, getopt, socket, time, pickle

from gmb.base import *


# USAGE:
#
USAGE = """\
USAGE: gmb [OPTIONS] [COMMAND] [ITEM...]

OPTIONS:

  -h, --help    print this message and exit
"""


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
        # parse the command line
        trace('args: %s' % repr(sys.argv))
        port = 5555
        shortopts = 'p:h'
        longopts = ['port=', 'help']
        opts, args = getopt.gnu_getopt(sys.argv[1:], shortopts, longopts)
        for o, a in opts :
            if o in ('-h', '--help') :
                sys.stderr.write(USAGE)
                sys.exit(0)
            elif o in ('-p', '--port') :
                port = int(a)
            else :
                assert 0, (o, a)
        # run
        host = 'localhost'
        trace('connecting to %s:%d' % (host, port))
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
        msg = ('command', 'install', '.*')
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
