import multiprocessing
import multiprocessing.queues

"""" Queue.qsize() workaround for mac os

Found solution for mac os not implemented error here: https://github.com/keras-team/autokeras/issues/368. 
This is a work around for mac os since multiprocessing.qsize is not implemented on mac os.

"""


class SharedCounter:
    """" A synchronized shared counter.

    The locking done by multiprocessing.Value ensures that only a single
    process or thread may read or write the in-memory ctypes object. However,
    in order to do n += 1, Python performs a read followed by a write, so a
    second process may read the old value before the new one is written by the
    first process. The solution is to use a multiprocessing.Lock to guarantee
    the atomicity of the modifications to Value.

    This class comes almost entirely from Eli Bendersky's blog:
    http://eli.thegreenplace.net/2012/01/04/shared-counter-with-pythons-multiprocessing/

    """

    def __init__(self, val=0):
        self.count = multiprocessing.Value("i", val)

    def increment(self, incr=1):
        """" Increment the counter by n (default = 1) """
        with self.count.get_lock():
            self.count.value += incr

    @property
    def value(self):
        """" Return the value of the counter """
        return self.count.value


class Queue(multiprocessing.queues.Queue):
    """" A portable implementation of multiprocessing.Queue.

    Because of multithreading / multiprocessing semantics, Queue.qsize() may
    raise the NotImplementedError exception on Unix platforms like Mac OS X
    where sem_getvalue() is not implemented. This subclass addresses this
    problem by using a synchronized shared counter (initialized to zero) and
    increasing / decreasing its value every time the put() and get() methods
    are called, respectively. This not only prevents NotImplementedError from
    being raised, but also allows us to implement a reliable version of both
    qsize() and empty().

    """

    def __init__(self, *args, **kwargs):
        super(Queue, self).__init__(*args, ctx=multiprocessing.get_context(), **kwargs)
        self.size = SharedCounter(0)

    def put(self, obj, block=True, timeout=None):
        self.size.increment(1)
        super(Queue, self).put(obj, block, timeout)

    def get(self, block=True, timeout=None):
        self.size.increment(-1)
        return super(Queue, self).get(block, timeout)

    def qsize(self):
        """" Reliable implementation of multiprocessing.Queue.qsize() """
        return self.size.value

    def empty(self):
        """" Reliable implementation of multiprocessing.Queue.empty() """
        return not self.qsize()
