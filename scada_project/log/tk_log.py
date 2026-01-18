"""Tkinter: okno logow/diagnostyki

Uruchamiane w osobnym watku, odbiera komunikaty przez Queue.
"""

import threading
import tkinter as tk
from tkinter.scrolledtext import ScrolledText
from queue import Queue, Empty


class TkLogWindow:
    def __init__(self, title: str = "Log / Diagnostyka"):
        self.title = title
        self.queue: Queue[str] = Queue()
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._root = None

    def start(self) -> None:
        if not self._thread.is_alive():
            self._thread.start()

    def log(self, msg: str) -> None:
        self.queue.put(msg)

    def _run(self) -> None:
        root = tk.Tk()
        root.title(self.title)
        root.geometry("520x380")

        txt = ScrolledText(root, state='disabled', wrap='word')
        txt.pack(fill='both', expand=True)

        def poll():
            try:
                while True:
                    m = self.queue.get_nowait()
                    txt.configure(state='normal')
                    txt.insert('end', m + "\n")
                    txt.see('end')
                    txt.configure(state='disabled')
            except Empty:
                pass
            root.after(100, poll)

        poll()
        root.mainloop()
