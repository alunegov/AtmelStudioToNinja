import unittest

from asninja.helpers import *


class TestHelpers(unittest.TestCase):
    def test_strip_empty_symbols(self):
        self.assertEquals(['a', 'c'], strip_empty_symbols(['a', '', 'c']))
        self.assertEquals([], strip_empty_symbols([]))

    def test_strip_updir(self):
        self.assertEquals('Path', strip_updir('../../Path'))
        self.assertEquals('Path', strip_updir('Path'))
        self.assertEquals('ath', strip_updir('..Path'))


if __name__ == '__main__':
    unittest.main()
