"""使用 Python 标准库运行：python -m unittest discover -s scripts -p 'test_*.py'。"""
import contextlib
import io
import json
from pathlib import Path
import tempfile
import unittest
import sys
from featurectl import scan, validate, to_index, coverage, impact, main


class TestFeaturectl(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        for d in ("features", "src", "tests"):
            (self.root / d).mkdir()
        (self.root / "src" / "inventory.py").write_text(
            "class Inventory:\n    def consume(self, qty):\n        return qty\n",
            encoding="utf-8",
        )
        (self.root / "src" / "cooking.py").write_text(
            "class Cooking:\n    def cook(self):\n        return 1\n", encoding="utf-8"
        )
        (self.root / "tests" / "test_inventory.py").write_text(
            "def test_consume_normal():\n    assert True\n", encoding="utf-8"
        )
        (self.root / "tests" / "test_cooking.py").write_text(
            "def test_cook_success():\n    assert True\n", encoding="utf-8"
        )
        (self.root / "features" / "inventory.md").write_text("""# 库存管理

## F-INV-002 消耗物品

从库存中消耗指定数量。

### 实现

| 角色 | 代码符号 |
|---|---|
| 主入口 | src/inventory.py::Inventory.consume |

### 行为场景

| 编号 | 类型 | 场景与预期 | 测试 |
|---|---|---|---|
| S-01 | 正常 | 消耗后数量减少 | tests/test_inventory.py::test_consume_normal |
""", encoding="utf-8")
        (self.root / "features" / "cooking.md").write_text("""# 料理管理

## F-COOK-001 制作料理

根据配方生成食品。

### 功能关系

| 类型 | 功能编号 |
|---|---|
| 依赖 | F-INV-002 |

### 实现

| 角色 | 代码符号 |
|---|---|
| 主入口 | src/cooking.py::Cooking.cook |

### 行为场景

| 编号 | 类型 | 场景与预期 | 测试 |
|---|---|---|---|
| S-01 | 正常 | 原料充足时制作成功 | tests/test_cooking.py::test_cook_success |
""", encoding="utf-8")

    def test_validate_clean(self):
        features, issues = scan(self.root)
        report = validate(self.root, features, issues)
        self.assertEqual([], [x for x in report if x.severity == "error"])
        self.assertEqual(2, len(features))

    def test_feature_metadata_and_full_index(self):
        document = self.root / "features" / "inventory.md"
        document.write_text(document.read_text(encoding="utf-8").replace(
            "消耗物品\n", "消耗物品 草案\n\n创建提交：abcdef1234567\n"), encoding="utf-8")
        features, issues = scan(self.root)
        feature = next(f for f in features if f.fid == "F-INV-002")
        self.assertEqual("草案", feature.status)
        self.assertEqual("消耗物品", feature.name)
        self.assertEqual("库存管理", feature.module)
        self.assertEqual("abcdef1234567", feature.created_commit)
        self.assertEqual("从库存中消耗指定数量。", feature.description)
        indexed = next(f for f in to_index(features)["features"] if f["id"] == feature.fid)
        self.assertEqual("abcdef1234567", indexed["created_commit"])
        self.assertEqual("S-01", indexed["scenarios"][0]["id"])
        self.assertEqual("src/inventory.py::Inventory.consume", indexed["implementations"][0]["symbol"])
        self.assertFalse([x for x in issues if x.severity == "error"])

    def test_creation_commit_blank_invalid_and_duplicate(self):
        document = self.root / "features" / "inventory.md"
        original = document.read_text(encoding="utf-8")
        for value, expected_error in (("-", False), ("", False), ("abcdef1", False),
                                      ("HEAD", True), ("$(command)", True)):
            with self.subTest(value=value):
                document.write_text(original.replace("从库存", f"创建提交：{value}\n\n从库存"), encoding="utf-8")
                features, issues = scan(self.root)
                self.assertEqual(expected_error, any(x.severity == "error" for x in issues))
        document.write_text(original.replace("从库存", "创建提交：abcdef1\n创建提交：abcdef2\n\n从库存"), encoding="utf-8")
        _, issues = scan(self.root)
        self.assertTrue(any("重复" in x.message for x in issues))

    def test_retired_features_stay_visible_without_inflating_current_coverage(self):
        document = self.root / "features" / "inventory.md"
        document.write_text("# 库存管理\n\n~~## F-INV-002 消耗物品~~ 已废弃\n\n不再提供库存扣减。\n", encoding="utf-8")
        features, issues = scan(self.root)
        retired = next(f for f in features if f.fid == "F-INV-002")
        self.assertEqual("已废弃", retired.status)
        self.assertEqual(1, coverage(features)["features"])
        self.assertEqual(2, len(to_index(features)["features"]))
        self.assertFalse([x for x in validate(self.root, [retired], issues) if x.severity == "warning"])

    def test_reverse_index_and_impact(self):
        features, _ = scan(self.root)
        index = to_index(features)
        self.assertEqual("F-INV-002", index["implementations"]["src/inventory.py::Inventory.consume"][0]["feature"])
        self.assertEqual("S-01", index["tests"]["tests/test_inventory.py::test_consume_normal"][0]["scenario"])
        selection = impact(features, ["src/inventory.py"])
        self.assertEqual(["F-INV-002"], [r["feature"] for r in selection["direct_candidates"]])
        self.assertEqual(["F-COOK-001"], [r["feature"] for r in selection["related_candidates"]])
        self.assertEqual(1.0, coverage(features)["structural_link_ratio"])
        self.assertIn("tests/test_cooking.py::test_cook_success", selection["tests_for_review"])

    def test_unknown_relation_and_missing_test_detected(self):
        file = self.root / "features" / "cooking.md"
        content = file.read_text(encoding="utf-8").replace("F-INV-002", "F-INV-999")
        file.write_text(content.replace("test_cook_success", "test_does_not_exist"), encoding="utf-8")
        feats, errors = scan(self.root)
        report = validate(self.root, feats, errors)
        messages = " ".join(x.message for x in report if x.severity == "error")
        self.assertIn("关系目标未定义", messages)
        self.assertIn("未发现 Python 符号", messages)

    def test_relation_only_id_and_duplicate_scenario_detected(self):
        f = self.root / "features" / "cooking.md"
        content = f.read_text(encoding="utf-8").replace("| 依赖 | F-INV-002 |", "| 依赖 | F-INV-002 消耗物品 |")
        content += "\n| S-01 | 正常 | 重复编号 | tests/test_cooking.py::test_cook_success |\n"  # not in section; parser won't see
        # Add duplication inside table instead
        content = content.replace("| S-01 | 正常 | 原料充足时制作成功 | tests/test_cooking.py::test_cook_success |", "| S-01 | 正常 | 原料充足时制作成功 | tests/test_cooking.py::test_cook_success |\n| S-01 | 正常 | 重复编号 | tests/test_cooking.py::test_cook_success |")
        f.write_text(content, encoding="utf-8")
        feats, issues = scan(self.root)
        self.assertTrue(any("目标格必须" in x.message for x in issues))
        self.assertTrue(any("重复场景编号" in x.message for x in issues))

    def test_relation_multiple_targets(self):
        f = self.root / "features" / "cooking.md"
        f.write_text(
            f.read_text(encoding="utf-8").replace("| 依赖 | F-INV-002 |", "| 依赖 | F-INV-002, F-INV-003 |"),
            encoding="utf-8",
        )
        feats, issues = scan(self.root)
        report = validate(self.root, feats, issues)
        self.assertTrue(any("关系目标未定义：F-INV-003" in x.message for x in report))
        inv = self.root / "features" / "inventory.md"
        inv.write_text(inv.read_text(encoding="utf-8") + "\n## F-INV-003 补货\n\n补充库存。\n", encoding="utf-8")
        feats, issues = scan(self.root)
        report = validate(self.root, feats, issues)
        self.assertEqual([], [x for x in report if x.severity == "error"])
        cook = next(x for x in feats if x.fid == "F-COOK-001")
        self.assertEqual([("依赖", "F-INV-002"), ("依赖", "F-INV-003")], cook.relations)
        self.assertEqual(
            ["F-INV-002", "F-INV-003"],
            [r["target"] for r in to_index(feats)["relations"] if r["source"] == "F-COOK-001"],
        )

    def test_relation_target_rejects_invalid_item(self):
        f = self.root / "features" / "cooking.md"
        f.write_text(
            f.read_text(encoding="utf-8").replace("| 依赖 | F-INV-002 |", "| 依赖 | F-INV-002, 消耗物品 |"),
            encoding="utf-8",
        )
        feats, issues = scan(self.root)
        self.assertTrue(any("目标格必须" in x.message for x in issues))
        cook = next(x for x in feats if x.fid == "F-COOK-001")
        self.assertEqual([("依赖", "F-INV-002")], cook.relations)

    def test_scenario_multiple_tests(self):
        inv = self.root / "features" / "inventory.md"
        inv.write_text(
            inv.read_text(encoding="utf-8").replace(
                "tests/test_inventory.py::test_consume_normal",
                "tests/test_inventory.py::test_consume_normal, tests/test_inventory.py::test_consume_empty",
            ),
            encoding="utf-8",
        )
        (self.root / "tests" / "test_inventory.py").write_text(
            "def test_consume_normal():\n    assert True\n\n\ndef test_consume_empty():\n    assert True\n",
            encoding="utf-8",
        )
        feats, issues = scan(self.root)
        report = validate(self.root, feats, issues)
        self.assertEqual([], [x for x in report if x.severity == "error"])
        scenario = next(x for x in feats if x.fid == "F-INV-002").scenarios[0]
        self.assertEqual(
            ["tests/test_inventory.py::test_consume_normal", "tests/test_inventory.py::test_consume_empty"],
            scenario.tests,
        )

    def test_cli_json(self):
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            rc = main(["validate", "--project", str(self.root), "--json"])
        self.assertEqual(0, rc)
        self.assertEqual(0, json.loads(out.getvalue())["errors"])

    def test_code_fence_is_ignored(self):
        f = self.root / "features" / "inventory.md"
        f.write_text(f.read_text(encoding="utf-8") + "\n```markdown\n## F-FAKE-001 示例\n```\n", encoding="utf-8")
        features, _ = scan(self.root)
        self.assertEqual(2, len(features))

    def test_any_language_locators_survive_validation_index_and_impact(self):
        implementations = {
            "inventory.ts": "Inventory.consume<T, U>",
            "inventory.rs": "inventory::Inventory::consume",
            "inventory.go": "(*Inventory).Consume",
            "inventory.gd": "Inventory.consume",
            "inventory.cs": "Inventory.Consume(int, string)",
            "inventory.java": "Inventory.consume",
            "inventory.vue": "<script setup>::consume",
            "inventory.xyz": "consume|fallback",
            "inventory": "consume-items",
            "inventory.cpp": "inventory::consume(int, int)",
        }
        for name, locator in implementations.items():
            with self.subTest(name=name):
                (self.root / "src" / name).write_text("source managed by project tools", encoding="utf-8")
                ref = f"src/{name}::{locator}"
                document = self.root / "features" / "inventory.md"
                document.write_text(
                    "## F-INV-002 消耗物品\n\n消耗库存。\n\n### 实现\n\n"
                    "| 角色 | 代码符号 |\n|---|---|\n"
                    f"| 主入口 | {ref.replace('|', chr(92) + '|')} |\n",
                    encoding="utf-8",
                )
                features, issues = scan(self.root)
                report = validate(self.root, features, issues)
                self.assertFalse([x for x in report if x.severity == "error"])
                self.assertTrue(any("仅检查了文件存在" in x.message for x in report))
                self.assertIn(ref, to_index(features)["implementations"])
                selection = impact(features, [f"src/{name}"])
                self.assertEqual(["F-INV-002"], [x["feature"] for x in selection["direct_candidates"]])

    def test_native_test_titles_with_commas_pipes_and_namespaces(self):
        (self.root / "tests" / "inventory.spec.ts").write_text("", encoding="utf-8")
        document = self.root / "features" / "inventory.md"
        refs = "`tests/inventory.spec.ts::库存 > 消耗 1\\, 2\\|3`， `tests/inventory.spec.ts::库存::空库存`"
        document.write_text(
            document.read_text(encoding="utf-8").replace("tests/test_inventory.py::test_consume_normal", refs),
            encoding="utf-8",
        )
        features, issues = scan(self.root)
        self.assertFalse([x for x in validate(self.root, features, issues) if x.severity == "error"])
        expected = ["tests/inventory.spec.ts::库存 > 消耗 1, 2|3", "tests/inventory.spec.ts::库存::空库存"]
        self.assertEqual(expected, next(f for f in features if f.fid == "F-INV-002").scenarios[0].tests)
        self.assertEqual(set(expected), set(impact(features, ["src/inventory.py"])["tests_for_review"]) - {"tests/test_cooking.py::test_cook_success"})

    def run_checker(self, source, *options):
        checker = self.root / "checker.py"
        checker.write_text(source, encoding="utf-8")
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            rc = main(["validate", "--project", str(self.root), "--json", *options,
                       "--symbol-checker", sys.executable, str(checker), "--native-option"])
        return rc, json.loads(output.getvalue())

    def test_project_checker_receives_native_reference_and_kind(self):
        (self.root / "src" / "存货.ts").write_text("throw new Error('must not execute');", encoding="utf-8")
        document = self.root / "features" / "inventory.md"
        document.write_text(document.read_text(encoding="utf-8").replace(
            "src/inventory.py::Inventory.consume", "src/存货.ts::Inventory.consume<T, U>"), encoding="utf-8")
        source = """import json, pathlib, sys
request = json.loads(sys.stdin.buffer.read().decode('utf-8'))
assert set(request) == {'path', 'symbol', 'kind'}
assert pathlib.Path(request['path']).is_file()
assert request['kind'] in ('implementation', 'test')
assert request['symbol']
assert sys.argv[1:] == ['--native-option']
if request['path'].endswith('.ts'):
    assert request['path'] == 'src/存货.ts'
    assert request['symbol'] == 'Inventory.consume<T, U>'
    assert request['kind'] == 'implementation'
print(json.dumps({'status': 'found'}))
"""
        rc, report = self.run_checker(source)
        self.assertEqual(0, rc)
        self.assertEqual([], report["issues"])

    def test_external_checker_can_reject_a_native_test_title(self):
        test_file = self.root / "tests" / "inventory.spec.ts"
        test_file.write_text("", encoding="utf-8")
        document = self.root / "features" / "inventory.md"
        document.write_text(document.read_text(encoding="utf-8").replace(
            "tests/test_inventory.py::test_consume_normal", "tests/inventory.spec.ts::库存 > consumes 1\\, 2"), encoding="utf-8")
        rc, report = self.run_checker("""import json, sys
request = json.loads(sys.stdin.buffer.read().decode('utf-8'))
status = 'found'
if request['path'].endswith('.ts'):
    assert request['kind'] == 'test'
    assert request['symbol'] == '库存 > consumes 1, 2'
    status = 'missing'
print(json.dumps({'status': status}))
""")
        self.assertEqual(1, rc)
        self.assertEqual(1, report["errors"])
        self.assertTrue(any("库存 > consumes 1, 2" in x["message"] for x in report["issues"]))

    def test_project_checker_distinguishes_missing_unknown_and_failures(self):
        cases = [
            ("print('{\"status\": \"missing\", \"message\": \"no such symbol\"}')", 1, "no such symbol"),
            ("print('{\"status\": \"unknown\", \"message\": \"dynamic symbol\"}')", 0, "dynamic symbol"),
            ("print('{\"status\": \"invalid\"}')", 1, "检查器"),
            ("print('not json')", 1, "检查器"),
            ("print('[]')", 1, "检查器"),
            ("print('{\"status\": \"found\", \"message\": []}')", 1, "检查器"),
            ("raise SystemExit(2)", 1, "检查器"),
        ]
        for source, expected_rc, message in cases:
            with self.subTest(source=source):
                rc, report = self.run_checker(source)
                self.assertEqual(expected_rc, rc)
                self.assertTrue(any(message in x["message"] for x in report["issues"]))

    def test_project_checker_timeout_is_an_error(self):
        rc, report = self.run_checker("import time; time.sleep(5)", "--symbol-checker-timeout", "0.1")
        self.assertEqual(1, rc)
        self.assertTrue(any("超时" in x["message"] for x in report["issues"]))

    def test_project_checker_missing_command_is_an_error(self):
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            rc = main(["validate", "--project", str(self.root), "--json", "--symbol-checker", str(self.root / "no-such-command")])
        self.assertEqual(1, rc)
        self.assertTrue(any("无法执行符号检查器" in x["message"] for x in json.loads(output.getvalue())["issues"]))

    def test_cli_rejects_empty_checker_and_invalid_timeout(self):
        for options in (["--symbol-checker"], ["--symbol-checker-timeout", "0"],
                        ["--symbol-checker-timeout", "nan"], ["--symbol-checker-timeout", "inf"]):
            with self.subTest(options=options), contextlib.redirect_stderr(io.StringIO()):
                with self.assertRaises(SystemExit) as result:
                    main(["validate", "--project", str(self.root), *options])
                self.assertEqual(2, result.exception.code)

    def test_missing_file_and_escape_are_errors_for_any_extension(self):
        document = self.root / "features" / "inventory.md"
        original = document.read_text(encoding="utf-8")
        for ref in ("src/missing.ts::consume", "../outside.rs::consume", "C:/outside.cs::Consume"):
            with self.subTest(ref=ref):
                document.write_text(original.replace("src/inventory.py::Inventory.consume", ref), encoding="utf-8")
                features, issues = scan(self.root)
                self.assertTrue([x for x in validate(self.root, features, issues) if x.severity == "error"])


if __name__ == "__main__":
    unittest.main()
