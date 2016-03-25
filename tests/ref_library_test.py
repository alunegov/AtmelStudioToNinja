import unittest
from asninja import RefLibrary


class TestRefLibrary(unittest.TestCase):
    def test_extract_name(self):
        self.assertEquals('Center', RefLibrary.extract_name('Center'))
        self.assertEquals('Center', RefLibrary.extract_name('libCenter'))
        self.assertEquals('Center', RefLibrary.extract_name('Center.a'))
        self.assertEquals('Center', RefLibrary.extract_name('libCenter.a'))


if __name__ == '__main__':
    unittest.main()
