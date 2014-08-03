#

import sys, getopt, socket, time, pickle, logging

from gmb.base import *


# USAGE:
#
USAGE = """\
USAGE: gmb [OPTIONS] [COMMAND] [ITEM...]

OPTIONS:
  -V, --cmd-verbose    increase command verbosity
  -Q, --cmd-quiet      decrease command verbosity
  -h, --help           print this message and exit
"""


# LogDomainFilter:
#
class LogDomainFilter :

    def filter (self, rec) :
        if rec.levelno in (LOG_LEVEL_CMDOUT, LOG_LEVEL_CMDERR) :
            rec.dom_prefix = ''
        else :
            rec.dom_prefix = '%s: ' % rec.name
        return True


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
        self.logger = log_setup('gmb')
        hdlr = logging.StreamHandler(sys.stderr)
        fmt = logging.Formatter('%(dom_prefix)s%(message)s')
        hdlr.setFormatter(fmt)
        dom_filt = LogDomainFilter()
        hdlr.addFilter(dom_filt)
        filt = LogLevelFilter()
        hdlr.addFilter(filt)
        self.logger.addHandler(hdlr)
        trace('hello')
        # parse the command line
        trace('args: %s' % repr(sys.argv))
        port = 5555
        cmd_verb_level = 1
        shortopts = 'p:VQh'
        longopts = ['port=', 'cmd-verbose', 'cmd-quiet', 'help']
        opts, args = getopt.gnu_getopt(sys.argv[1:], shortopts, longopts)
        for o, a in opts :
            if o in ('-h', '--help') :
                sys.stderr.write(USAGE)
                sys.exit(0)
            elif o in ('-p', '--port') :
                port = int(a)
            elif o in ('-V', '--cmd-verbose') :
                cmd_verb_level += 1
            elif o in ('-Q', '--cmd-quiet') :
                cmd_verb_level -= 1
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
        msg = ('verb-level', 6, cmd_verb_level)
        pickle.dump(msg, fout)
        fout.flush()
        msg = ('command', 'install', '.*')
        pickle.dump(msg, fout)
        fout.flush()
        fout.close()
        # recv
        unpickler = pickle.Unpickler(fin)
        while True :
            obj = unpickler.load()
            key = obj[0]
            if key == 'log' :
                lvl, msg = obj[1]
                log(lvl, msg)
            else :
                trace("ERROR: unknown message key: %s" % repr(obj))
        assert 0, "bye"

# exec
if __name__ == '__main__' :
    GmbApp.main()
