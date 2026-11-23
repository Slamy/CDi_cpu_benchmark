"""Run with python3 -m unittest discover -s benchmark_results -v."""
import os
import pty
import queue
import tempfile
import threading
import time
import unittest
from pathlib import Path

from analyze import Capture, ROOT, compare, export, parse
from live_gui import receive


class CaptureTests(unittest.TestCase):
    def test_combined_phases_use_per_cycle_totals(self):
        vmpeg, mister = Capture(), Capture()
        for a, b in [(10, 30), (20, 20)]:
            vmpeg.feed(f'[SYSRAM] Add {a} {b}')
            vmpeg.feed('-----')
        for a, b in [(30, 20), (40, 10)]:
            mister.feed(f'[SYSRAM] Add {a} {b}')
            mister.feed('-----')
        parsed = {'vmpeg': vmpeg.snapshot(), 'mister': mister.snapshot()}
        rows = compare(parsed, combine_phases=True)
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]['phase'], 'DA=0+1')
        self.assertEqual(rows[0]['vmpeg_n'], 2)
        self.assertEqual(rows[0]['vmpeg_mean'], 40)
        self.assertEqual(rows[0]['mister_mean'], 50)
        self.assertEqual(rows[0]['vmpeg_variance'], 0)
        self.assertEqual(rows[0]['mister_sd'], 0)
        self.assertEqual(rows[0]['mister_change_percent'], 25)
        self.assertEqual(len(compare(parsed)), 2)

    def test_latest_cycle_per_location_replaces_old_values(self):
        capture = Capture()
        for line in ['[VIDEO1] Add 10 20', '[VIDEO1] removed 1 2', '-----',
                     '[SYSRAM] Add 30 40', '-----', '[VIDEO1] Add 50 60']:
            capture.feed(line, latest_only=True)
        self.assertEqual(capture.data['VIDEO1', 'Add'], [(10, 20)])
        capture.feed('-----', latest_only=True)
        self.assertEqual(capture.data['VIDEO1', 'Add'], [(50, 60)])
        self.assertEqual(capture.data['SYSRAM', 'Add'], [(30, 40)])
        self.assertNotIn(('VIDEO1', 'removed'), capture.data)
        rows = compare({'vmpeg': capture.snapshot(), 'mister': capture.snapshot()})
        self.assertTrue(all(row['vmpeg_n'] == 1 for row in rows))
        self.assertTrue(all(row['vmpeg_variance'] is None for row in rows))

    def test_partial_cycles_legacy_labels_and_single_sample(self):
        capture = Capture()
        capture.feed('Jo! 0 0')
        capture.feed('[SYSRAM] new measurement 4 20')
        self.assertFalse(capture.data)
        self.assertTrue(capture.feed('-----'))
        capture.feed('[SYSRAM] new measurement 6 24')
        self.assertTrue(capture.feed('[SYSRAM] FMA DCLK 92 807'))
        capture.feed('[SYSRAM] unfinished 99 99')
        other = Capture()
        other.feed('[SYSRAM] new measurement 2 10')
        other.feed('-----')
        rows = compare({'vmpeg': capture.snapshot(), 'mister': other.snapshot()})
        self.assertEqual(len(rows), 2)
        self.assertEqual(rows[0]['vmpeg_mean'], 5)
        self.assertEqual(rows[0]['vmpeg_variance'], 2)
        self.assertEqual(rows[0]['mister_mean'], 2)
        self.assertIsNone(rows[0]['mister_variance'])
        self.assertEqual(rows[0]['mister_change_percent'], -60)
        self.assertEqual(capture.cycles, 2)
        with tempfile.TemporaryDirectory() as folder:
            report = export({'vmpeg': capture.snapshot(), 'mister': other.snapshot()}, folder)
            self.assertIn('🔴 **-60.0%**', report)
            self.assertTrue((Path(folder) / 'comparison.csv').exists())

    def test_real_logs_stream_like_file_parser(self):
        for name in ['vmpeg', 'mister']:
            path = ROOT / f'log_{name}'
            capture = Capture()
            content = path.read_text(errors='replace')
            for line in content.splitlines():
                capture.feed(line)
            with tempfile.TemporaryDirectory() as folder:
                snapshot = Path(folder) / 'snapshot'
                snapshot.write_text(content)
                self.assertEqual(capture.snapshot(), parse(snapshot))
            self.assertGreater(capture.cycles, 0)

    def test_empty_export(self):
        with tempfile.TemporaryDirectory() as folder:
            export({name: Capture().snapshot() for name in ['vmpeg', 'mister']}, folder)
            self.assertEqual((Path(folder) / 'comparison.csv').read_text(), 'location,benchmark,phase\n')


class ReceiverTests(unittest.TestCase):
    def setUp(self):
        self.stop = threading.Event()
        self.events = queue.Queue()
        self.worker = None

    def tearDown(self):
        self.stop.set()
        if self.worker:
            self.worker.join(timeout=2)
            self.assertFalse(self.worker.is_alive())

    def start(self, mode, target):
        self.worker = threading.Thread(target=receive, args=(mode, target, 9600, self.stop, lambda k, v: self.events.put((k, v))))
        self.worker.start()
        self.assertEqual(self.events.get(timeout=2), ('status', 'Receiving'))

    def test_uart_fragmented_crlf_and_unplug(self):
        master, slave = pty.openpty()
        try:
            self.start('UART', os.ttyname(slave))
            os.write(master, b'[SYSRAM] Add 10')
            time.sleep(0.03)
            os.write(master, b' 20\r\n---')
            time.sleep(0.03)
            os.write(master, b'--\r\n')
            self.assertEqual(self.events.get(timeout=2), ('line', '[SYSRAM] Add 10 20'))
            self.assertEqual(self.events.get(timeout=2), ('line', '-----'))
            os.close(master)
            master = None
            self.assertEqual(self.events.get(timeout=2)[0], 'error')
            self.assertEqual(self.events.get(timeout=2)[0], 'done')
        finally:
            if master is not None:
                os.close(master)
            os.close(slave)

    def test_file_append_and_truncation(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'capture'
            path.write_text('[VIDEO1] Add 1 2\n-----\n')
            self.start('Follow log', str(path))
            self.assertTrue(self.events.empty())
            with path.open('a') as stream:
                stream.write('[SYSRAM] Add 3 4\n-----\n')
            self.assertEqual(self.events.get(timeout=2), ('line', '[SYSRAM] Add 3 4'))
            self.assertEqual(self.events.get(timeout=2), ('line', '-----'))
            path.write_text('-----\n')
            self.assertEqual(self.events.get(timeout=2)[0], 'reset')
            self.assertEqual(self.events.get(timeout=2), ('line', '-----'))
            replacement = Path(folder) / 'replacement'
            replacement.write_text('[VIDEO1] Add 5 6\n-----\n')
            replacement.replace(path)
            self.assertEqual(self.events.get(timeout=2)[0], 'reset')
            self.assertEqual(self.events.get(timeout=2), ('status', 'Receiving'))
            self.assertEqual(self.events.get(timeout=2), ('line', '[VIDEO1] Add 5 6'))
            self.assertEqual(self.events.get(timeout=2), ('line', '-----'))
            self.stop.set()
            self.worker.join(timeout=2)

    def test_invalid_uart_reports_error(self):
        receive('UART', '/no/such/uart', 9600, self.stop, lambda k, v: self.events.put((k, v)))
        self.assertEqual(self.events.get()[0], 'error')
        self.assertEqual(self.events.get()[0], 'done')


@unittest.skipUnless(os.environ.get('DISPLAY'), 'Needs a display (use xvfb-run)')
class GuiTests(unittest.TestCase):
    def test_live_receive_filters_and_disconnect(self):
        import tkinter as tk
        from live_gui import App
        root = tk.Tk()
        app = App(root)
        master, slave = pty.openpty()
        try:
            vmpeg = app.inputs['vmpeg']
            vmpeg.clear()
            vmpeg.accept('[SYSRAM] Add 20 40')
            vmpeg.accept('-----')
            source = app.inputs['mister']
            self.assertEqual(source.mode.get(), 'Follow log')
            self.assertEqual(source.target.get(), str(ROOT / 'log_mister'))
            source.mode.set('UART')
            source.target.set(os.ttyname(slave))
            source.baud.set('9600')
            source.connect()
            end = time.monotonic() + 3
            while not source.status.get().startswith('Receiving') and time.monotonic() < end:
                root.update()
                time.sleep(0.01)
            self.assertTrue(source.status.get().startswith('Receiving'))
            os.write(master, b'[SYSRAM] partial 999 999\r\n-----\r\n[SYSRAM] Add 10 20\r\n-----\r\n')
            while source.capture.cycles < 1 and time.monotonic() < end:
                root.update()
                time.sleep(0.01)
            self.assertEqual(source.capture.cycles, 1)
            self.assertNotIn(('SYSRAM', 'partial'), source.capture.data)
            app.regressions.set(True)
            app.phase.set('DA=1')
            app.refresh()
            items = app.table.get_children()
            self.assertEqual(len(items), 1)
            self.assertEqual(app.table.item(items[0], 'values')[-1], '-50.0%')
            self.assertEqual(app.table.item(items[0], 'tags'), ('negative',))
            app.phase.set('All')
            app.refresh()
            items = app.table.get_children()
            self.assertEqual(len(items), 1)
            values = app.table.item(items[0], 'values')
            self.assertEqual(values[2], 'DA=0+1')
            self.assertEqual(values[4], '60.00')
            self.assertEqual(values[8], '30.00')
            self.assertEqual(values[-1], '-50.0%')
            source.disconnect()
            source.worker.join(timeout=2)
            self.assertFalse(source.worker.is_alive())
        finally:
            app.close()
            os.close(master)
            os.close(slave)


if __name__ == '__main__':
    unittest.main()
