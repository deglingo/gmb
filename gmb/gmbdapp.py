#

import os, sys, glob, getopt, queue, socket, signal, threading, pickle, time, subprocess, json, stat, logging, logging.handlers, weakref, functools

from gmb.base import *
from gmb.sysconf import SYSCONF


# gmbrepr:
#
def gmbrepr (obj, descr) :
    return '<%s %s>' % (obj.__class__.__name__, descr)


# PipeThread:
#
class PipeThread :

    def __init__ (self, name, fin, log_level, log_extra=None) :
        self.name = name
        self.fin = fin
        self.log_level = log_level
        self.log_extra = log_extra
        self.thread = threading.Thread(target=self.__run_T)
        self.thread.start()

    def join (self) :
        self.thread.join()

    def __run_T (self) :
        for line in self.fin :
            line = line.rstrip('\n')
            log(self.log_level, line, extra=self.log_extra)
        trace("%s: EOF" % self.name)


# gmbexec:
#
def gmbexec (cmd, log_extra=None, **kwargs) :
    cwd = kwargs.pop('cwd', None)
    if cwd is None :
        cwd = os.getcwd()
    prompt = '%s>' % cwd # [todo] user@hostname
    # [fixme] quote cmd
    info("%s %s" % (prompt, ' '.join(cmd)), extra=log_extra)
    proc = subprocess.Popen(cmd, cwd=cwd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True, **kwargs)
    p_out = PipeThread('p-out', proc.stdout, log_level=LOG_LEVEL_CMDOUT, log_extra=log_extra)
    p_err = PipeThread('p-err', proc.stderr, log_level=LOG_LEVEL_CMDERR, log_extra=log_extra)
    p_out.join()
    p_err.join()
    r = proc.wait()
    assert r == 0, r


# IDCounter:
#
class IDCounter :


    # __init__:
    #
    def __init__ (self) :
        self.counter = 0
        self.lock = threading.Lock()


    # next:
    #
    def next (self) :
        with self.lock :
            self.counter += 1
            c = self.counter
        return c


# ClientLogHandler:
#
class ClientLogHandler (logging.Handler) :


    # __init__:
    #
    def __init__ (self, clid, send_func) :
        logging.Handler.__init__(self, 1)
        self.clid = clid
        self.send_func = send_func


    # emit:
    #
    def emit (self, rec) :
        # print("[%d/%d] >> %s" % (rec.ssid, self.clid, rec.message))
        self.send_func(self.clid, rec)


# ClientLogFilter:
#
class ClientLogFilter :

    def __init__ (self, clid, ssid) :
        self.clid = clid
        self.ssid = ssid

    def filter (self, rec) :
        return getattr(rec, 'ssid', 0) == self.ssid


# Config:
#
class Config :


    # __init__:
    #
    def __init__ (self) :
        self.gmbdlogdir = os.path.join(SYSCONF['pkglogdir'], 'gmbd')
        self.pkglistdir = os.path.join(SYSCONF['pkgsysconfdir'], 'packages.d')
        self.packages = {}
        self.builds = {} # map <(target, pkg), build>
        # [fixme]
        self.dbdir = '/tmp/gmbdb'
        try: os.mkdir(self.dbdir)
        except FileExistsError: pass
        # [fixme]
        t = CfgTarget(name='home', prefix=os.path.join(os.environ['HOME'], 'local'))
        self.targets = {'home': t}

    # list_packages:
    #
    def list_packages (self) :
        return list(self.packages.values())


    # get_build:
    #
    def get_build (self, target, package) :
        key = (target.name, package.name)
        build = self.builds.get(key)
        if build is None :
            build = self.builds[key] = CfgBuild(self, target, package)
        return build


    # read_packages:
    #
    def read_packages (self) :
        trace("reading packages in '%s'" % self.pkglistdir)
        pkglist = glob.glob(os.path.join(self.pkglistdir, '*.pkg'))
        for fname in pkglist :
            pkgname = os.path.splitext(os.path.basename(fname))[0]
            trace(" - '%s'" % pkgname)
            assert pkgname not in self.packages, pkgname
            pkg = CfgPackage(pkgname)
            self.packages[pkgname] = pkg
        trace("found %d packages" % len(self.packages))


# CfgTarget:
#
class CfgTarget :


    # __init__:
    #
    def __init__ (self, name, prefix) :
        self.name = name
        self.prefix = prefix


# CfgPackage:
#
class CfgPackage :


    # __init__:
    #
    def __init__ (self, name) :
        self.name = name


# DBFile:
#
class DBFile :


    # __init__:
    #
    def __init__ (self, fname) :
        self.fname = fname
        try:
            with open(self.fname, 'r') as f :
                self.data = json.load(f)
        except FileNotFoundError:
            self.data = {}


    # close:
    #
    def close (self) :
        pass


    # select:
    #
    def select (self, key, defo) :
        rec = self.data.get(key)
        if rec is None :
            return defo, 0
        else :
            return rec


    # insert:
    #
    def insert (self, key, value, stamp) :
        if stamp is None :
            stamp = time.time()
        self.data[key] = (value, stamp)
        # write
        tmpfile = self.fname + '.tmp'
        with open(tmpfile, 'w') as f :
            json.dump(self.data, f)
        os.rename(tmpfile, self.fname)


# CfgItem:
#
class CfgItem :


    # __init__:
    #
    def __init__ (self, config, name) :
        self.config = config # [FIXME] ref cycle
        self.name = name
        dbname = '%s@%s.db' % (self.__class__.__name__.lower(), name)
        self.dbfile = os.path.join(self.config.dbdir, dbname)


    # get_state:
    #
    def get_state (self, key, defo='unset') :
        db = DBFile(self.dbfile)
        state, stamp = db.select(key, defo=defo)
        db.close()
        return state, stamp


    # set_state:
    #
    def set_state (self, key, state, stamp=None) :
        db = DBFile(self.dbfile)
        db.insert(key, state, stamp)
        db.close()


# CfgSource:
#
class CfgSource (CfgItem) :


    # __init__:
    #
    def __init__ (self, config, package) :
        CfgItem.__init__(self, config, package.name)
        self.package = package
        # [fixme]
        self.srcdir = os.path.join('/src', package.name)
        # [fixme]
        self.bhv_bootstrap_cls = BhvBootstrapGNU


# CfgBuild:
#
class CfgBuild (CfgItem) :


    # __init__:
    #
    def __init__ (self, config, target, package) :
        CfgItem.__init__(self, config, package.name)
        self.target = target
        self.package = package
        # [fixme]
        self.source = CfgSource(config, package)
        # [fixme]
        self.builddir = os.path.join('/build', package.name)
        # [fixme]
        self.bhv_configure_cls = BhvConfigureGNU
        self.bhv_build_cls = BhvBuildGNU
        self.bhv_install_cls = BhvInstallGNU


# Behaviour:
#
class Behaviour :


    # __init__:
    #
    def __init__ (self, task) :
        self.task = task

        
    # popen:
    #
    def popen (self, cmd, **kwargs) :
        return gmbexec(cmd, log_extra={}, **kwargs)


# BhvBootstrap:
#
class BhvBootstrap (Behaviour) :
    pass


# BhvConfigure:
#
class BhvConfigure (Behaviour) :
    pass


# BhvBuild:
#
class BhvBuild (Behaviour) :
    pass


# BhvInstall:
#
class BhvInstall (Behaviour) :
    pass


# BhvBootstrapGNU:
#
class BhvBootstrapGNU (BhvBootstrap) :


    # check_run:
    #
    def check_run (self, cmd, item) :
        state, stamp = item.get_state('bootstrap', 'clean')
        if state != 'done' :
            return True
        else :
            return False

    
    # run:
    #
    def run (self, cmd, item) :
        trace("bootstrapping source %s" % item)
        cmd = ['sh', './autogen']
        self.popen(cmd, cwd=item.srcdir)
        item.set_state('bootstrap', 'done')


# BhvConfigureGNU:
#
class BhvConfigureGNU (BhvConfigure) :


    # check_run:
    #
    def check_run (self, cmd, item) :
        state, stamp = item.get_state('configure', 'clean')
        if state != 'done' :
            return True
        else :
            return False


    # run:
    #
    def run (self, cmd, item) :
        trace("configure build %s" % item)
        try: os.mkdir(item.builddir)
        except FileExistsError: pass
        configure = os.path.join(item.source.srcdir, 'configure')
        cmd = [configure, '--prefix', item.target.prefix]
        self.popen(cmd, cwd=item.builddir)
        item.set_state('configure', 'done')


# BhvBuildGNU:
#
class BhvBuildGNU (BhvBuild) :


    # check_run:
    #
    def check_run (self, cmd, item) :
        # check state
        state, stamp = item.get_state('build', 'clean')
        if state != 'done' :
            return True
        # check sources modifications
        if self.__check_sources(stamp, item.source.srcdir) :
            return True
        return False

    def __check_sources (self, stamp, path) :
        st = os.stat(path)
        m = st.st_mode
        if stat.S_ISDIR(m) :
            for child in os.listdir(path) :
                if self.__check_sources(stamp, os.path.join(path, child)) :
                    return True
            return False
        elif stat.S_ISREG(m) :
            if st.st_mtime > stamp :
                trace('file modified: %s' % path)
                return True
            else :
                return False
        else :
            assert 0, path
        

    # run:
    #
    def run (self, cmd, item) :
        trace("build %s" % item)
        self.popen(['make'], cwd=item.builddir)
        item.set_state('build', 'done')


# BhvInstallGNU:
#
class BhvInstallGNU (BhvInstall) :


    # check_run:
    #
    def check_run (self, cmd, item) :
        state, stamp = item.get_state('install', 'clean')
        if state != 'done' :
            return True
        else :
            return False


    # run:
    #
    def run (self, cmd, item) :
        trace("install %s" % item)    
        self.popen(['make', 'install'], cwd=item.builddir)
        item.set_state('install', 'done')


# Client:
#
class Client :


    # __init__:
    #
    def __init__ (self, clid, sock, addr) :
        self.clid = clid
        self.sock = sock
        self.addr = addr
        self.msg_queue = queue.Queue()


    # start:
    #
    def start (self, read_T, write_T) :
        self.read_thread = threading.Thread(target=read_T, args=(self,))
        self.write_thread = threading.Thread(target=write_T, args=(self,))
        self.read_thread.start()
        self.write_thread.start()


# Server
#
class Server :


    # __init__:
    #
    def __init__ (self, port, event_queue) :
        self.event_queue = event_queue
        self.host = ''
        self.port = port
        self.clid_counter = IDCounter()
        self.clients = {}
        self.clients_lock = threading.Lock()

        
    # start:
    #
    def start (self) :
        trace('starting server on port %d ...' % self.port)
        self.listen_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.listen_sock.bind((self.host, self.port))
        self.listen_sock.listen(1)
        self.listen_thread = threading.Thread(target=self.__listen_T)
        self.listen_thread.start()


    # send:
    #
    def send (self, clid, msg) :
        with self.clients_lock :
            client = self.clients.get(clid)
        if client is None :
            # [fixme] ?
            trace("ERROR: client not found: %s" % clid)
        client.msg_queue.put(msg)


    # __listen_T:
    #
    def __listen_T (self) :
        while True :
            conn, addr = self.listen_sock.accept()
            trace('connected by %s' % repr(addr))
            client = Client(self.clid_counter.next(), conn, addr)
            with self.clients_lock :
                self.clients[client.clid] = client
            self.event_queue.put(('connect', client.clid))
            client.start(self.__client_read_T, self.__client_write_T)


    # __client_read_T:
    #
    def __client_read_T (self, cli) :
        f = cli.sock.makefile('rb')
        unpickler = pickle.Unpickler(f)
        while True :
            obj = unpickler.load()
            self.event_queue.put(('message', cli.clid, obj))


    # __client_write_T:
    #
    def __client_write_T (self, cli) :
        f = cli.sock.makefile('wb')
        pickler = pickle.Pickler(f)
        while True :
            msg = cli.msg_queue.get()
            pickler.dump(msg)
            f.flush()


# Command:
#
class Command :
    pass


# CmdBootstrap:
#
class CmdBootstrap (Command) :

    cmdname = 'bootstrap' # [fixme]

    def get_depends (self, item) :
        return ()

    def get_behaviour (self, task) :
        return task.item.bhv_bootstrap_cls(task)


# CmdConfigure:
#
class CmdConfigure (Command) :

    cmdname = 'configure' # [fixme]

    def get_depends (self, item) :
        return ((CmdBootstrap(), item.source),)

    def get_behaviour (self, task) :
        return task.item.bhv_configure_cls(task)

    
# CmdBuild:
#
class CmdBuild (Command) :

    cmdname = 'build' # [fixme]

    def get_depends (self, item) :
        return ((CmdConfigure(), item),)

    def get_behaviour (self, task) :
        return task.item.bhv_build_cls(task)


# CmdInstall:
#
class CmdInstall (Command) :

    cmdname = 'install' # [fixme]

    def get_depends (self, item) :
        return ((CmdBuild(), item),)

    def get_behaviour (self, task) :
        return task.item.bhv_install_cls(task)


# TaskPool:
#
class TaskPool :


    __id_counter = IDCounter()

    
    # __init__:
    #
    def __init__ (self) :
        self.poolid = TaskPool.__id_counter.next()
        self.tasks = []


    # start:
    #
    def start (self) :
        self.t_wait = list(self.tasks)
        self.t_run = []
        self.t_done = []


    # find_task:
    #
    def find_task (self, cmd, item) :
        # [fixme]
        for task in self.tasks :
            if task.cmd.__class__ is cmd.__class__ and task.item is item :
                return task
        return None


    # get_next_task:
    #
    def get_next_task (self) :
        for task in self.t_wait :
            if self.__check_task_run(task) :
                return task
        return None

    def __check_task_run (self, task) :
        for dep in task.depends :
            if dep.state in (Task.S_WAIT, Task.S_RUN) :
                return False
        return True


# Task:
#
class Task :


    # states
    S_WAIT = 0
    S_RUN = 1
    S_SUCCESS = 2
    S_ERROR = 3
    S_CANCEL = 4

    pool = property(lambda s: s._wrpool())


    # __init__:
    #
    def __init__ (self, pool, cmd, item, auto) :
        self._wrpool = weakref.ref(pool)
        self.cmd = cmd
        self.item = item
        self.auto = auto
        self.state = Task.S_WAIT
        self.depends = []
        self.rdepends = []


    # __repr__:
    #
    def __repr__ (self) :
        return gmbrepr(self, "%s:%s" % (self.cmd.cmdname, self.item.name))


# Scheduler:
#
class Scheduler :


    # __init__:
    #
    def __init__ (self, event_queue) :
        self.event_queue = event_queue

        
    # start:
    #
    def start (self) :
        self.max_jobs = 2 # [fixme]
        self.task_pools = []
        self.pending_tasks = []
        self.current_pool = None
        self.process_cond = threading.Condition()
        self.thread = threading.Thread(target=self.__run_T)
        self.thread.start()


    # __run_T:
    #
    def __run_T (self) :
        trace("scheduler: run")
        while True :
            with self.process_cond :
                self.process_cond.wait()
                self.__process()


    # __process:
    #
    def __process (self) :
        trace("scheduler: process")
        # process all pending tasks
        # [FIXME] lock something here ?
        for task, status, exc_info in self.pending_tasks :
            trace("task terminated: %s (%s)" % (task, status))
            assert task.state == Task.S_RUN
            task.state = status
            self.current_pool.t_run.remove(task)
            self.current_pool.t_done.append(task)
            if status == Task.S_SUCCESS :
                assert exc_info is None, exc_info
            elif status == Task.S_ERROR :
                self.__cancel_rdepends(task)
            else :
                assert 0, status
        self.pending_tasks = []
        # check if the current pool has anything left to do
        if self.current_pool is not None :
            if not (self.current_pool.t_wait or self.current_pool.t_run) :
                trace("task pool finished: %s" % self.current_pool)
                self.event_queue.put(('pool-term', self.current_pool.poolid))
                self.current_pool = None
        # if no pool is currently at work, start the first one
        if self.current_pool is None :
            if self.task_pools :
                self.current_pool = self.task_pools.pop(0)
                trace("starting task pool %s" % self.current_pool)
                self.current_pool.start()
            else :
                trace("all task pools finished")
        # try to start the next task(s)
        if self.current_pool is not None :
            while self.current_pool.t_wait and len(self.current_pool.t_run) < self.max_jobs :
                task = self.current_pool.get_next_task()
                if task is None :
                    assert self.current_pool.t_run # !!
                    break
                self.__start_task(self.current_pool, task)


    # __cancel_rdepends:
    #
    def __cancel_rdepends (self, task) :
        for rdep in task.rdepends :
            self.__cancel_task(rdep)

    def __cancel_task (self, task) :
        if task.state == Task.S_CANCEL :
            return
        assert task.state == Task.S_WAIT, task
        trace("task cancelled: %s" % task)
        task.state == Task.S_CANCEL
        task.pool.t_wait.remove(task)
        task.pool.t_done.append(task)


    # __start_task:
    #
    def __start_task (self, pool, task) :
        trace("starting task: %s" % task)
        assert task.state == Task.S_WAIT
        task.state = Task.S_RUN
        pool.t_wait.remove(task)
        pool.t_run.append(task)
        task_thread = threading.Thread(target=self.__run_task, args=(task,))
        task_thread.start()


    # __run_task:
    #
    def __run_task (self, task) :
        trace("running task: %s" % task)
        # [TODO] run...
        status = Task.S_SUCCESS
        exc_info = None
        try:
            bhv = task.cmd.get_behaviour(task)
            if bhv.check_run(task.cmd, task.item) :
                bhv.run(task.cmd, task.item)
        except:
            status = Task.S_ERROR
            exc_info = sys.exc_info()
            error('task %s failed' % task, exc_info=exc_info)
        with self.process_cond :
            self.pending_tasks.append((task, status, exc_info))
            self.process_cond.notify()

                
    # schedule_command:
    #
    def schedule_command (self, cmd, items) :
        trace("scheduling command : %s %s" % (cmd, items))
        pool = TaskPool()
        cmdcls = CmdInstall # [FIXME]
        for i in items :
            cmdobj = cmdcls()
            self.__schedule_task(pool, cmdobj, i, auto=False)
        with self.process_cond :
            self.task_pools.append(pool)
            self.process_cond.notify()
        return pool.poolid


    # __schedule_task:
    #
    def __schedule_task (self, pool, cmd, item, auto) :
        task = pool.find_task(cmd, item)
        # already have this task, stop here
        if task is not None :
            if not auto :
                task.auto = False
            return task
        # create a new task object
        task = Task(pool, cmd, item, auto)
        pool.tasks.append(task)
        for dep_cmd, dep_item in cmd.get_depends(item) :
            dep_task = self.__schedule_task(pool, dep_cmd, dep_item, auto=True)
            # [FIXME] ref cycle
            task.depends.append(dep_task)
            dep_task.rdepends.append(task)
        return task


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
        try:
            # create the config
            self.config = Config()
            # setup the logger
            self.__setup_logger()
            trace('hello')
            # parse command line
            shortopts = 'p:'
            longopts = ['port=']
            opts, args = getopt.gnu_getopt(sys.argv[1:], shortopts, longopts)
            port = 5555
            for o, a in opts :
                if o in ('-p', '--port') :
                    port = int(a)
                else :
                    assert 0, (o, a)
            # init the config
            self.__init_config()
            #
            self.client_log_handlers = {}
            #
            self.event_queue = queue.Queue()
            self.main_thread = threading.Thread(target=self.__main_T)
            self.server = Server(port=port, event_queue=self.event_queue)
            self.scheduler = Scheduler(self.event_queue)
            #
            self.main_thread.start()
            self.server.start()
            self.scheduler.start()
            signal.pause()
        finally:
            sys.stdout.flush()
            sys.stderr.flush()


    # __init_config:
    #
    def __init_config (self) :
        # trace("reading packages list from '%s'" % self.config.pkglistdir)
        self.config.read_packages()


    # __setup_logger:
    #
    def __setup_logger (self) :
        self.logger = log_setup('gmbd')
        # console handler
        hdlr = logging.StreamHandler(sys.stderr)
        fmt = logging.Formatter('%(name)s: %(message)s')
        hdlr.setFormatter(fmt)
        self.logger.addHandler(hdlr)
        # file handler
        try: os.mkdir(self.config.gmbdlogdir)
        except FileExistsError: pass
        fname = os.path.join(self.config.gmbdlogdir, 'gmbd.log')
        h = logging.handlers.RotatingFileHandler(fname, maxBytes=512*1024, backupCount=5)
        h.doRollover()
        h.setLevel(1)
        self.logger.addHandler(h)


    # __main_T:
    #
    def __main_T (self) :
        self.fixme_pool_owner = {} # [fixme]
        while True :
            event = self.event_queue.get()
            trace('event: %s' % repr(event))
            key = event[0]
            if key == 'connect' :
                trace('connect: %s' % repr(event[1:]))
                clid = event[1]
                ssid = 1 # [FIXME]
                self.__setup_client_log_handler(ssid, clid)
                trace("session %d created for client %d" % (ssid, clid), extra={'ssid': ssid})
            elif key == 'message' :
                trace('message: %s' % repr(event[1:]))
                clid = event[1]
                msg = event[2]
                msgkey = msg[0]
                if msgkey == 'command' :
                    target = self.config.targets['home']
                    pkgs = self.config.list_packages()
                    builds = [self.config.get_build(target, p) for p in pkgs]
                    poolid = self.scheduler.schedule_command('install', builds)
                    self.fixme_pool_owner[poolid] = clid
                    self.server.send(clid, ('pool-reg', poolid))
                elif msgkey == 'verb-level' :
                    self.__set_client_verb_level(clid, int(msg[1]), int(msg[2]))
                else :
                    trace("[FIXME] unknown message key: %s" % repr(msgkey))
            elif key == 'pool-term' :
                poolid = event[1]
                clid = self.fixme_pool_owner[poolid]
                self.server.send(clid, ('pool-term', poolid))
            else :
                trace('FIXME: unhandled event: %s' % repr(event[1:]))


    # __setup_client_log_handler:
    #
    def __setup_client_log_handler (self, ssid, clid) :
        h = ClientLogHandler(clid, self.__send_log)
        f1 = ClientLogFilter(clid, ssid)
        h.addFilter(f1)
        f2 = LogLevelFilter()
        h.addFilter(f2)
        self.client_log_handlers[clid] = (h, f1, f2)
        self.logger.addHandler(h)


    # __set_client_verb_level:
    #
    def __set_client_verb_level (self, clid, lvl, cmdlvl) :
        self.client_log_handlers[clid][2].set_level(lvl, cmdlvl)


    # __send_log:
    #
    def __send_log (self, clid, rec) :
        msg = (rec.levelno, rec.message)
        self.server.send(clid, ('log', msg))


# exec
if __name__ == '__main__' :
    GmbdApp.main()
