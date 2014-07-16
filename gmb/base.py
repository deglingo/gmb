# base.py - basic stuff for gmb and gmbd

__all__ = [
    'log_setup',
    'trace',
]

import sys, logging
    

LOG_DOMAIN = None


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


# logging funcs
#
def trace (msg) :
    assert LOG_DOMAIN is not None
    logger = logging.getLogger(LOG_DOMAIN)
    logger.log(logging.DEBUG, msg)
