import asyncio
import threading

from PySide6.QtCore import QObject, Signal

class AsyncRunner(QObject):
    completed = Signal(int, object, object)
    progress = Signal(int, object)

    def __init__(self):
        super().__init__()
        self.loop = asyncio.new_event_loop()
        self.ready = threading.Event()
        self.thread = threading.Thread(target=self._run, daemon=True)
        self.thread.start()
        self.ready.wait()
        self.counter = 0
        self.futures = {}
        self.lock = threading.Lock()

    def _run(self):
        asyncio.set_event_loop(self.loop)
        self.ready.set()
        self.loop.run_forever()

    def submit(self, coro):
        with self.lock:
            self.counter += 1
            task_id = self.counter
        future = asyncio.run_coroutine_threadsafe(coro, self.loop)
        self.futures[task_id] = future

        def done(fut):
            self.futures.pop(task_id, None)
            try:
                result = fut.result()
                error = None
            except BaseException as exc:
                result = None
                error = exc
            self.completed.emit(task_id, result, error)

        future.add_done_callback(done)
        return task_id

    def submit_with_progress(self, coro_factory):
        with self.lock:
            self.counter += 1
            task_id = self.counter

        def progress_callback(payload):
            self.progress.emit(task_id, payload)

        future = asyncio.run_coroutine_threadsafe(coro_factory(progress_callback), self.loop)
        self.futures[task_id] = future

        def done(fut):
            self.futures.pop(task_id, None)
            try:
                result = fut.result()
                error = None
            except BaseException as exc:
                result = None
                error = exc
            self.completed.emit(task_id, result, error)

        future.add_done_callback(done)
        return task_id

    def cancel(self, task_id):
        future = self.futures.pop(task_id, None)
        if future is None:
            return False
        return future.cancel()

    def stop(self):
        try:
            self.loop.call_soon_threadsafe(self.loop.stop)
        except Exception:
            pass
        try:
            if self.thread.is_alive():
                self.thread.join(timeout=2)
        except Exception:
            pass