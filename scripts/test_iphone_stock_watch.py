"""Consumer-visible stock classification boundaries; no live network calls."""
import json
import unittest
from unittest.mock import patch

import iphone_stock_watch as watch


def product(name, state):
    return {'@type': 'Product', 'name': name,
            'offers': {'availability': 'https://schema.org/' + state}}


def markup(value):
    return '<script type="application/ld+json">' + json.dumps(value) + '</script>'


class StockClassificationTests(unittest.TestCase):
    def classify(self, body):
        with patch.object(watch, 'fetch', return_value=body):
            return watch.generic('retailer', watch.APPLE)

    def test_other_iphone_stock_is_not_duo_stock(self):
        rows = self.classify(markup([product('iPhone 18 Pro', 'InStock'), product('iPhone Duo', 'OutOfStock')]))
        self.assertEqual([r['status'] for r in rows], ['UNAVAILABLE'])

    def test_preorder_and_cart_copy_never_imply_immediate_stock(self):
        rows = self.classify('iPhone Duo Available 23 October Add to cart Same day delivery')
        self.assertEqual(rows[0]['status'], 'UNKNOWN')
        self.assertEqual(self.classify(markup(product('iPhone Duo', 'PreOrder')))[0]['status'], 'UNAVAILABLE')

    def test_conflicting_offers_are_not_reported_as_confirmed_stock(self):
        item = product('iPhone Duo', 'InStock')
        item['offers'] = [item['offers'], {'availability': 'https://schema.org/OutOfStock'}]
        self.assertEqual(self.classify(markup(item))[0]['status'], 'CONFLICT')

    def test_instock_is_candidate_with_unconfirmed_delivery(self):
        row = self.classify(markup(product('iPhone Duo 512GB', 'InStock')))[0]
        self.assertEqual(row['status'], 'CANDIDATE')
        self.assertIn('UNCONFIRMED', row['delivery'])

    def test_network_failure_is_not_out_of_stock(self):
        def blocked():
            raise OSError('403 Forbidden')
        row = watch.safe_check('Apple', watch.APPLE, blocked)[0]
        self.assertEqual(row['status'], 'ERROR')
        self.assertIn('403 Forbidden', row['evidence'])

    def test_non_authorised_seller_cannot_be_fetched(self):
        with self.assertRaisesRegex(ValueError, 'Non-authorised'):
            watch.fetch('https://www.carousell.sg/iphone-duo')


if __name__ == '__main__':
    unittest.main()
