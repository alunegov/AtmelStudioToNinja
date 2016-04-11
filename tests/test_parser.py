import unittest

from asninja.parser import *


class TestAtmelStudioProject(unittest.TestCase):
    def setUp(self):
        self.asp = AtmelStudioProject('Korsar3.cproj', 'Korsar3')

    def tearDown(self):
        self.asp = None

    def test_init(self):
        self.assertIsNone(self.asp.config_group)
        self.assertFalse(self.asp.is_cpp)
        self.assertFalse(self.asp.is_lib)
        self.assertEqual('Korsar3', self.asp.output_name)
        self.assertEqual('.elf', self.asp.output_ext)
        self.assertEqual('ArmGcc', self.asp.toolchain_settings)
        self.assertIsNotNone(self.asp.ref_libs)
        self.assertIsInstance(self.asp.ref_libs, list)
        self.assertLess(0, len(self.asp.ref_libs))

    def test_output(self):
        self.assertEqual('Korsar3.elf', self.asp.output())

    def test_toolchain(self):
        prj_version, name, flavour = self.asp.toolchain_id()
        self.assertEqual('6.2', prj_version)
        self.assertEqual('com.Atmel.ARMGCC.C', name)
        self.assertEqual('Native', flavour)

    def test_select_config(self):
        self.assertTrue(self.asp.select_config('Debug'))
        self.assertIsNotNone(self.asp.config_group)

        self.assertTrue(self.asp.select_config('Release'))
        self.assertIsNotNone(self.asp.config_group)

        self.assertFalse(self.asp.select_config('NonExists'))
        self.assertIsNone(self.asp.config_group)

    def test_key_raw(self):
        self.assertTrue(self.asp.select_config('Debug'))

        self.assertIsNotNone(self.asp.key_raw('armgcc.common.outputfiles.hex'))
        self.assertIsNone(self.asp.key_raw('NonExists'))

    def test_key_as_bool(self):
        self.assertTrue(self.asp.select_config('Debug'))

        self.assertTrue(self.asp.key_as_bool('armgcc.compiler.warnings.AllWarnings', False))
        self.assertFalse(self.asp.key_as_bool('armgcc.common.outputfiles.hex', True))
        self.assertFalse(self.asp.key_as_bool('NonExists', False))
        self.assertTrue(self.asp.key_as_bool('NonExists', True))

    def test_key_as_str(self):
        self.assertTrue(self.asp.select_config('Debug'))

        self.assertEqual('bla-Maximum (-g3)',
                          self.asp.key_as_str('armgcc.compiler.optimization.DebugLevel', 'bla-{}', '',))
        self.assertEqual('Dummy', self.asp.key_as_str('NonExists', 'bla-{}', 'Dummy',))

    def test_key_as_strlist(self):
        self.assertTrue(self.asp.select_config('Debug'))

        keys = self.asp.key_as_strlist('armgcc.compiler.symbols.DefSymbols', 'bla-{}')
        self.assertIsNotNone(keys)
        self.assertIsInstance(keys, list)
        self.assertLess(0, len(keys))
        for key in keys:
            self.assertIn('bla-', key)

        keys = self.asp.key_as_strlist('NonExists', 'bla-{}')
        self.assertIsNotNone(keys)
        self.assertIsInstance(keys, list)
        self.assertEqual(0, len(keys))

    def test_src_files(self):
        files = self.asp.src_files()
        self.assertIsNotNone(files)
        self.assertIsInstance(files, list)
        self.assertLess(0, len(files))
        for file in files:
            __, file_ext = os.path.splitext(file)
            self.assertTrue(file_ext in ['.c', '.cpp', '.h'], 'unexpected srcfile ext ' + file_ext)

    def test_compiler_flags(self):
        self.assertTrue(self.asp.select_config('Debug'))

        flags = self.asp.compiler_flags(True, add_defs=['TestDef'], del_defs=[], add_undefs=[])
        self.assertIsNotNone(flags)
        self.assertIsInstance(flags, list)
        self.assertLess(0, len(flags))

        self.assertTrue('-DTestDef' in flags)

    def test_compiler_flags_with_empty_def(self):
        self.assertTrue(self.asp.select_config('Debug'))

        flags = self.asp.compiler_flags(True, add_defs=[''], del_defs=[], add_undefs=[])
        self.assertFalse('-D' in flags)

    def test_linker_flags(self):
        self.assertTrue(self.asp.select_config('Debug'))

        flags = self.asp.linker_flags('Debug')
        self.assertIsNotNone(flags)
        self.assertIsInstance(flags, list)
        self.assertLess(0, len(flags))

    def test_archiver_flags(self):
        self.assertTrue(self.asp.select_config('Debug'))

        flags = self.asp.archiver_flags()
        self.assertIsNotNone(flags)
        self.assertIsInstance(flags, list)
        self.assertEqual(1, len(flags))
        self.assertEqual('-r', flags[0])


class TestRefLibrary(unittest.TestCase):
    def test_lib_name(self):
        reflib = RefLibrary('', 'Center')

        self.assertEqual('libCenter', reflib.lib_name(False))
        self.assertEqual('libCenter.a', reflib.lib_name(True))

    def test_full_name(self):
        reflib = RefLibrary('Path', 'Center')

        self.assertEqual('Path/Debug/libCenter.a', reflib.full_name('Debug'))

    def test_extract_name(self):
        self.assertEqual('Center', RefLibrary.extract_name('Center'))
        self.assertEqual('Center', RefLibrary.extract_name('libCenter'))
        self.assertEqual('Center', RefLibrary.extract_name('Center.a'))
        self.assertEqual('Center', RefLibrary.extract_name('libCenter.a'))


if __name__ == '__main__':
    unittest.main()
