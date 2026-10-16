#!/usr/bin/env python3
"""功能单元规范的零依赖静态检查/索引/影响候选工具。

不运行测试；不保证通过静态引用推导完整代码影响关系。
运行环境为 Python 3.9+；目标项目语言不限。内置逻辑只使用标准库，不访问网络。
"""
from __future__ import annotations

import argparse
import ast
from collections import defaultdict, deque
from dataclasses import dataclass, field
import json
import math
from pathlib import Path
import re
import subprocess
import sys
from typing import Dict, List, Optional, Tuple

F_RE = re.compile(r"^F-[A-Z][A-Z0-9]*-\d{3,}$")
S_RE = re.compile(r"^S-\d{2,}$")
HEADING_F = re.compile(r"^##\s+(F-[A-Z][A-Z0-9]*-\d{3,})\s+(.+?)\s*$")
HEADING = re.compile(r"^(#{1,6})\s+(.+?)\s*$")
CODE_REF = re.compile(r"^([^:]+)::(.+)$")
PY_EXTS = {".py"}
# 功能关系目标的分隔符；测试定位符允许转义逗号，由 split_test_refs 单独处理。
SEP_RE = re.compile(r"[,，]")


@dataclass
class Scenario:
    sid: str
    kind: str
    expected: str
    tests: List[str]
    line: int


@dataclass
class Feature:
    fid: str
    name: str
    document: str
    line: int
    description: str = ""
    relations: List[Tuple[str, str]] = field(default_factory=list)
    implementations: List[Tuple[str, str]] = field(default_factory=list)
    scenarios: List[Scenario] = field(default_factory=list)
    # 模块取自文档一级标题；状态沿用功能标题后缀。创建提交由作者在实现提交后登记。
    module: str = ""
    status: str = "有效"
    created_commit: str = ""


@dataclass
class Issue:
    severity: str
    location: str
    message: str

    def as_json(self) -> dict:
        return vars(self)


@dataclass
class SymbolChecker:
    """接口职责：通过 JSON 协议调用项目提供的语言工具。

    调用方：引用校验流程；未配置时继续使用内置检查。
    实现要求：命令按参数数组执行，以项目根目录为工作目录；失败必须报告错误。
    """

    command: List[str]
    timeout: float = 30.0

    def check(self, project: Path, path: str, symbol: str, is_test: bool) -> Tuple[Optional[bool], str]:
        """函数职责：查询一个实现或测试定位符是否存在。

        输入说明：路径已通过项目边界及文件存在性校验；符号保留项目原生写法。
        输出说明：found 返回 True，missing 或协议失败返回 False，unknown 返回 None。
        实现思路：通过标准输入发送 JSON，限时读取标准输出，严格校验状态字段。
        """
        request = {"path": path, "symbol": symbol, "kind": "test" if is_test else "implementation"}
        try:
            # 符号只作为 JSON 数据传入；参数数组不经 shell 展开，项目工具自行解释原生名称。
            result = subprocess.run(
                self.command, cwd=project, input=json.dumps(request, ensure_ascii=False),
                text=True, encoding="utf-8", capture_output=True, timeout=self.timeout, check=False,
            )
        except subprocess.TimeoutExpired:
            return False, f"符号检查器超时（{self.timeout:g} 秒）：{path}::{symbol}"
        except (OSError, UnicodeError, ValueError) as exc:
            return False, f"无法执行符号检查器：{exc}"
        if result.returncode:
            return False, f"符号检查器执行失败（退出码 {result.returncode}）：{path}::{symbol}"
        try:
            response = json.loads(result.stdout)
        except ValueError:
            return False, "符号检查器必须输出一个 JSON 对象"
        if not isinstance(response, dict) or response.get("status") not in ("found", "missing", "unknown"):
            return False, "符号检查器 status 必须是 found、missing 或 unknown"
        message = response.get("message", "")
        if not isinstance(message, str):
            return False, "符号检查器 message 必须是字符串"
        status = response["status"]
        if status == "found":
            return True, ""
        if status == "missing":
            return False, message or f"未发现符号：{path}::{symbol}"
        return None, message or f"检查器无法确认符号：{path}::{symbol}"


def split_test_refs(text: str) -> List[str]:
    """函数职责：拆分测试引用列表并还原定位符中的转义逗号。

    输入说明：多引用以半角或全角逗号分隔；定位符内的逗号写为 \\, 或 \\，。
    输出说明：返回保留原生名称和命名空间分隔符的完整引用；空值和 - 返回空列表。
    实现思路：仅在未转义逗号处分隔，再还原逗号转义和 Markdown 代码标记。
    """
    if text.strip() in ("", "-"):
        return []
    return [re.sub(r"\\([,，])", r"\1", part.strip().strip("`").strip())
            for part in re.split(r"(?<!\\)[,，]", text) if part.strip()]


def strip_code_fences(lines: List[str]) -> List[str]:
    """保留行号；忽略代码围栏内展示性的 F-ID/表格。"""
    inside, marker = False, ""
    result = []
    for line in lines:
        stripped = line.strip()
        m = re.match(r"^(`{3,}|~{3,})", stripped)
        if m and not inside:
            inside, marker = True, m.group(1)[0]
            result.append("")
            continue
        if m and inside and m.group(1)[0] == marker:
            inside = False
            result.append("")
            continue
        result.append("" if inside else line)
    return result


def clean_cell(cell: str) -> str:
    return cell.strip().strip("`").strip()


def table_parse(lines: List[Tuple[int, str]], origin: str, issues: List[Issue]):
    """解析简单 Markdown 表格，每个标题段允许恰好一张表。"""
    visible = [(no, s.strip()) for no, s in lines if s.strip() and not s.lstrip().startswith("<!--")]
    # 先保护 Markdown 转义竖线，再拆分并还原，避免原生定位符被误当作表格分隔。
    rows = [(no, [clean_cell(x.replace("\x00", "|")) for x in s.replace(r"\|", "\x00").strip("|").split("|")])
            for no, s in visible if s.startswith("|") and s.endswith("|")]
    if not rows:
        return None, []
    header = rows[0][1]
    data = []
    for no, cells in rows[1:]:
        if all(re.fullmatch(r":?-{3,}:?", v.strip()) for v in cells):
            continue
        if len(cells) != len(header):
            issues.append(Issue("error", f"{origin}:{no}", f"表格列数 {len(cells)} 与表头 {len(header)} 不一致"))
            continue
        data.append((no, cells))
    return header, data


def parse_sections(lines: List[str], first: int, last: int, feat: Feature, issues: List[Issue]) -> None:
    cur_name = None
    cur_start = None
    sections: List[Tuple[str, int, int]] = []
    prologue = []
    commit_seen = False
    for i in range(first + 1, last):
        line = lines[i]
        m = HEADING.match(line)
        if m and len(m.group(1)) == 3:
            if cur_name is not None and cur_start is not None:
                sections.append((cur_name, cur_start, i))
            cur_name, cur_start = m.group(2).strip(), i + 1
        elif cur_name is None and line.strip() and not line.startswith(">") and not line.startswith("<!--"):
            if line.strip().startswith("创建提交："):
                value = clean_cell(line.strip().split("：", 1)[1])
                if commit_seen:
                    issues.append(Issue("error", f"{feat.document}:{i+1}", "创建提交重复登记"))
                commit_seen = True
                if value not in ("", "-") and not re.fullmatch(r"[0-9a-fA-F]{7,40}", value):
                    issues.append(Issue("error", f"{feat.document}:{i+1}", "创建提交应为 7 到 40 位十六进制 hash；未登记时填 -"))
                else:
                    feat.created_commit = "" if value in ("", "-") else value.lower()
            else:
                prologue.append(line.strip())
    if cur_name is not None and cur_start is not None:
        sections.append((cur_name, cur_start, last))
    feat.description = " ".join(prologue).strip()
    if not feat.description:
        issues.append(Issue("warning", f"{feat.document}:{feat.line}", "功能没有简短的语义描述"))
    seen = set()
    expected_headers = {
        "功能关系": ["类型", "功能编号"],
        "实现": ["角色", "代码符号"],
        "行为场景": ["编号", "类型", "场景与预期", "测试"],
    }
    for title, s, e in sections:
        if title not in expected_headers:
            continue
        loc = f"{feat.document}:{s}"
        if title in seen:
            issues.append(Issue("error", loc, f"{feat.fid} 重复出现 {title} 章节"))
        seen.add(title)
        table, rows = table_parse([(i + 1, lines[i]) for i in range(s, e)], loc, issues)
        if table is None:
            issues.append(Issue("warning", loc, f"{title} 章节没有表格，空章节建议删除"))
            continue
        if table != expected_headers[title]:
            issues.append(Issue("error", loc, f"{title} 表头应为 {' | '.join(expected_headers[title])}"))
            continue
        if title == "功能关系":
            for no, (kind, target) in rows:
                if kind not in ("依赖", "触发"):
                    issues.append(Issue("error", f"{feat.document}:{no}", "功能关系类型只能是依赖或触发"))
                # 同一格允许多个目标 F-ID，逐个校验后各自登记为一条关系。
                for item in (part.strip() for part in SEP_RE.split(target)):
                    if not F_RE.fullmatch(item):
                        issues.append(Issue("error", f"{feat.document}:{no}", "功能关系目标格必须且只能包含 F-ID，多个 F-ID 用逗号分隔"))
                        continue
                    feat.relations.append((kind, item))
        elif title == "实现":
            for no, (role, ref) in rows:
                if role not in ("主入口", "关键实现"):
                    issues.append(Issue("warning", f"{feat.document}:{no}", "实现角色建议使用主入口或关键实现"))
                feat.implementations.append((role, ref))
        else:
            ids = set()
            for no, (sid, kind, expected, tests_text) in rows:
                if not S_RE.fullmatch(sid):
                    issues.append(Issue("error", f"{feat.document}:{no}", f"场景编号 {sid!r} 应为 S-01 等格式"))
                if sid in ids:
                    issues.append(Issue("error", f"{feat.document}:{no}", f"重复场景编号 {sid}"))
                ids.add(sid)
                if not expected or expected == "-":
                    issues.append(Issue("error", f"{feat.document}:{no}", "场景与预期不能留空"))
                tests = split_test_refs(tests_text)
                feat.scenarios.append(Scenario(sid, kind, expected, tests, no))


def scan(project: Path) -> Tuple[List[Feature], List[Issue]]:
    features_dir = project / "features"
    issues: List[Issue] = []
    if not features_dir.is_dir():
        return [], [Issue("error", "features/", "未找到 features/ 目录；先按模板建立功能目录")]
    documents = sorted(p for p in features_dir.rglob("*.md") if p.name.lower() != "readme.md" and not any(x.startswith(".") for x in p.relative_to(features_dir).parts))
    if not documents:
        issues.append(Issue("warning", "features/", "未发现模块功能文档"))
    features = []
    for doc in documents:
        relative = doc.relative_to(project).as_posix()
        try:
            lines = strip_code_fences(doc.read_text(encoding="utf-8-sig").splitlines())
        except (OSError, UnicodeError) as exc:
            issues.append(Issue("error", relative, f"无法读取文件：{exc}"))
            continue
        # 删除线只影响标题显示，废弃功能仍须保留 ID 和状态供视图定位。
        lines = [line.replace("~~", "") if line.startswith(("## ", "~~## ")) else line for line in lines]
        module = next((line[2:].strip() for line in lines if line.startswith("# ")), doc.stem)
        blocks = []
        for i, line in enumerate(lines):
            m = HEADING_F.match(line)
            if m:
                blocks.append((i, m.group(1), m.group(2)))
            elif line.startswith("## F-"):
                issues.append(Issue("error", f"{relative}:{i+1}", "功能标题格式不正确，预期 ## F-MOD-001 名称"))
        for n, (start, fid, name) in enumerate(blocks):
            end = blocks[n + 1][0] if n + 1 < len(blocks) else len(lines)
            # 功能块到下一个二级标题（可含模块共用约束）为止。
            for i in range(start + 1, end):
                if lines[i].startswith("## "):
                    end = i
                    break
            feat = Feature(fid, name, relative, start + 1)
            feat.module = module
            status = re.search(r"\s+(草案|有效|已废弃)(?:[（(].*)?$", name)
            if status:
                feat.status = status.group(1)
                feat.name = name[:status.start()].strip()
            parse_sections(lines, start, end, feat, issues)
            features.append(feat)
    return features, issues


def repo_file(project: Path, ref: str) -> Optional[Path]:
    """不允许绝对路径和相对逃逸；兼容 Windows 风格分隔符。"""
    p = Path(ref.replace("\\", "/"))
    if p.is_absolute() or any(part in ("..", ".") for part in p.parts):
        return None
    resolved = (project / p).resolve()
    try:
        resolved.relative_to(project.resolve())
    except ValueError:
        return None
    return resolved


def python_symbol_exists(path: Path, qualified: str) -> Tuple[Optional[bool], str]:
    try:
        tree = ast.parse(path.read_text(encoding="utf-8-sig"), filename=str(path))
    except (SyntaxError, OSError, UnicodeError) as exc:
        return None, f"无法静态解析 Python 文件：{exc}"
    fields = qualified.replace("::", ".").split(".")
    # 特定参数化实例收敛为测试函数，具体参数实例不做静态验证。
    if fields:
        fields[-1] = re.sub(r"\[.*\]$", "", fields[-1])
    current = tree.body
    for name in fields:
        found = next((n for n in current if isinstance(n, (ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)) and n.name == name), None)
        if found is None:
            return False, f"未发现 Python 符号 {qualified}"
        current = getattr(found, "body", [])
    return True, ""


def check_ref(project: Path, ref: str, context: str, issues: List[Issue], is_test: bool,
              checker: Optional[SymbolChecker] = None) -> None:
    """先校验通用路径和非空定位符；外部检查器优先，否则按内置能力报告验证边界。"""
    m = CODE_REF.fullmatch(ref)
    if not m:
        issues.append(Issue("error", context, f"引用应为 项目相对路径::符号，当前为 {ref}"))
        return
    path_str, symbol = m.groups()
    path = repo_file(project, path_str)
    if path is None:
        issues.append(Issue("error", context, f"无效或越界的引用路径：{path_str}"))
        return
    if not path.is_file():
        issues.append(Issue("error", context, f"引用文件不存在：{path_str}"))
        return
    if not symbol.strip():
        issues.append(Issue("error", context, f"空符号引用：{ref}"))
        return
    if checker is not None:
        ok, reason = checker.check(project, path.relative_to(project.resolve()).as_posix(), symbol, is_test)
        if ok is not True:
            issues.append(Issue("error" if ok is False else "warning", context, reason))
    elif path.suffix.lower() in PY_EXTS:
        # pytest 使用 Class::fn；普通实现为 Class.method。
        ok, reason = python_symbol_exists(path, symbol)
        if ok is False:
            issues.append(Issue("error", context, reason))
        elif ok is None:
            issues.append(Issue("warning", context, reason))
        elif "[" in symbol:
            issues.append(Issue("warning", context, f"仅确认了参数化测试函数，未静态确认具体参数实例：{ref}"))
    else:
        issues.append(Issue("warning", context, f"仅检查了文件存在，未确认符号：{ref}；可通过 --symbol-checker 接入项目工具"))


def validate(project: Path, features: List[Feature], parse_issues: List[Issue],
             checker: Optional[SymbolChecker] = None) -> List[Issue]:
    issues = list(parse_issues)
    first_defs = {}
    all_ids = {f.fid for f in features}
    for feature in features:
        if feature.fid in first_defs:
            issues.append(Issue("error", f"{feature.document}:{feature.line}", f"重复功能 ID {feature.fid}，首次定义：{first_defs[feature.fid]}"))
        first_defs.setdefault(feature.fid, f"{feature.document}:{feature.line}")
        if feature.status == "已废弃":
            if feature.implementations or feature.relations or any(s.tests for s in feature.scenarios):
                issues.append(Issue("error", f"{feature.document}:{feature.line}", "已废弃功能应清空实现、功能关系和测试引用"))
            continue
        seen_rel = set()
        for kind, target in feature.relations:
            if (kind, target) in seen_rel:
                issues.append(Issue("error", f"{feature.document}:{feature.line}", f"重复关系：{kind} {target}"))
            seen_rel.add((kind, target))
            if target == feature.fid:
                issues.append(Issue("error", f"{feature.document}:{feature.line}", "功能不能依赖或触发自己"))
            if F_RE.fullmatch(target) and target not in all_ids:
                issues.append(Issue("error", f"{feature.document}:{feature.line}", f"关系目标未定义：{target}"))
            elif any(f.fid == target and f.status == "已废弃" for f in features):
                issues.append(Issue("error", f"{feature.document}:{feature.line}", f"关系目标已废弃：{target}"))
        if not feature.implementations:
            issues.append(Issue("warning", f"{feature.document}:{feature.line}", "未指定实现位置（草案/未实现可以接受）"))
        for role, ref in feature.implementations:
            check_ref(project, ref, f"{feature.document}:{feature.line} [{feature.fid} 实现 {role}]", issues, False, checker)
        if not feature.scenarios:
            issues.append(Issue("warning", f"{feature.document}:{feature.line}", "尚无行为场景；简单功能可接受"))
        for s in feature.scenarios:
            if not s.tests:
                issues.append(Issue("warning", f"{feature.document}:{s.line}", f"{feature.fid}/{s.sid} 暂无自动化测试引用"))
            for ref in s.tests:
                check_ref(project, ref, f"{feature.document}:{s.line} [{feature.fid}/{s.sid}]", issues, True, checker)
    return issues


def to_index(features: List[Feature]):
    by_impl, by_test = defaultdict(list), defaultdict(list)
    relations = []
    for f in features:
        for role, ref in f.implementations:
            by_impl[ref].append({"feature": f.fid, "role": role})
        for s in f.scenarios:
            for ref in s.tests:
                by_test[ref].append({"feature": f.fid, "scenario": s.sid})
        for kind, target in f.relations:
            relations.append({"source": f.fid, "type": kind, "target": target})
    return {
        "features": [{
            "id": f.fid, "name": f.name, "document": f.document, "line": f.line,
            "module": f.module, "status": f.status, "description": f.description,
            "created_commit": f.created_commit,
            "implementations": [{"role": role, "symbol": ref} for role, ref in f.implementations],
            "scenarios": [{"id": s.sid, "type": s.kind, "expected": s.expected, "tests": s.tests} for s in f.scenarios],
        } for f in features],
        "implementations": dict(sorted(by_impl.items())),
        "tests": dict(sorted(by_test.items())),
        "relations": relations,
    }


def coverage(features: List[Feature]) -> dict:
    # 统计当前功能；废弃条目保留在索引中，但不构成当前验证缺口。
    features = [f for f in features if f.status != "已废弃"]
    total = sum(len(f.scenarios) for f in features)
    linked = sum(bool(s.tests) for f in features for s in f.scenarios)
    return {
        "features": len(features),
        "scenarios": total,
        "scenarios_with_test_reference": linked,
        "scenarios_without_test_reference": total - linked,
        "structural_link_ratio": round(linked / total, 4) if total else None,
        "warning": "关联率不是测试执行通过率或行为充分性证明",
    }


def git_changed_files(project: Path, base: str) -> List[str]:
    p = subprocess.run(["git", "-C", str(project), "diff", "--name-only", base, "--"], text=True, capture_output=True, check=False)
    if p.returncode:
        raise RuntimeError(f"git diff 失败：{p.stderr.strip()}")
    return [s.strip().replace("\\", "/") for s in p.stdout.splitlines() if s.strip()]


def impact(features: List[Feature], changed_files: List[str], depth: int = 1) -> dict:
    changed = {x.replace("\\", "/").removeprefix("./") for x in changed_files}
    direct = defaultdict(set)
    for f in features:
        if f.document in changed:
            direct[f.fid].add("功能规格文件发生变化")
        for _, ref in f.implementations:
            m = CODE_REF.match(ref)
            if m and m.group(1).replace("\\", "/") in changed:
                direct[f.fid].add("关联的实现文件发生变化（文件级候选）")
        for s in f.scenarios:
            for ref in s.tests:
                m = CODE_REF.match(ref)
                if m and m.group(1).replace("\\", "/") in changed:
                    direct[f.fid].add(f"关联测试文件发生变化（{s.sid}）")
    graph = defaultdict(set)
    # 依赖 A->B：B 变化可能影响 A；触发 A->B：A 改变可能影响 B。
    for f in features:
        for kind, target in f.relations:
            if kind == "依赖":
                graph[target].add(f.fid)
            elif kind == "触发":
                graph[f.fid].add(target)
    visited = set(direct)
    frontier = deque((fid, 0) for fid in direct)
    indirect = defaultdict(set)
    while frontier:
        fid, dist = frontier.popleft()
        if dist >= depth:
            continue
        for neighbor in sorted(graph[fid]):
            if neighbor not in visited:
                visited.add(neighbor)
                indirect[neighbor].add(f"功能关系影响候选（来自 {fid}，{dist+1} 跳）")
                frontier.append((neighbor, dist + 1))
    tests = defaultdict(list)
    for f in features:
        if f.fid in visited:
            for s in f.scenarios:
                for ref in s.tests:
                    tests[ref].append({"feature": f.fid, "scenario": s.sid})
    return {
        "changed_files": sorted(changed),
        "direct_candidates": [{"feature": fid, "reasons": sorted(v)} for fid, v in sorted(direct.items())],
        "related_candidates": [{"feature": fid, "reasons": sorted(v)} for fid, v in sorted(indirect.items())],
        "tests_for_review": dict(sorted(tests.items())),
        "limitation": "仅基于改动文件和显式功能关系；候选测试不是完整回归范围，公共未登记符号/动态依赖可能漏检",
    }


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="功能单元驱动开发：检查、反向索引、关联统计和变更影响候选")
    sub = parser.add_subparsers(dest="command", required=True)
    for cmd in ("validate", "index", "coverage", "impact"):
        p = sub.add_parser(cmd)
        p.add_argument("--project", required=True, type=Path, help="项目根目录（其中包含 features/）")
        if cmd == "validate":
            p.add_argument("--json", action="store_true", help="以 JSON 格式输出检查报告")
            p.add_argument("--symbol-checker-timeout", type=float, default=30.0, help="每次符号查询的超时秒数（默认 30）")
            p.add_argument("--symbol-checker", nargs=argparse.REMAINDER,
                           help="项目符号检查命令及参数，必须置于最后；通过 stdin/stdout 交换 UTF-8 JSON")
        if cmd == "impact":
            p.add_argument("--changed", action="append", default=[], help="改动的项目相对路径，可重复")
            p.add_argument("--git-base", default=None, help="使用 git diff BASE 列出相对 BASE 变化的文件")
            p.add_argument("--depth", type=int, default=1, help="功能关系扩展层数（默认 1）")
    args = parser.parse_args(argv)
    checker = None
    if args.command == "validate":
        if not math.isfinite(args.symbol_checker_timeout) or args.symbol_checker_timeout <= 0:
            parser.error("--symbol-checker-timeout 必须是有限正数")
        if args.symbol_checker is not None:
            if not args.symbol_checker:
                parser.error("--symbol-checker 后必须提供命令")
            checker = SymbolChecker(args.symbol_checker, args.symbol_checker_timeout)
    project = args.project.resolve()
    features, initial = scan(project)
    if any(x.severity == "error" for x in initial) and not features:
        for issue in initial:
            print(f"[错误] {issue.location}: {issue.message}", file=sys.stderr)
        return 1
    if args.command == "validate":
        issues = validate(project, features, initial, checker)
        if args.json:
            print(json.dumps({"features": len(features), "errors": sum(x.severity == "error" for x in issues), "warnings": sum(x.severity == "warning" for x in issues), "issues": [x.as_json() for x in issues]}, ensure_ascii=False, indent=2))
        else:
            for issue in issues:
                print(f"[{'错误' if issue.severity == 'error' else '提示'}] {issue.location}: {issue.message}")
            print(f"检查完成：{len(features)} 个功能，{sum(x.severity == 'error' for x in issues)} 个错误，{sum(x.severity == 'warning' for x in issues)} 个提示")
        return int(any(x.severity == "error" for x in issues))
    if any(x.severity == "error" for x in initial):
        for issue in initial:
            if issue.severity == "error":
                print(f"[错误] {issue.location}: {issue.message}", file=sys.stderr)
        return 1
    if args.command == "index":
        output = to_index(features)
    elif args.command == "coverage":
        output = coverage(features)
    else:
        if args.depth < 0:
            parser.error("--depth 不能小于 0")
        changed = list(args.changed)
        if args.git_base:
            try:
                changed += git_changed_files(project, args.git_base)
            except (RuntimeError, FileNotFoundError) as exc:
                parser.error(str(exc))
        if not changed:
            parser.error("impact 至少需要 --changed 或 --git-base")
        output = impact(features, changed, args.depth)
    print(json.dumps(output, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
