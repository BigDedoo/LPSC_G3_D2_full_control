# utils/thread_manager.py

from PyQt5.QtCore import QThread

class ThreadManager:
    @staticmethod
    def start_worker(worker):
        """
        Starts a worker in a new QThread. Moves the worker to the thread, connects the thread's
        started signal to the worker's start() method, and returns the thread.
        """
        thread = QThread()
        worker.moveToThread(thread)
        thread.started.connect(worker.start)
        thread.start()
        return thread

    @staticmethod
    def stop_worker(worker, thread):
        """
        Stops the worker and properly quits and waits for the thread to finish.
        """
        worker.stop()
        if thread.isRunning():
            thread.quit()
            thread.wait()
