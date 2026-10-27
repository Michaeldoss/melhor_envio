import ast
import unittest
from pathlib import Path

ROOT = Path(__file__).parent
NAMES = {'arlete_serves_uf'}

tree = ast.parse((ROOT / 'app.py').read_text())
definitions = ast.Module(
    body=[node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name in NAMES],
    type_ignores=[],
)
scope = {'ARLETE_ALLOWED_UFS': {'SC','PR','RS','SP','RJ'}}
exec(compile(definitions, 'app.py', 'exec'), scope)


class ArleteCoverageTests(unittest.TestCase):
    def test_official_operating_states_are_allowed(self):
        for uf in ['SC','PR','RS','SP','RJ']:
            with self.subTest(uf=uf):
                self.assertTrue(scope['arlete_serves_uf'](uf))

    def test_maranhao_and_other_states_are_blocked(self):
        for uf in ['MA','PA','GO','BA','MG','ES','CE']:
            with self.subTest(uf=uf):
                self.assertFalse(scope['arlete_serves_uf'](uf))

    def test_normalizes_input(self):
        self.assertTrue(scope['arlete_serves_uf'](' sc '))
        self.assertFalse(scope['arlete_serves_uf'](''))


if __name__ == '__main__':
    unittest.main()
