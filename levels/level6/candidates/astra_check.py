"""Run and independently simulate a level 6 candidate, saving valid outputs."""
import importlib.util
import sys
import time
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
NAME = sys.argv[1] if len(sys.argv) > 1 else 'astra'
spec = importlib.util.spec_from_file_location(NAME, Path(__file__).with_name(NAME + '.py'))
candidate = importlib.util.module_from_spec(spec)
spec.loader.exec_module(candidate)


def main():
    level = ROOT / 'levels/level6'
    output = level / 'runs' / NAME
    output.mkdir(parents=True, exist_ok=True)
    for path in sorted((level / 'data').glob('in_*.txt')):
        text = path.read_text()
        expected = path.with_name(path.name.replace('in_', 'out_', 1))
        if expected.exists():
            ok, message, score = candidate.check(text, expected.read_text())
            assert ok, message
            print('Official example: PASS, score=%d' % score, flush=True)
        start = time.process_time()
        answer = candidate.solve(text)
        elapsed = time.process_time() - start
        target = output / path.name.replace('in_', 'out_', 1)
        if target.exists():
            old = target.read_text()
            assert candidate.check(text, old)[0]
            old_blocks = re.split(r'\n\s*\n', old.strip())
            new_blocks = re.split(r'\n\s*\n', answer.strip())
            answer = '\n\n'.join(min((a, b), key=lambda s: len(s.splitlines()))
                                   for a, b in zip(old_blocks, new_blocks))
        ok, message, score = candidate.check(text, answer)
        assert ok, message
        assert elapsed < 300, elapsed
        target.write_text(answer + '\n')
        print('%s: PASS, score=%d, %.2fs CPU -> %s' %
              (path.name, score, elapsed, target.relative_to(ROOT)), flush=True)


if __name__ == '__main__':
    main()
