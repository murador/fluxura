import ast
import tomllib
from pathlib import Path
import unittest


class PRRegressionTests(unittest.TestCase):
    def test_extraction_task_serializes_with_to_dict(self) -> None:
        source = Path("src/fluxura/pipeline/tasks.py").read_text(encoding="utf-8")
        tree = ast.parse(source)

        extraction_task = next(
            node
            for node in tree.body
            if isinstance(node, ast.FunctionDef) and node.name == "extraction_task"
        )
        return_stmt = next(node for node in extraction_task.body if isinstance(node, ast.Return))
        returned_expr = ast.unparse(return_stmt.value)

        self.assertIn("to_dict", returned_expr)
        self.assertNotIn("__dict__", returned_expr)

    def test_calculate_totals_returns_payload_as_dict(self) -> None:
        source = Path("src/fluxura/services/calculation.py").read_text(encoding="utf-8")
        tree = ast.parse(source)

        calculate_totals = next(
            node
            for node in tree.body
            if isinstance(node, ast.FunctionDef) and node.name == "calculate_totals"
        )
        return_stmt = next(node for node in calculate_totals.body if isinstance(node, ast.Return))
        returned_expr = ast.unparse(return_stmt.value)

        self.assertIn("'payload': payload.to_dict()", returned_expr)

    def test_pyproject_includes_psycopg_dependency(self) -> None:
        data = tomllib.loads(Path("pyproject.toml").read_text(encoding="utf-8"))
        dependencies = data["project"]["dependencies"]
        self.assertTrue(any(dep.startswith("psycopg") for dep in dependencies))


if __name__ == "__main__":
    unittest.main()
