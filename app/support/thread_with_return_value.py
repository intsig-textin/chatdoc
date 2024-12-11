import threading


class ThreadWithReturnValue(threading.Thread):
    def __init__(self, group=None, target=None, name=None, args=(), kwargs=None, *, daemon=None):
        super().__init__(group=group, target=target, name=name, daemon=daemon)
        self.args = args
        self.kwargs = kwargs if kwargs is not None else {}
        self._return = None
        self.exception = None

    def run(self):
        try:
            if self._target is not None:
                self._return = self._target(*self.args, **self.kwargs)
        except Exception as e:
            self.exception = e

    def join(self, *args, **kwargs):
        super().join(*args, **kwargs)
        if self.exception:
            raise self.exception
        return self._return
