#!/usr/bin/env python3
"""Build a dependency-free, single-file copy of the MiMo reading guide."""
from __future__ import annotations
import argparse
from pathlib import Path


def build(output: Path) -> Path:
    root = Path(__file__).resolve().parent
    html = (root / 'index.html').read_text(encoding='utf-8')
    replacements = {
        '<link rel="stylesheet" href="guide.css">': '<style>\n' + (root / 'guide.css').read_text(encoding='utf-8').rstrip('\n') + '\n</style>',
        '<script src="guide.js"></script>': '<script>\n' + (root / 'guide.js').read_text(encoding='utf-8').rstrip('\n') + '\n</script>',
    }
    for marker, content in replacements.items():
        if html.count(marker) != 1:
            raise ValueError(f'Expected exactly one source marker: {marker}')
        html = html.replace(marker, content)
    if output.resolve() in {root / 'index.html', root / 'guide.css', root / 'guide.js'}:
        raise ValueError('Output must not overwrite the maintained source files.')
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(html, encoding='utf-8')
    return output.resolve()


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=Path(__file__).with_name('MiMo_RL_Interactive_Guide.html'))
    args = parser.parse_args()
    try:
        print(build(args.output))
    except (OSError, ValueError) as exc:
        parser.exit(1, f'Build failed: {exc}\n')
