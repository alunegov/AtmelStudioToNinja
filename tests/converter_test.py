import unittest

from asninja.converter import *


class TestConverter(unittest.TestCase):
    def test_detect_linker_script(self):
        self.assertEquals('linker_script', Converter.detect_linker_script(['bla -T../linker_script']))
        self.assertEquals('linker_script', Converter.detect_linker_script(['bla -T../linker_script bla']))
        self.assertIsNone(Converter.detect_linker_script(['linker_script']))

    def test_convert(self):
        pass


if __name__ == '__main__':
    unittest.main()
