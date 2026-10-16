"""自动登记与校验测试处置表中「创建提交」列的脚本。

用法：python sync-commits.py [项目根目录] [--check]
默认模式：把 TEST-DISPOSITION.md 中「创建提交」为 — 的测试行，按测试名与文件路径
用 git 定位首次引入提交并原位回填 7 位短 hash；无法定位的行保持 — 并在报告中给出
原因与该文件最近的提交历史，供人工按 SKILL.md「提交关联」的规则复核。
--check：不修改文件，校验表中已登记的 hash 是否指向真实提交、测试名是否真的
出现在该提交的文件内容中（测试后来更名也会命中此告警）；发现问题退出码为 1。

定位顺序（与 SKILL.md「提交关联」一致）：
1. git log --reverse -S '<测试名>' -- <文件>，候选从旧到新逐个用「测试名按词边界出现在
   该提交的文件内容中」验证，取最早命中——测试后加进既有文件或随文件新增都由此命中；
2. 不限文件的 -S 测试名（测试随文件迁移时兜底，未做内容核对）；
3. --diff-filter=A --follow 取文件首次入库提交（测试名与历史不一致时兜底，标注文件级）。
"""

import os
import re
import subprocess
import sys

TEST_DOC = 'TEST-DISPOSITION.md'


def git(root, *args):
    """运行 git 命令，返回 stdout 文本；失败（非 0 退出、git 缺失、超时）返回 None"""
    try:
        proc = subprocess.run(['git', *args], cwd=root, stdout=subprocess.PIPE,
                              stderr=subprocess.DEVNULL, timeout=30)
    except (OSError, subprocess.TimeoutExpired):
        return None
    if proc.returncode != 0:
        return None
    return proc.stdout.decode('utf-8', 'replace')


def split_cells(line):
    """与视图 splitRow 同规则：按未转义的 | 切分一行表格行，去掉首尾管道"""
    prepared = line.strip().replace('\\|', '\x00')
    return [c.replace('\x00', '|').strip() for c in prepared.strip('|').split('|')]


def is_separator(line):
    cells = split_cells(line)
    return bool(cells) and all(re.fullmatch(r':?-{2,}:?', c) for c in cells)


def pipe_positions(line):
    """行内未转义 | 的下标（含行首行尾的管道）"""
    pos, esc = [], False
    for i, ch in enumerate(line):
        if esc:
            esc = False
        elif ch == '\\':
            esc = True
        elif ch == '|':
            pos.append(i)
    return pos


def replace_cell(line, col_index, value):
    """原位替换第 col_index 个单元格，其余字符逐字节保留，避免重排整行的对齐空格"""
    pos = pipe_positions(line)
    a, b = pos[col_index], pos[col_index + 1]
    return line[:a + 1] + f' {value} ' + line[b:]


def find_tables(lines, columns):
    """扫描文档里含全部指定列的管道表，返回 [(列名→下标, 数据行行号列表)]"""
    tables = []
    i = 0
    while i < len(lines):
        if lines[i].lstrip().startswith('|'):
            cells = split_cells(lines[i])
            if all(c in cells for c in columns) and i + 1 < len(lines) and is_separator(lines[i + 1]):
                col_map = {c: cells.index(c) for c in columns}
                rows = []
                j = i + 2
                while j < len(lines) and lines[j].lstrip().startswith('|'):
                    rows.append(j)
                    j += 1
                tables.append((col_map, rows))
                i = j
                continue
        i += 1
    return tables


def boundary_pattern(name):
    """测试名的词边界匹配，避免 test_foo 命中 test_foo_bar 一类子串"""
    return re.compile('(?<![A-Za-z0-9_])' + re.escape(name) + '(?![A-Za-z0-9_])')


def find_origin(root, name, file):
    """定位首次引入该测试的提交，返回 (hash, 来源说明) 或 (None, None)"""
    file = file.replace('\\', '/')
    out = git(root, 'log', '--reverse', '--format=%h', f'-S{name}', '--', file)
    if out is not None:
        pat = boundary_pattern(name)
        for h in out.split():
            content = git(root, 'show', f'{h}:{file}')
            if content is not None and pat.search(content):
                return h[:7], '引入提交'
    out = git(root, 'log', '--reverse', '--format=%h', f'-S{name}')
    if out:
        return out.split()[0][:7], '按测试名定位（不限文件，未做内容核对）'
    out = git(root, 'log', '--reverse', '--format=%h', '--diff-filter=A', '--follow', '--', file)
    if out:
        return out.split()[0][:7], '文件首次入库'
    return None, None


def fill(root):
    path = os.path.join(root, TEST_DOC)
    if not os.path.exists(path):
        print(f'错误：找不到 {path}，测试处置表默认建在项目根目录')
        return 1
    with open(path, encoding='utf-8', newline='') as f:
        lines = f.readlines()
    tables = find_tables(lines, ['ID', '测试', '文件', '创建提交'])
    if not tables:
        print(f'错误：{TEST_DOC} 中没有含「ID/测试/文件/创建提交」列的表格，请按模板补齐列')
        return 1
    filled, skipped, unresolved = [], [], []
    for col_map, row_idx in tables:
        for idx in row_idx:
            line = lines[idx]
            cells = split_cells(line)
            tid = cells[col_map['ID']]
            cur = cells[col_map['创建提交']]
            if cur not in ('—', '-', ''):
                skipped.append(tid)
                continue
            name, file = cells[col_map['测试']], cells[col_map['文件']]
            if not name or not file:
                unresolved.append((tid, '测试名或文件列为空'))
                continue
            norm = file.replace('\\', '/')
            in_history = git(root, 'log', '-1', '--format=%h', '--', norm)
            if in_history is not None and not in_history.strip():
                state = '尚未提交' if os.path.exists(os.path.join(root, norm)) else '路径在历史与工作区中都不存在，请检查文件列'
                unresolved.append((tid, state))
                continue
            commit, source = find_origin(root, name, norm)
            if commit:
                if len(pipe_positions(line)) > col_map['创建提交'] + 1:
                    lines[idx] = replace_cell(line, col_map['创建提交'], commit)
                    filled.append(f'{tid} {name} → {commit}（{source}）')
                else:
                    unresolved.append((tid, '行内单元格数量与表头不一致'))
            else:
                history = git(root, 'log', '--oneline', '-5', '--follow', '--', norm) or '（无历史）'
                unresolved.append((tid, '未能定位，文件最近提交供参考：' + ' / '.join(history.split())))
    with open(path, 'w', encoding='utf-8', newline='') as f:
        f.writelines(lines)
    print(f'{TEST_DOC} 创建提交登记：回填 {len(filled)} 行；已有 hash 未改动 {len(skipped)} 行；未登记 {len(unresolved)} 行')
    for item in filled:
        print(f'  {item}')
    for tid, reason in unresolved:
        print(f'  {tid} 未登记：{reason}')
    return 0


def check(root):
    problems = 0
    path = os.path.join(root, TEST_DOC)
    if not os.path.exists(path):
        print(f'校验：找不到 {TEST_DOC}，跳过')
        return 0
    with open(path, encoding='utf-8', newline='') as f:
        lines = f.readlines()
    tables = find_tables(lines, ['ID', '创建提交', '测试', '文件'])
    if not tables:
        print(f'{TEST_DOC} 校验：没有含所需列的表格，跳过')
        return 0
    print(f'{TEST_DOC} 校验：')
    for col_map, row_idx in tables:
        for idx in row_idx:
            cells = split_cells(lines[idx])
            tid = cells[col_map['ID']]
            cur = cells[col_map['创建提交']]
            if cur in ('—', '-', ''):
                print(f'  {tid} 未登记创建提交')
                continue
            if git(root, 'rev-parse', '--verify', '--quiet', f'{cur}^{{commit}}') is None:
                print(f'  {tid} hash {cur} 无效：不是仓库中的提交')
                problems += 1
                continue
            name = cells[col_map['测试']]
            norm = cells[col_map['文件']].replace('\\', '/')
            content = git(root, 'show', f'{cur}:{norm}')
            if content is None:
                print(f'  {tid} hash {cur} 可疑：文件 {norm} 在该提交中不存在')
                problems += 1
            elif not boundary_pattern(name).search(content):
                print(f'  {tid} hash {cur} 可疑：测试名未出现在该提交的 {norm} 中（测试可能后来更名）')
                problems += 1
            else:
                print(f'  {tid} hash {cur} ✓')
    if problems:
        print(f'校验发现问题 {problems} 处，请复核')
        return 1
    print('校验通过')
    return 0


def main():
    argv = sys.argv[1:]
    check_only = '--check' in argv
    argv = [a for a in argv if not a.startswith('--')]
    root = os.path.abspath(argv[0]) if argv else os.getcwd()
    if git(root, 'rev-parse', '--git-dir') is None:
        print(f'错误：{root} 不是 git 仓库（或 git 不可用）')
        return 1
    return check(root) if check_only else fill(root)


if __name__ == '__main__':
    sys.exit(main())
