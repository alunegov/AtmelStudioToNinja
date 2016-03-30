import unittest

from asninja.helpers import *


class TestHelpers(unittest.TestCase):
    def test_strip_empty_symbols(self):
        self.assertEqual(['a', 'c'], strip_empty_symbols(['a', '', 'c']))
        self.assertEqual([], strip_empty_symbols([]))

    def test_strip_updir(self):
        self.assertEqual('Path', strip_updir('../../Path'))
        self.assertEqual('Path', strip_updir('Path'))
        self.assertEqual('ath', strip_updir('..Path'))


if __name__ == '__main__':
    unittest.main()
