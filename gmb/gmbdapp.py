#

import os, sys, glob, getopt, queue, socket, signal, threading, pickle, time, subprocess, json, stat, logging, logging.handlers, weakref, functools, errno, copy

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
        # print("[%d/%d] >> %s" % (rec.orderid, self.clid, rec.message))
        self.send_func(self.clid, rec)


# ClientLogFilter:
#
class ClientLogFilter :

    def __init__ (self, clid) :
        self.clid = clid
        self.orders = set()

    def add_order (self, orderid) :
        self.orders.add(orderid)

    def filter (self, rec) :
        return getattr(rec, 'clid', 0) == self.clid \
          or getattr(rec, 'orderid', 0) in self.orders


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
        try:
            os.mkdir(self.dbdir)
        except OSError as exc:
            if exc.errno == errno.EEXIST : pass
            else : raise
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
            pkg.configure(json.load(open(fname, 'rt')))
            self.packages[pkgname] = pkg
        trace("found %d packages" % len(self.packages))
        self.__fix_depends()


    def __fix_depends (self) :
        for pkg in self.packages.values() :
            pkg.depends = tuple(self.packages[p] for p in pkg.depends)


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


    # configure:
    #
    def configure (self, data) :
        self.depends = tuple(data.pop("depends", ()))        
        assert not data, data


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
        except IOError as exc:
            if exc.errno != errno.ENOENT :
                raise
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
        self.bhv_check_cls = BhvCheckGNU
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
        return gmbexec(cmd, log_extra={'orderid': self.task.order.orderid}, **kwargs)


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


# BhvCheck:
#
class BhvCheck (Behaviour) :
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
        try:
            os.mkdir(item.builddir)
        except OSError as exc:
            if exc.errno != errno.EEXIST : raise
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
        # check depends reinstall ([fixme) lazy/strict option)
        for pkg_dep in item.package.depends :
            build_dep = item.config.get_build(item.target, pkg_dep)
            state_dep, stamp_dep = build_dep.get_state('install', 'clean')
            assert state_dep == 'done'
            if stamp_dep > stamp :
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


# BhvCheckGNU:
#
class BhvCheckGNU (BhvCheck) :


    # check_run:
    #
    def check_run (self, cmd, item) :
        # check state
        state, stamp = item.get_state('check', 'clean')
        if state != 'done' :
            return True
        build_state, build_stamp = item.get_state('build', 'clean')
        assert build_state == 'done', build_state
        if build_stamp > stamp :
            return True
        return False
        

    # run:
    #
    def run (self, cmd, item) :
        trace("check %s" % item)
        self.popen(['make', 'check'], cwd=item.builddir)
        item.set_state('check', 'done')


# BhvInstallGNU:
#
class BhvInstallGNU (BhvInstall) :


    # check_run:
    #
    def check_run (self, cmd, item) :
        state, stamp = item.get_state('install', 'clean')
        if state != 'done' :
            return True
        build_state, build_stamp = item.get_state('build', 'clean')
        assert build_state == 'done', build_state
        if build_stamp > stamp :
            return True
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
    def __init__ (self, clid, sock, addr, msg_queue, rthread, wthread) :
        self.clid = clid
        self.sock = sock
        self.addr = addr
        self.msg_queue = msg_queue
        self.rthread = rthread
        self.wthread = wthread
        self.rclosed = False
        self.wclosed = False


    # start:
    #
    def start (self, read_T, write_T) :
        self.rthread.start()
        self.wthread.start()


# Server
#
class Server :


    # __init__:
    #
    def __init__ (self, port, event_queue) :
        self.event_queue = event_queue
        self.intern_queue = queue.Queue()
        self.host = ''
        self.port = port
        self.id_counter = IDCounter()
        self.clients = {}
        self.clients_lock = threading.Lock()

        
    # start:
    #
    def start (self) :
        trace('starting server on port %d ...' % self.port)
        self.main_thread = threading.Thread(target=self.__main_T)
        self.listen_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.listen_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.listen_sock.bind((self.host, self.port))
        self.listen_sock.listen(1)
        self.listen_thread = threading.Thread(target=self.__listen_T)
        # start all
        self.main_thread.start()
        self.listen_thread.start()


    # __main_T:
    #
    def __main_T (self) :
        while True :
            evt = self.intern_queue.get()
            if evt[0] == 'accept' :
                conn, addr = evt[1:]
                clid = self.id_counter.next()
                msg_queue = queue.Queue()
                rt = threading.Thread(target=self.__client_read_T, args=(clid, conn))
                wt = threading.Thread(target=self.__client_write_T, args=(clid, conn, msg_queue))
                cli = Client(clid, conn, addr, msg_queue, rt, wt)
                trace("client %d accepted: %s" % (cli.clid, addr))
                with self.clients_lock :
                    self.clients[cli.clid] = cli
                self.event_queue.put(('connect', cli.clid))
                rt.start()
                wt.start()
            elif evt[0] == 'end-rthread' :
                clid = evt[1]
                with self.clients_lock :
                    cli = self.clients[clid]
                cli.msg_queue.put(None)
                cli.rthread.join()
                cli.rclosed = True
                self.__close_client(cli)
            elif evt[0] == 'end-wthread' :
                clid = evt[1]
                with self.clients_lock :
                    cli = self.clients[clid]
                cli.wthread.join()
                cli.wclosed = True
                self.__close_client(cli)
            else :
                error("server: unknown event key: %s" % repr(evt))


    # __close_client:
    #
    def __close_client (self, cli) :
        if cli.rclosed and cli.wclosed :
            trace("deleting client %d" % cli.clid)
            cli.sock.close()
            with self.clients_lock :
                del self.clients[cli.clid]
                

    # send:
    #
    def send (self, clid, msg) :
        with self.clients_lock :
            client = self.clients.get(clid)
        if client is None :
            # [fixme] ?
            trace("ERROR: client not found: %s" % clid)
            return
        client.msg_queue.put(msg)


    # __listen_T:
    #
    def __listen_T (self) :
        while True :
            conn, addr = self.listen_sock.accept()
            self.intern_queue.put(('accept', conn, addr))


    # __client_read_T:
    #
    def __client_read_T (self, clid, sock) :
        exc_info = None
        try:
            f = sock.makefile('rb')
            unpickler = pickle.Unpickler(f)
            while True :
                try:
                    obj = unpickler.load()
                except EOFError:
                    trace("got EOF from client %d" % clid)
                    break
                self.event_queue.put(('message', clid, obj))
        except:
            exc_info = sys.exc_info()
            error("error in read thread (client %d)" % clid, exc_info=exc_info)
        f.close()
        self.intern_queue.put(('end-rthread', clid, exc_info))


    # __client_write_T:
    #
    def __client_write_T (self, clid, sock, msg_queue) :
        exc_info = None
        try:
            f = sock.makefile('wb')
            pickler = pickle.Pickler(f)
            while True :
                msg = msg_queue.get()
                if msg is None :
                    trace("got END for client %d" % clid)
                    break
                pickler.dump(msg)
                f.flush()
        except:
            exc_info = sys.exc_info()
            error("error in write thread (client %d)" % clid, exc_info=exc_info)
        f.close()
        self.intern_queue.put(('end-wthread', clid, exc_info))


# Command:
#
class Command :
    pass


# CmdBootstrap:
#
class CmdBootstrap (Command) :

    cmdname = 'bootstrap' # [fixme]

    def get_depends (self, item) :
        depends = []
        # [fixme]
        config = item.config
        target = config.targets['home']
        depends.extend((CmdInstall(), config.get_build(target, dep))
                       for dep in item.package.depends)
        return depends

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


# CmdCheck:
#
class CmdCheck (Command) :

    cmdname = 'check' # [fixme]

    def get_depends (self, item) :
        return ((CmdBuild(), item),)

    def get_behaviour (self, task) :
        return task.item.bhv_check_cls(task)


# CmdInstall:
#
class CmdInstall (Command) :

    cmdname = 'install' # [fixme]

    def get_depends (self, item) :
        return ((CmdCheck(), item),)

    def get_behaviour (self, task) :
        return task.item.bhv_install_cls(task)


# Order:
#
class Order :


    __id_counter = IDCounter()

    
    # __init__:
    #
    def __init__ (self, config) :
        self.config = config
        self.orderid = Order.__id_counter.next()
        self.tasks = []


    # list_tasks:
    #
    # Return all taskid registered for this order.
    #
    def list_tasks (self) :
        return [t.taskid for t in self.tasks]


    # get_task:
    #
    # Return the task object associated with an id.
    #
    def get_task (self, taskid) :
        # [FIXME]
        for t in self.tasks :
            if t.taskid == taskid :
                return t
        assert 0, taskid


    # list_depends:
    #
    def list_depends (self, taskid, recurse=False) :
        assert not recurse # [TODO]
        task = self.get_task(taskid)
        return [d.taskid for d in task.depends]


    # list_rdepends:
    #
    def list_rdepends (self, taskid, recurse=False) :
        assert recurse # [TODO]
        task = self.get_task(taskid)
        deplist = set()
        self._list_rdepends(task, deplist)
        return list(deplist)

    def _list_rdepends (self, task, deplist) :
        for rdep in task.rdepends :
            if rdep.taskid in deplist :
                continue
            deplist.add(rdep.taskid)
            self._list_rdepends(rdep, deplist)


    # start:
    #
    # [REMOVEME]
    #
    def start (self) :
        self.t_wait = list(self.tasks)
        self.t_run = []
        self.t_done = []


    # find_task:
    #
    # [FIXME]
    #
    def find_task (self, cmd, item) :
        # [fixme]
        for task in self.tasks :
            if task.cmd.__class__ is cmd.__class__ and task.item is item :
                return task
        return None


    # get_next_task:
    #
    # [REMOVEME]
    #
    def get_next_task (self) :
        for task in self.t_wait :
            if self.__check_task_run(task) :
                return task
        return None

    def __check_task_run (self, task) :
        for dep in task.depends :
            if dep.state in (TaskState.WAITING, TaskState.RUNNING) :
                return False
        return True


# ORT:
#
# Order runtime.
#
class ORT :


    order = property(lambda s: s.__order)
    orderid = property(lambda s: s.__order.orderid)
    n_waiting = property(lambda s: s.get_state_count(TaskState.WAITING))
    n_running = property(lambda s: s.get_state_count(TaskState.RUNNING))

    
    # __init__:
    #
    def __init__ (self, order) :
        self.__order = order
        tlist = order.list_tasks()
        self.__states = dict((t, TaskState.WAITING)
                             for t in tlist)
        self.__states_map = {
            TaskState.WAITING:    set(tlist),
            TaskState.RUNNING:     set(),
            TaskState.SUCCESS: set(),
            TaskState.ERROR:   set(),
            TaskState.CANCELLED:  set(),
        }


    # get_state:
    #
    def get_state (self, taskid) :
        return self.__states[taskid]


    # set_state:
    #
    def set_state (self, taskid, state) :
        old_state = self.__states[taskid]
        if old_state == state :
            return
        self.__states_map[old_state].remove(taskid)
        self.__states_map[state].add(taskid)
        self.__states[taskid] = state


    # get_state_count:
    #
    # Return the number of tasks which are in a particular state.
    #
    def get_state_count (self, state) :
        return len(self.__states_map[state])


    # get_states_map:
    #
    def get_states_map (self) :
        return copy.deepcopy(self.__states_map)


    # is_finished:
    #
    def is_finished (self) :
        return not (self.__states_map[TaskState.WAITING] or self.__states_map[TaskState.RUNNING])


    # peek_ready:
    #
    # Peek one task ready to run (ie all its depends are done
    # successfully) and returns its taskid or 0 if not found.
    #
    def peek_ready (self) :
        for tid in self.__states_map[TaskState.WAITING] :
            if self.is_ready(tid) :
                return tid
        return 0


    # is_ready:
    #
    # True if the given task is ready to run.
    #
    def is_ready (self, taskid) :
        for depid in self.__order.list_depends(taskid, recurse=False) :
            depstate = self.__states[depid]
            if depstate != TaskState.SUCCESS :
                return False
        return True


# Task:
#
class Task :


    taskid = property(lambda s: s.__taskid)
    order = property(lambda s: s._wrorder())

    __id_counter = IDCounter()


    # __init__:
    #
    def __init__ (self, order, cmd, item, auto) :
        self.__taskid = Task.__id_counter.next()
        self._wrorder = weakref.ref(order)
        self.cmd = cmd
        self.item = item
        self.auto = auto
        self.state = TaskState.WAITING
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
        self.orders = []
        self.pending_tasks = []
        self.ort = None
        self.process_cond = threading.Condition()
        self.thread = threading.Thread(target=self.__run_T)
        self.thread.start()


    # add_order:
    #
    def add_order (self, order) :
        with self.process_cond :
            self.orders.append(order)
            self.process_cond.notify()


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
        # finalize all pending tasks
        while self.pending_tasks :
            task, status, exc_info = self.pending_tasks.pop()
            self.__finalize_task(task, status, exc_info)
        self.pending_tasks = []
        # finalize the current order if all tasks are done
        if self.ort is not None and self.ort.is_finished() :
            self.__finalize_order()
        # if no order is currently at work, start the first one
        if self.ort is None :
            if not self.orders :
                trace("all orders finished")
                return
            self.__start_order()
        # try to start the next task(s)
        while self.ort.n_waiting > 0 and self.ort.n_running < self.max_jobs :
            taskid = self.ort.peek_ready()
            if taskid == 0 :
                trace("[fixme] no task is ready")
                break
            self.__start_task(taskid)


    # __start_task:
    #
    def __start_task (self, taskid) :
        task = self.ort.order.get_task(taskid) # [fixme]
        trace("starting task %d (%s)" % (taskid, task))
        assert self.ort.get_state(task.taskid) == TaskState.WAITING
        self.ort.set_state(task.taskid, TaskState.RUNNING)
        # [FIXME] use a pool of worker threads instead
        task_thread = threading.Thread(target=self.__run_task, args=(task,))
        task_thread.start()


    # __finalize_task:
    #
    def __finalize_task (self, task, status, exc_info) :
        trace("task terminated: %s (%s)" % (task, status))
        if status == TaskState.SUCCESS :
            assert exc_info is None, exc_info
        elif status == TaskState.ERROR :
            self.__cancel_rdepends(task.taskid)
        else :
            assert 0, status
        assert self.ort.get_state(task.taskid) == TaskState.RUNNING
        self.ort.set_state(task.taskid, status)


    # __start_order:
    #
    def __start_order (self) :
        assert self.ort is None
        order = self.orders.pop(0)
        self.ort = ORT(order)
        trace("starting task order %s" % self.ort,
              extra={'orderid': self.ort.orderid})


    # __finalize_order:
    #
    def __finalize_order (self) :
        trace("order finished: %s" % self.ort.order,
              extra={'orderid': self.ort.orderid})
        self.event_queue.put(('order-term', self.ort.orderid, self.ort.get_states_map()))
        self.ort = None


    # __cancel_rdepends:
    #
    def __cancel_rdepends (self, taskid) :
        for rdep in self.ort.order.list_rdepends(taskid, recurse=True) :
            s = self.ort.get_state(rdep)
            if s == TaskState.CANCELLED :
                pass
            elif s == TaskState.WAITING :
                trace("cancelling task %d" % rdep)
                self.ort.set_state(rdep, TaskState.CANCELLED)
            else :
                assert 0, (rdep, s)


    # __run_task:
    #
    def __run_task (self, task) :
        trace("running task: %s" % task)
        # [TODO] run...
        status = TaskState.SUCCESS
        exc_info = None
        try:
            bhv = task.cmd.get_behaviour(task)
            trace("behaviour: %s" % bhv)
            if bhv.check_run(task.cmd, task.item) :
                trace(" -> run")
                bhv.run(task.cmd, task.item)
            else :
                trace(" -> skip")
        except:
            trace(" -> error")
            status = TaskState.ERROR
            exc_info = sys.exc_info()
            error('task %s failed' % task, exc_info=exc_info)
        trace(" -> done")
        with self.process_cond :
            self.pending_tasks.append((task, status, exc_info))
            self.process_cond.notify()


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
        r = 0
        try:
            self.__real_run()
        except:
            print_exception()
            r = 1
        finally:
            sys.stdout.flush()
            sys.stderr.flush()
        sys.exit(r)


    # __real_run:
    #
    def __real_run (self) :
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
        self.order_owner = {}
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
        try:
            os.mkdir(self.config.gmbdlogdir)
        except OSError as exc:
            if exc.errno != errno.EEXIST : raise
        fname = os.path.join(self.config.gmbdlogdir, 'gmbd.log')
        h = logging.handlers.RotatingFileHandler(fname, maxBytes=512*1024, backupCount=5)
        h.doRollover()
        h.setLevel(1)
        self.logger.addHandler(h)


    # __main_T:
    #
    def __main_T (self) :
        handlers = {
            'connect':      self.__on_connect,
            'message':      self.__on_message,
            'order-term': self.__on_order_term,
        }
        while True :
            event = self.event_queue.get()
            trace('event: %s' % repr(event))
            try:
                h = handlers[event[0]]
            except KeyError:
                error("no handler for event: %s" % repr(event))
                continue
            h(event)


    # __on_connect:
    #
    def __on_connect (self, event) :
        clid = event[1]
        self.__setup_client_log_handler(clid)
        trace("client %d connected" % clid)


    # __on_message:
    #
    def __on_message (self, event) :
        trace('message: %s' % repr(event[1:]))
        clid = event[1]
        msg = event[2]
        msgkey = msg[0]
        if msgkey == 'install' :
            self.__schedule_order(clid)
        elif msgkey == 'verb-level' :
            self.__set_client_verb_level(clid, int(msg[1]), int(msg[2]))
        else :
            trace("[FIXME] unknown message key: %s" % repr(msgkey))


    # __on_order_term:
    #
    def __on_order_term (self, event) :
        orderid = event[1]
        states = event[2]
        clid = self.order_owner[orderid]
        self.server.send(clid, ('order-term', orderid, states))


    # __schedule_order:
    #
    def __schedule_order (self, clid) :
        target = self.config.targets['home']
        pkgs = self.config.list_packages()
        builds = [self.config.get_build(target, p) for p in pkgs]

        # trace("scheduling command : %s %s" % (cmd, items))
        order = Order(self.config)
        cmdcls = CmdInstall # [FIXME]
        for i in builds :
            cmdobj = cmdcls()
            self.__schedule_task(order, cmdobj, i, auto=False)

        self.order_owner[order.orderid] = clid
        self.client_log_handlers[clid][1].add_order(order.orderid)
        self.server.send(clid, ('order-reg', order.orderid))

        self.scheduler.add_order(order)


    # __schedule_task:
    #
    def __schedule_task (self, order, cmd, item, auto) :
        task = order.find_task(cmd, item)
        # already have this task, stop here
        if task is not None :
            if not auto :
                task.auto = False
            return task
        # create a new task object
        task = Task(order, cmd, item, auto)
        order.tasks.append(task)
        for dep_cmd, dep_item in cmd.get_depends(item) :
            dep_task = self.__schedule_task(order, dep_cmd, dep_item, auto=True)
            # [FIXME] ref cycle
            task.depends.append(dep_task)
            dep_task.rdepends.append(task)
        return task


    # __setup_client_log_handler:
    #
    def __setup_client_log_handler (self, clid) :
        h = ClientLogHandler(clid, self.__send_log)
        f1 = ClientLogFilter(clid)
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
