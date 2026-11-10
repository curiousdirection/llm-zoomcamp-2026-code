"""Append a course lesson to a module's lesson notebook.

Reads course/<module>/<NN>-*.md and appends it to <module>/lesson/lesson.ipynb in the
layout used by 02-vector-search/lesson/lesson.ipynb:

- module header cell (created with the notebook): title + list of every lesson
- per lesson: `---` + `# Lesson NN: Title` + Source/Video line + text before the first `##`
- one markdown cell per `##` section; each ```python block becomes its own (unrun) code cell,
  other fenced blocks (bash, toml, text...) stay inside the markdown
- relative links/images are rewritten to point into course/

Usage (from the repo root):
    python3 .claude/skills/add-lesson/build_notebook.py 04-evaluation 03 [04 ...]
"""

import argparse
import json
import os
import re
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..'))

KERNEL_METADATA = {
    'kernelspec': {'display_name': '.venv', 'language': 'python', 'name': 'python3'},
    'language_info': {
        'codemirror_mode': {'name': 'ipython', 'version': 3},
        'file_extension': '.py',
        'mimetype': 'text/x-python',
        'name': 'python',
        'nbconvert_exporter': 'python',
        'pygments_lexer': 'ipython3',
    },
}


def to_source(text):
    lines = text.split('\n')
    return [line + '\n' for line in lines[:-1]] + [lines[-1]]


def md(text):
    return {'cell_type': 'markdown', 'metadata': {}, 'source': to_source(text.strip())}


def code(text):
    return {'cell_type': 'code', 'execution_count': None, 'metadata': {}, 'outputs': [],
            'source': to_source(text.strip('\n'))}


def read_module(module):
    """Return (module title, [(num, title, filename)]) from course/<module>/module.yaml."""
    text = open(os.path.join(ROOT, 'course', module, 'module.yaml')).read()
    module_title = re.search(r'^title:\s*"?(.*?)"?\s*$', text, re.M).group(1)
    lessons = []
    for title, path in re.findall(r'title:\s*"?(.*?)"?\s*\n\s*path:\s*(\S+)', text):
        num = path.split('-', 1)[0]
        if path.endswith('-intro.md') and num == '01' and not title.lower().startswith('intro'):
            title = f'Introduction to {title}'  # matches the module 2/4 notebooks
        lessons.append((num, title, path))
    return module_title, lessons


def fix_links(text, course_rel, module):
    # ../other-module/... -> <course>/other-module/...
    text = re.sub(r'\]\(\.\./', f']({course_rel}/', text)
    # same-module relative paths (images/, code/, 02-foo.md) -> <course>/<module>/...
    return re.sub(r'\]\((?!https?:|mailto:|#|/|\.\./)([^)]+)\)',
                  lambda m: f']({course_rel}/{module}/{m.group(1)})', text)


def section_cells(part):
    """Prose -> markdown cells, each ```python block -> its own code cell."""
    cells = []
    for i, chunk in enumerate(re.split(r'^```python[ \t]*\n(.*?)^```[ \t]*\n?', part, flags=re.S | re.M)):
        if i % 2:
            cells.append(code(chunk))
        elif chunk.strip():
            cells.append(md(chunk))
    return cells


def lesson_cells(module, lesson, course_rel):
    num, title, filename = lesson
    raw = open(os.path.join(ROOT, 'course', module, filename)).read()
    front, body = '', raw
    if raw.startswith('---'):
        _, front, body = raw.split('---', 2)
    video = re.search(r'video_url:\s*"?([^"\s]+)"?', front)
    body = re.sub(r'^\s*# .*\n', '', body.lstrip('\n'), count=1)  # drop the H1, replaced by ours

    header = f'---\n\n# Lesson {num}: {title}\n\nSource: [`{filename}`]({course_rel}/{module}/{filename})'
    if video:
        header += f' · Video: [YouTube]({video.group(1)})'

    parts = re.split(r'\n(?=## )', fix_links(body, course_rel, module))
    cells = section_cells(parts[0])
    if cells and cells[0]['cell_type'] == 'markdown':
        cells[0] = md(header + '\n\n' + ''.join(cells[0]['source']))
    else:
        cells.insert(0, md(header))
    for part in parts[1:]:
        cells += section_cells(part)
    return cells


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('module', help='module folder name, e.g. 04-evaluation')
    parser.add_argument('lessons', nargs='+', help='lesson numbers, e.g. 03 04')
    parser.add_argument('--notebook', help='write elsewhere, e.g. for a dry run (default: <module>/lesson/lesson.ipynb)')
    args = parser.parse_args()

    module_title, lessons = read_module(args.module)
    by_num = {num: lesson for lesson in lessons for num in [lesson[0]]}
    nb_path = args.notebook or os.path.join(ROOT, args.module, 'lesson', 'lesson.ipynb')
    # links are relative to where lesson notebooks live (<module>/lesson/), even with --notebook
    course_rel = os.path.relpath(os.path.join(ROOT, 'course'), os.path.join(ROOT, args.module, 'lesson'))

    if os.path.exists(nb_path):
        nb = json.load(open(nb_path))
    else:
        nb = {'cells': [], 'metadata': KERNEL_METADATA, 'nbformat': 4, 'nbformat_minor': 5}
    nb['cells'] = [c for c in nb['cells'] if ''.join(c['source']).strip()]  # drop blank placeholder cells
    if not nb['cells']:
        listing = '\n'.join(f'- **Lesson {n}** - {t} (`{f}`)' for n, t, f in lessons)
        nb['cells'].append(md(
            f'# {module_title}\n\nLessons from [`course/{args.module}`]({course_rel}/{args.module}/), '
            f'one section per lesson:\n\n{listing}'))

    for num in args.lessons:
        num = num.zfill(2)
        if num not in by_num:
            sys.exit(f'Lesson {num} not in course/{args.module}/module.yaml')
        if any(f'# Lesson {num}:' in ''.join(c['source']) for c in nb['cells']):
            print(f'Lesson {num} already in notebook, skipping')
            continue
        cells = lesson_cells(args.module, by_num[num], course_rel)
        nb['cells'] += cells
        n_code = sum(c['cell_type'] == 'code' for c in cells)
        print(f'Lesson {num}: added {len(cells)} cells ({n_code} code)')

    os.makedirs(os.path.dirname(os.path.abspath(nb_path)), exist_ok=True)
    with open(nb_path, 'w') as fh:
        json.dump(nb, fh, indent=1, ensure_ascii=False)
        fh.write('\n')


if __name__ == '__main__':
    main()
