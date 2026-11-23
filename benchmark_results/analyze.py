"""Summarize the supplied logs using only the Python standard library."""
import csv
import re
import statistics
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = Path(__file__).resolve().parent
NAMES = ['getime', 'getpid', 'pt_coord', 'dm_wrpix', 'dr_circ', 'gc_ptn', 'dc_wrli', 'Multi', 'Add', 'Div', 'Copy VRAM', 'Copy SYSRAM', 'Copy SYSROM', 'Copy DVCROM']

class Capture:
    """Incrementally collect complete cycles; incomplete measurements stay pending."""

    def __init__(self):
        self.data = defaultdict(list)
        self.current = []
        self.cycles = 0

    def feed(self, line, latest_only=False):
        line = line.strip()
        match = re.fullmatch(r'(?:\[([^]]+)\]\s+)?(.+?)\s+(\d+)\s+(\d+)', line)
        if line == '-----' or (match and match[2] == 'FMA DCLK'):
            if not self.current:
                return False
            counts = Counter((location, name) for location, name, _, _ in self.current)
            if latest_only:
                locations = {location for location, _, _, _ in self.current}
                for key in list(self.data):
                    if key[0] in locations:
                        del self.data[key]
            occurrence = Counter()
            for location, name, a, b in self.current:
                occurrence[location, name] += 1
                label = f'{name} #{occurrence[location, name]}' if counts[location, name] > 1 else name
                self.data[location, label].append((a, b))
            self.current = []
            self.cycles += 1
            return True
        if match and (match[1] or match[2] in NAMES):
            self.current.append((match[1] or "unknown", match[2], int(match[3]), int(match[4])))
        return False

    def snapshot(self):
        return self.data, self.cycles, self.current


def parse(path):
    capture = Capture()
    for line in path.read_text(errors='replace').splitlines():
        capture.feed(line)
    return capture.snapshot()


def compare(parsed, combine_phases=False):
    labels = list(parsed['realcdi'][0])
    labels += [label for label in parsed['measure'][0] if label not in labels]
    rows = []
    for location, label in labels:
        for col in ([None] if combine_phases else range(2)):
            row = {'location': location, 'benchmark': label, 'phase': 'DA=0+1' if col is None else f'DA={col}'}
            for name, (data, _, _) in parsed.items():
                values = [sum(pair) if col is None else pair[col] for pair in data.get((location, label), [])]
                row[f'{name}_n'] = len(values)
                for key, func in [('mean', statistics.mean), ('variance', statistics.variance), ('sd', statistics.stdev), ('median', statistics.median), ('min', min), ('max', max)]:
                    row[f'{name}_{key}'] = func(values) if len(values) >= (2 if key in ('variance', 'sd') else 1) else None
            v, m = row['realcdi_mean'], row['measure_mean']
            row['mister_change_percent'] = (m / v - 1) * 100 if v and m is not None else None
            rows.append(row)
    return rows


def export(parsed, output=OUT):
    output = Path(output)
    output.mkdir(parents=True, exist_ok=True)
    rows = compare(parsed)
    with (output / 'comparison.csv').open('w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0]) if rows else ['location', 'benchmark', 'phase'], lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)

    report = ['# Real CD-i versus measurement', '',
        'Only terminated benchmark cycles are included: `-----` ends a cycle;', '',
        f"Real CD-i: {parsed['realcdi'][1]} complete cycles; {len(parsed['realcdi'][2])} trailing measurements excluded. MiSTer: {parsed['measure'][1]} complete cycles; {len(parsed['measure'][2])} trailing measurements excluded.", '',
        'Means are arithmetic means. Variance is sample variance (denominator n−1); SD is its square root. Variance has squared units. Change = 100 × (MiSTer mean / VMPEG mean − 1).', '',
        'DA=0 and DA=1 refer to the display-active register bit tested by src/main.c. Operation rows count loop iterations in each phase; positive changes mean more operations per phase. Phase duration differences also affect operation counts, so the percentages are not isolated CPU speedups.', '',
        'Benchmarks are matched by code location and label;', '',
        'MiSTer change: 🔴 **negative** · 🟢 positive · ⚪ zero. Negative changes indicate lower throughput per phase.', '']
    for phase in ['DA=0', 'DA=1']:
        report += [f'## {phase}', '', '| Location | Benchmark | VMPEG mean ± SD | VMPEG variance | MiSTer mean ± SD | MiSTer variance | MiSTer change |', '|---|---|---:|---:|---:|---:|---:|']
        for row in rows:
            if row['phase'] != phase:
                continue
            def fmt(name):
                if row[f'{name}_mean'] is None:
                    return '—', '—'
                sd = row[f'{name}_sd']
                variance = row[f'{name}_variance']
                return (f"{row[f'{name}_mean']:.2f} ± " + (f'{sd:.2f}' if sd is not None else '—'),
                        f'{variance:.3f}' if variance is not None else '—')
            v, vv = fmt('realcdi')
            m, mv = fmt('measure')
            change = row['mister_change_percent']
            delta = f'{change:+.1f}%' if change is not None else '—'
            if change is not None:
                if change < 0:
                    delta = f'🔴 **{delta}**'
                elif change > 0:
                    delta = f'🟢 {delta}'
                else:
                    delta = f'⚪ {delta}'
            report.append(f"| {row['location']} | {row['benchmark']} | {v} | {vv} | {m} | {mv} | {delta} |")
        report.append('')
    (output / 'comparison.md').write_text('\n'.join(report))
    return '\n'.join(report)


if __name__ == '__main__':
    parsed = {name: parse(ROOT / f'log_{name}') for name in ['realcdi', 'measure']}
    print(export(parsed))
