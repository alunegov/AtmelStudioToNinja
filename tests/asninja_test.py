import unittest
import asninja


class TestRefLibrary(unittest.TestCase):

    def test_lib_name(self):
        reflib = asninja.RefLibrary('', 'Center')
        self.assertEquals('libCenter', reflib.lib_name(False))
        self.assertEquals('libCenter.a', reflib.lib_name(True))

    def test_full_name(self):
        reflib = asninja.RefLibrary('Path', 'Center')
        self.assertEquals('Path/Debug/libCenter.a', reflib.full_name('Debug'))

    def test_extract_name(self):
        self.assertEquals('Center', asninja.RefLibrary.extract_name('Center'))
        self.assertEquals('Center', asninja.RefLibrary.extract_name('libCenter'))
        self.assertEquals('Center', asninja.RefLibrary.extract_name('Center.a'))
        self.assertEquals('Center', asninja.RefLibrary.extract_name('libCenter.a'))


class TestFunctions(unittest.TestCase):

    def test_strip_updir(self):
        self.assertEquals('Path', asninja.strip_updir('Path'))
        self.assertEquals('Path', asninja.strip_updir('../Path'))
        self.assertEquals('Path', asninja.strip_updir('../../Path'))
        self.assertEquals('ath', asninja.strip_updir('..Path'))

    def test_detect_linker_script(self):
        self.assertEquals('linker_script', asninja.detect_linker_script(['bla -T../linker_script']))
        self.assertEquals('linker_script', asninja.detect_linker_script(['bla -T../linker_script bla']))
        self.assertIsNone(asninja.detect_linker_script(['linker_script']))


if __name__ == '__main__':
    unittest.main()
