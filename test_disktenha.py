import ast
import json
import re
import unittest
import unicodedata
from pathlib import Path
from typing import Any
from disktenha_rates import DISKTENHA_TABLE

# Exercise the real pure provider code without importing HTTP clients or credentials.
ROOT = Path(__file__).parent
NAMES = {'normalize_text', 'get_total_actual_weight', 'get_total_cubic_weight',
         'is_voluminous_load', 'classify_service', 'DiskTenhaProvider'}
tree = ast.parse((ROOT / 'app.py').read_text())
definitions = ast.Module(body=[node for node in tree.body if isinstance(node, (ast.FunctionDef, ast.ClassDef)) and node.name in NAMES], type_ignores=[])
scope = dict(Any=Any, unicodedata=unicodedata, DISKTENHA_TABLE=DISKTENHA_TABLE,
             DISKTENHA_ENABLED=True, DISKTENHA_CUBIC_DIVISOR=6000, DISKTENHA_VOLUMINOUS_FEE=3)
exec(compile(definitions, 'app.py', 'exec'), scope)

class DiskTenhaTariffTests(unittest.TestCase):
    def quote(self, city, uf='SC', weight=1):
        return scope['DiskTenhaProvider']().quote(city, uf, [{'width':10,'height':10,'length':10,'weight':weight}])[0]

    def test_all_75_supplied_rows_prices_partners_and_delivery(self):
        rows = json.loads((ROOT / 'disktenha_source_2026_10_19.json').read_text())
        self.assertEqual(len(rows), 75)
        for city, price, delivery, partner in rows:
            key = scope['normalize_text'](re.sub(r'\s*\((PR|SC)\)$', '', city))
            with self.subTest(city=city):
                row = DISKTENHA_TABLE[key]
                self.assertEqual(row, {'price':float(price.replace(',','.')), 'delivery_text':delivery, 'partner':partner or None})
                self.assertEqual(self.quote(key, 'PR' if city.endswith('(PR)') else 'SC')['price'], row['price'])

    def test_updated_base_rates(self):
        for city in ['Joinville','Garuva','Itapoá']:
            self.assertEqual(self.quote(city)['price'], 15)

    def test_updated_delivery_hours(self):
        for city in ['Benedito Novo','Doutor Pedrinho']:
            self.assertEqual(self.quote(city)['delivery_label'], '2ª, 4ª e 6ª, até 18h')

    def test_new_destinations_and_city_aliases(self):
        for city, uf, price in [('Agrolândia','SC',58),('Antônio Carlos','SC',49),('Fazenda Rio Grande','PR',43),('Piraquara','PR',43),('Rio Negro','PR',41),('Florianópolis','SC',49),('Florianópolis (Ilha)','SC',49)]:
            self.assertEqual(self.quote(city,uf)['price'], price)

    def test_existing_extra_weight_fee_and_unserved_uf(self):
        result = self.quote('Joinville', weight=60)
        self.assertEqual(result['price'], 28)  # base 15 + 10 kg exceeding 50 + existing fee 3
        self.assertIsNone(self.quote('Joinville','RS')['price'])
        self.assertIsNone(self.quote('Cidade desconhecida')['price'])

if __name__ == '__main__':
    unittest.main()
