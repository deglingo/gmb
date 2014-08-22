# base.py - basic stuff for gmb and gmbd

__all__ = [
    'LOG_LEVEL_DEBUG',
    'LOG_LEVEL_INFO',
    'LOG_LEVEL_WARNING',
    'LOG_LEVEL_ERROR',
    'LOG_LEVEL_CRITICAL',
    'LOG_LEVEL_CMDOUT',
    'LOG_LEVEL_CMDERR',
    'LogLevelFilter',
    'TaskState',
    'print_exception',
    'format_exception',
    'log_setup',
    'log',
    'trace',
    'info',
    'error',
]

import os, sys, logging, traceback
    

LOG_DOMAIN = None


# Log levels
#
LOG_LEVEL_DEBUG    = logging.DEBUG
LOG_LEVEL_INFO     = logging.INFO
LOG_LEVEL_WARNING  = logging.WARNING
LOG_LEVEL_ERROR    = logging.ERROR
LOG_LEVEL_CRITICAL = logging.CRITICAL

LOG_LEVEL_CMDOUT   = LOG_LEVEL_INFO + 1
LOG_LEVEL_CMDERR   = LOG_LEVEL_INFO + 2

LOG_LEVEL_ALL = set((LOG_LEVEL_DEBUG,
                     LOG_LEVEL_INFO,
                     LOG_LEVEL_WARNING,
                     LOG_LEVEL_ERROR,
                     LOG_LEVEL_CRITICAL,
                     LOG_LEVEL_CMDOUT,
                     LOG_LEVEL_CMDERR))

# just in case, make sure all levels are unique
assert len(LOG_LEVEL_ALL) == 7


# LogLevelFilter:
#
class LogLevelFilter :


    # __init__:
    #
    def __init__ (self, lvl=4, cmdlvl=1) :
        self.set_level(lvl, cmdlvl)


    # set_level:
    #
    def set_level (self, lvl, cmdlvl) :
        self.levels = l = set()
        if lvl > 0 : l.add(LOG_LEVEL_CRITICAL)
        if lvl > 1 : l.add(LOG_LEVEL_ERROR)
        if lvl > 2 : l.add(LOG_LEVEL_WARNING)
        if lvl > 3 : l.add(LOG_LEVEL_INFO)
        if lvl > 4 : l.add(LOG_LEVEL_DEBUG)
        if cmdlvl > 0 : l.add(LOG_LEVEL_CMDERR)
        if cmdlvl > 1 : l.add(LOG_LEVEL_CMDOUT)


    # filter:
    #
    def filter (self, rec) :
        return rec.levelno in self.levels


# TaskState:
#
class TaskState :

    WAITING = 0
    RUNNING = 1
    SUCCESS = 2
    ERROR = 3
    CANCELLED = 4


# print_exception:
#
def print_exception (exc_info=None, f=None) :
    if f is None : f = sys.stderr
    fmt = format_exception(exc_info)
    f.writelines(fmt)
    f.flush()


# format_exception:
#
def format_exception (exc_info=None) :
    if exc_info is None :
        exc_info = sys.exc_info()
    tp, exc, tb = exc_info
    xtb = traceback.extract_tb(tb)
    # format tb
    rows = []
    wcols = (0, 0)
    for fn, ln, fc, co in reversed(xtb) :
        fn = os.path.realpath(fn)
        c0 = '%s:%d:%s%s' % (fn, ln, fc, ('' if fc[0] == '<' else '()'))
        c1 = co
        rows.append((c0, c1))
        wcols = (max(wcols[0], len(c0)), max(wcols[1], len(c1)))
    # title
    title = '%s: %s' % (tp.__name__, exc)
    #
    width = max(len(title), sum(wcols) + 4)
    sep1 = ('=' * width) + '\n'
    sep2 = ('-' * width) + '\n'
    out = [sep1, title+'\n', sep2]
    rowfmt = '%%-%ds -- %%s\n' % (wcols[0])
    for r in rows :
        out.append(rowfmt % r)
    out.append(sep1)
    return out


# log_setup:
#
def log_setup (domain) :
    global LOG_DOMAIN
    assert LOG_DOMAIN is None
    logging.lastResort = None
    LOG_DOMAIN = domain
    logger = logging.getLogger(domain)
    logger.setLevel(1)
    return logger


# logging funcs
#
def log (lvl, msg, *args, **kwargs) :
    assert LOG_DOMAIN is not None
    logger = logging.getLogger(LOG_DOMAIN)
    logger.log(lvl, msg, *args, **kwargs)

def info (m, *a, **k) :
    log(LOG_LEVEL_INFO, m, *a, **k)
    
def trace (msg, *args, **kwargs) :
    assert LOG_DOMAIN is not None
    logger = logging.getLogger(LOG_DOMAIN)
    logger.log(logging.DEBUG, msg, *args, **kwargs)

def error (msg, *args, **kwargs) :
    assert LOG_DOMAIN is not None
    logger = logging.getLogger(LOG_DOMAIN)
    logger.log(logging.ERROR, msg, *args, **kwargs)
    
