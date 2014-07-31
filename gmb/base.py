# base.py - basic stuff for gmb and gmbd

__all__ = [
    'LOG_LEVEL_DEBUG',
    'LOG_LEVEL_INFO',
    'LOG_LEVEL_WARNING',
    'LOG_LEVEL_ERROR',
    'LOG_LEVEL_CRITICAL',
    'LOG_LEVEL_CMDOUT',
    'LOG_LEVEL_CMDERR',
    'log_setup',
    'log',
    'trace',
    'error',
]

import sys, logging
    

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


# log_setup:
#
def log_setup (domain) :
    global LOG_DOMAIN
    assert LOG_DOMAIN is None
    logging.lastResort = None
    LOG_DOMAIN = domain
    logger = logging.getLogger(domain)
    logger.setLevel(1)
    hdlr = logging.StreamHandler(sys.stderr)
    fmt = logging.Formatter('%(name)s: %(message)s')
    hdlr.setFormatter(fmt)
    logger.addHandler(hdlr)
    return logger


# logging funcs
#
def log (lvl, msg, *args, **kwargs) :
    assert LOG_DOMAIN is not None
    logger = logging.getLogger(LOG_DOMAIN)
    logger.log(lvl, msg, *args, **kwargs)
    
def trace (msg, *args, **kwargs) :
    assert LOG_DOMAIN is not None
    logger = logging.getLogger(LOG_DOMAIN)
    logger.log(logging.DEBUG, msg, *args, **kwargs)

def error (msg, *args, **kwargs) :
    assert LOG_DOMAIN is not None
    logger = logging.getLogger(LOG_DOMAIN)
    logger.log(logging.ERROR, msg, *args, **kwargs)
    
