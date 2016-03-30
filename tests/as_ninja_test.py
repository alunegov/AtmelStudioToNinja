import unittest

from asninja.as_ninja import *


class TestASNinja(unittest.TestCase):
    def test_detect_linker_script(self):
        self.assertEquals('linker_script', detect_linker_script(['bla -T../linker_script']))
        self.assertEquals('linker_script', detect_linker_script(['bla -T../linker_script bla']))
        self.assertIsNone(detect_linker_script(['linker_script']))

    def test_convert(self):
        pass


if __name__ == '__main__':
    unittest.main()
