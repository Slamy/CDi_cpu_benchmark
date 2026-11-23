"""Live UART benchmark comparison. Run with python3 benchmark_results/live_gui.py."""
import codecs
import glob
import os
import queue
import re
import select
import threading
import time
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

from analyze import Capture, ROOT, compare, export


def uart_chunks(port, baud, stop):
    """Read a POSIX UART as 8N1 with flow control disabled; restore on close."""
    import termios
    speed = getattr(termios, f'B{baud}', None)
    if speed is None:
        raise ValueError(f'Unsupported baud rate: {baud}')
    fd = os.open(port, os.O_RDWR | os.O_NOCTTY | os.O_NONBLOCK)
    original = None
    try:
        original = termios.tcgetattr(fd)
        settings = termios.tcgetattr(fd)
        settings[0] = settings[1] = settings[3] = 0
        settings[2] = termios.CS8 | termios.CREAD | termios.CLOCAL
        settings[4] = settings[5] = speed
        settings[6][termios.VMIN] = 0
        settings[6][termios.VTIME] = 0
        termios.tcsetattr(fd, termios.TCSANOW, settings)
        yield None  # Device opened successfully.
        while not stop.is_set():
            if select.select([fd], [], [], 0.2)[0]:
                chunk = os.read(fd, 8192)
                if not chunk:
                    raise OSError('UART disconnected')
                yield chunk
    finally:
        try:
            if original is not None:
                termios.tcsetattr(fd, termios.TCSANOW, original)
        finally:
            os.close(fd)


def file_chunks(path, stop, start_at_end=True):
    """Follow new output; read restarted files from their beginning."""
    with open(path, 'rb') as stream:
        if start_at_end:
            stream.seek(0, os.SEEK_END)
        yield None
        while not stop.is_set():
            stat = os.stat(path)
            opened = os.fstat(stream.fileno())
            if (stat.st_dev, stat.st_ino) != (opened.st_dev, opened.st_ino):
                yield b''  # Reset the capture when its source is replaced.
                return
            if stat.st_size < stream.tell():
                stream.seek(0)
                yield b''
            chunk = stream.read(8192)
            if chunk:
                yield chunk
            else:
                stop.wait(0.2)


def receive(mode, target, baud, stop, emit):
    """Worker: frame CR/LF lines without exposing partial UART reads to parsing."""
    decoder = codecs.getincrementaldecoder('utf-8')(errors='replace')
    pending = ''
    first_file = True
    try:
        while not stop.is_set():
            chunks = uart_chunks(target, baud, stop) if mode == 'UART' else file_chunks(target, stop, start_at_end=first_file)
            first_file = False
            for chunk in chunks:
                if stop.is_set():
                    break
                if chunk is None:
                    emit('status', 'Receiving')
                    continue
                if chunk == b'':
                    decoder.reset()
                    pending = ''
                    emit('reset', 'Source file restarted')
                    continue
                pending += decoder.decode(chunk).replace('\r', '\n')
                lines = pending.split('\n')
                pending = lines.pop()
                for line in lines:
                    if line:
                        emit('line', line)
                if len(pending) > 65536:
                    raise ValueError('No line ending received in 64 KiB; check the baud rate')
            if mode == 'UART' or stop.is_set():
                break
    except Exception as error:
        emit('error', str(error))
    finally:
        emit('done', '')


class Source:
    def __init__(self, app, name, baud):
        self.app, self.name = app, name
        self.capture = Capture()
        self.raw = []
        self.stop = None
        self.worker = None
        self.synchronizing = False
        self.latest_only = False
        self.generation = 0
        box = ttk.LabelFrame(app.sources, text=name.upper(), padding=10)
        box.pack(side='left', fill='both', expand=True, padx=5)
        self.mode = tk.StringVar(value='UART' if name == 'realcdi' else 'Follow log')
        self.target = tk.StringVar(value='/dev/ttyUSB0' if name == 'realcdi' else str(ROOT / 'log_measure'))
        self.baud = tk.StringVar(value=str(baud))
        self.reset_on_connect = tk.BooleanVar(value=True)
        line = ttk.Frame(box)
        line.pack(fill='x')
        ttk.Combobox(line, textvariable=self.mode, values=['UART', 'Follow log'], state='readonly', width=12).pack(side='left')
        ttk.Label(line, text='Baud').pack(side='left', padx=(12, 4))
        ttk.Combobox(line, textvariable=self.baud, values=['9600', '19200', '38400', '57600', '115200', '230400'], width=9).pack(side='left')
        self.ports = ttk.Combobox(box, textvariable=self.target)
        self.ports.pack(fill='x', pady=7)
        self.refresh_ports()
        actions = ttk.Frame(box)
        actions.pack(fill='x')
        self.connect_button = ttk.Button(actions, text='Connect', command=self.connect)
        self.connect_button.pack(side='left')
        ttk.Button(actions, text='Disconnect', command=self.disconnect).pack(side='left', padx=4)
        ttk.Button(actions, text='Browse…', command=self.browse).pack(side='left')
        ttk.Button(actions, text='Load log…', command=self.load).pack(side='left', padx=4)
        actions = ttk.Frame(box)
        actions.pack(fill='x', pady=6)
        ttk.Button(actions, text='Clear', command=self.clear).pack(side='left')
        ttk.Button(actions, text='Save capture…', command=self.save).pack(side='left', padx=4)
        ttk.Checkbutton(actions, text='Clear on connect', variable=self.reset_on_connect).pack(side='left')
        self.status = tk.StringVar(value='Disconnected')
        self.counts = tk.StringVar()
        ttk.Label(box, textvariable=self.status, wraplength=480).pack(anchor='w')
        ttk.Label(box, textvariable=self.counts).pack(anchor='w')
        self.update_counts()

    def refresh_ports(self):
        self.ports['values'] = sorted(set(glob.glob('/dev/ttyUSB*') + glob.glob('/dev/ttyACM*') + glob.glob('/dev/ttyS*') + glob.glob('/dev/cu.*')))

    def browse(self):
        path = filedialog.askopenfilename(title='Select growing capture log')
        if path:
            self.mode.set('Follow log')
            self.target.set(path)

    def update_counts(self):
        mode = ' · latest cycle per location, no averaging' if self.latest_only else ''
        self.counts.set(f'{self.capture.cycles} complete cycles · {len(self.capture.current)} pending measurements{mode}')

    def clear(self):
        self.capture = Capture()
        self.raw = []
        self.synchronizing = bool(self.worker and self.worker.is_alive())
        self.update_counts()
        self.app.dirty = True

    def load(self, path=None):
        if path is None:
            path = filedialog.askopenfilename(title=f'Load {self.name.upper()} benchmark log')
        if not path:
            return
        try:
            content = Path(path).read_text(errors='replace')
        except OSError as error:
            messagebox.showerror('Cannot load log', str(error))
            return
        self.disconnect()
        self.latest_only = False
        self.clear()
        for line in content.splitlines():
            self.accept(line)
        self.status.set(f'Loaded {Path(path).name}')

    def accept(self, line):
        if self.synchronizing:
            # Attaching midway through a cycle must not produce a partial sample.
            if line.strip() == '-----' or re.search(r'(?:^|\]\s+)FMA DCLK\s+\d+\s+\d+\s*$', line):
                self.synchronizing = False
                self.status.set('Receiving')
            return
        self.raw.append(line)
        if self.capture.feed(line, latest_only=self.latest_only):
            self.app.dirty = True

    def save(self):
        path = filedialog.asksaveasfilename(title='Save raw capture', initialfile=f'log_{self.name}', confirmoverwrite=True)
        if path:
            try:
                Path(path).write_text('\n'.join(self.raw) + ('\n' if self.raw else ''))
            except OSError as error:
                messagebox.showerror('Cannot save capture', str(error))

    def connect(self):
        if self.worker and self.worker.is_alive():
            messagebox.showinfo('Receiver stopping', 'Wait for the previous connection to close, then connect again.')
            return
        self.refresh_ports()
        try:
            baud = int(self.baud.get())
            if not self.target.get().strip():
                raise ValueError('Choose a UART device or capture file')
        except ValueError as error:
            messagebox.showerror('Invalid connection', str(error))
            return
        if self.reset_on_connect.get():
            self.clear()
        else:
            self.capture.current = []  # Never combine fragments from different sessions.
        self.synchronizing = True
        self.latest_only = self.mode.get() == 'Follow log'
        self.generation += 1
        generation = self.generation
        stop = threading.Event()
        self.stop = stop

        def emit(kind, value):
            while not stop.is_set():
                try:
                    self.app.events.put((self.name, generation, kind, value), timeout=0.2)
                    return
                except queue.Full:
                    pass

        self.status.set('Connecting…')
        self.connect_button.configure(state='disabled')
        self.worker = threading.Thread(target=receive, args=(self.mode.get(), self.target.get(), baud, stop, emit), daemon=True)
        self.worker.start()

    def disconnect(self):
        if self.stop:
            self.stop.set()
        self.generation += 1
        self.status.set('Disconnected')
        self.connect_button.configure(state='normal')


class App:
    def __init__(self, root):
        self.root = root
        self.events = queue.Queue(maxsize=10000)
        self.dirty = True
        root.title('CD-i Live Benchmark Comparison')
        root.geometry('1450x820')
        root.minsize(1050, 600)
        style = ttk.Style(root)
        if 'clam' in style.theme_names():
            style.theme_use('clam')
        style.configure('Treeview', rowheight=26)
        ttk.Label(root, text='CD-i Live Benchmark Comparison', font=('', 19, 'bold')).pack(anchor='w', padx=15, pady=(12, 4))
        ttk.Label(root, text='Complete cycles update the table. Red = fewer MiSTer operations per phase. UART: 8N1, no flow control.').pack(anchor='w', padx=15)
        self.sources = ttk.Frame(root, padding=8)
        self.sources.pack(fill='x')
        self.inputs = {name: Source(self, name, baud) for name, baud in [('realcdi', 9600), ('measure', 115200)]}
        controls = ttk.Frame(root, padding=(15, 5))
        controls.pack(fill='x')
        ttk.Label(controls, text='Phase').pack(side='left')
        self.phase = tk.StringVar(value='All')
        phase = ttk.Combobox(controls, textvariable=self.phase, values=['All', 'DA=0', 'DA=1'], state='readonly', width=8)
        phase.pack(side='left', padx=5)
        phase.bind('<<ComboboxSelected>>', lambda _: self.refresh())
        self.regressions = tk.BooleanVar()
        ttk.Checkbutton(controls, text='Only negative changes', variable=self.regressions, command=self.refresh).pack(side='left', padx=10)
        ttk.Label(controls, text='Filter').pack(side='left')
        self.search = tk.StringVar()
        self.search.trace_add('write', lambda *_: self.refresh())
        ttk.Entry(controls, textvariable=self.search, width=25).pack(side='left', padx=5)
        ttk.Button(controls, text='Export Markdown + CSV…', command=self.export).pack(side='right')
        frame = ttk.Frame(root, padding=(15, 5))
        frame.pack(fill='both', expand=True)
        columns = ('location', 'benchmark', 'phase', 'realcdi_n', 'realcdi_mean', 'realcdi_sd', 'realcdi_variance', 'mister_n', 'mister_mean', 'mister_sd', 'mister_variance', 'change')
        self.table = ttk.Treeview(frame, columns=columns, show='headings')
        headings = ['Code location', 'Benchmark', 'Phase', 'V n', 'CDI value', 'V SD', 'V variance', 'M n', 'MiSTer value', 'M SD', 'M variance', 'MiSTer change']
        for key, title in zip(columns, headings):
            self.table.heading(key, text=title)
            self.table.column(key, width=170 if key == 'benchmark' else 100, minwidth=65, anchor='w' if key in ('location', 'benchmark') else 'e')
        self.table.tag_configure('negative', foreground='#a01414', background='#ffe5e5')
        self.table.tag_configure('positive', foreground='#17602e')
        y = ttk.Scrollbar(frame, orient='vertical', command=self.table.yview)
        x = ttk.Scrollbar(frame, orient='horizontal', command=self.table.xview)
        self.table.configure(yscrollcommand=y.set, xscrollcommand=x.set)
        self.table.grid(row=0, column=0, sticky='nsew')
        y.grid(row=0, column=1, sticky='ns')
        x.grid(row=1, column=0, sticky='ew')
        frame.rowconfigure(0, weight=1)
        frame.columnconfigure(0, weight=1)
        self.summary = tk.StringVar()
        ttk.Label(root, textvariable=self.summary, padding=(15, 8)).pack(anchor='w')
        for name, source in self.inputs.items():
            path = ROOT / f'log_{name}'
            if path.exists():
                source.load(path)
            source.update_counts()
        self.refresh()
        root.protocol('WM_DELETE_WINDOW', self.close)
        self.timer = root.after(100, self.poll)

    def parsed(self):
        return {name: source.capture.snapshot() for name, source in self.inputs.items()}

    def refresh(self):
        rows = compare(self.parsed(), combine_phases=self.phase.get() == 'All')
        selected = self.table.selection()
        position = self.table.yview()[0]
        self.table.delete(*self.table.get_children())
        negatives = sum(row['mister_change_percent'] is not None and row['mister_change_percent'] < 0 for row in rows)
        shown = 0
        for index, row in enumerate(rows):
            change = row['mister_change_percent']
            if self.phase.get() != 'All' and row['phase'] != self.phase.get():
                continue
            if self.regressions.get() and (change is None or change >= 0):
                continue
            if self.search.get().lower() not in f"{row['location']} {row['benchmark']}".lower():
                continue
            values = [row['location'], row['benchmark'], row['phase']]
            for name in ['realcdi', 'measure']:
                values.append(row[f'{name}_n'])
                for stat in ['mean', 'sd', 'variance']:
                    value = row[f'{name}_{stat}']
                    values.append('—' if value is None else f'{value:.3f}' if stat == 'variance' else f'{value:.2f}')
            values.append('—' if change is None else f'{change:+.1f}%')
            tag = 'negative' if change is not None and change < 0 else 'positive' if change is not None and change > 0 else ''
            self.table.insert('', 'end', iid=str(index), values=values, tags=(tag,))
            shown += 1
        for item in selected:
            if self.table.exists(item):
                self.table.selection_add(item)
        self.table.yview_moveto(position)
        self.summary.set(f'{shown} rows shown · {negatives} negative comparisons · Follow log: latest cycle per location. UART/loaded logs: averages. SD/variance require 2 samples.')
        self.dirty = False

    def poll(self):
        deadline = time.monotonic() + 0.03
        while time.monotonic() < deadline:
            try:
                name, generation, kind, value = self.events.get_nowait()
            except queue.Empty:
                break
            source = self.inputs[name]
            if generation != source.generation:
                continue
            if kind == 'line':
                source.accept(value)
            elif kind == 'reset':
                source.clear()
                source.synchronizing = False  # Restarted files are read from the beginning.
                source.status.set(value)
            elif kind in ('status', 'error'):
                source.status.set('Receiving · waiting for first cycle separator' if kind == 'status' and source.synchronizing else value)
            elif kind == 'done':
                source.connect_button.configure(state='normal')
        for source in self.inputs.values():
            source.update_counts()
        if self.dirty:
            self.refresh()
        self.timer = self.root.after(150, self.poll)

    def export(self):
        target = filedialog.askdirectory(title='Export comparison.md and comparison.csv')
        if target:
            if any((Path(target) / name).exists() for name in ['comparison.md', 'comparison.csv']):
                if not messagebox.askyesno('Replace comparison files?', 'Replace comparison.md and comparison.csv in this folder?'):
                    return
            try:
                export(self.parsed(), target)
            except OSError as error:
                messagebox.showerror('Cannot export', str(error))
            else:
                messagebox.showinfo('Export complete', f'Saved comparison.md and comparison.csv to {target}')

    def close(self):
        for source in self.inputs.values():
            source.disconnect()
        for source in self.inputs.values():
            if source.worker:
                source.worker.join(timeout=1)
        self.root.after_cancel(self.timer)
        self.root.destroy()


if __name__ == '__main__':
    App(tk.Tk()).root.mainloop()
