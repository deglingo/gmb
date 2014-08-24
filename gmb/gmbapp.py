#

import sys, getopt, socket, time, pickle, logging, pprint

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
        opts, args = getopt.getopt(sys.argv[1:], shortopts, longopts)
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
        # the command to send
        # [fixme] handle multiple commands
        if not args :
            error("command required")
            sys.exit(1)
        command = tuple(args)
        # run
        host = 'localhost'
        trace('connecting to %s:%d' % (host, port))
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.connect((host, port))
        trace('connected')
        fout = s.makefile('wb')
        fin = s.makefile('rb')
        # send
        cmdlist = [('verb-level', 6, cmd_verb_level)]
        cmdlist.append(command)
        for cmd in cmdlist :
            pickle.dump(cmd, fout)
        fout.flush()
        fout.close()
        # recv
        ssid = 0
        unpickler = pickle.Unpickler(fin)
        while True :
            obj = unpickler.load()
            key = obj[0]
            if key == 'log' :
                lvl, msg = obj[1]
                log(lvl, msg)
            elif key == 'session-reg' :
                assert ssid == 0
                ssid = obj[1]
            elif key == 'session-term' :
                assert ssid == obj[1], (ssid, obj[1])
                states = obj[2]
                if states[TaskState.ERROR] or states[TaskState.CANCELLED] :
                    status, status_str = 1, 'ERROR'
                else :
                    status, status_str = 0, 'SUCCESS'
                info('session %d terminated: %s (%s)' %
                     (ssid, status_str, self.states_summary(states)))
                break
            else :
                error("unknown message key: %s" % repr(obj))
        sys.exit(status)

    def states_summary (self, states) :
        sl = ((TaskState.SUCCESS, 'success', 'success'),
              (TaskState.ERROR, 'error', 'errors'),
              (TaskState.CANCELLED, 'cancelled', 'cancelled'))
        summary = []
        for st, s, p in sl :
            n = len(states[st])
            if n == 0 : pass
            elif n == 1 : summary.append((n, s))
            else : summary.append((n, p))
        return ', '.join('%d %s' % p for p in summary)

# exec
if __name__ == '__main__' :
    GmbApp.main()
