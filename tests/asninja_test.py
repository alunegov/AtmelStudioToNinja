import os
import unittest
import asninja


class TestAtmelStudio62ToolChain(unittest.TestCase):

    def setUp(self):
        pass

    def tearDown(self):
        pass

    def test_toolchain(self):
        ast = asninja.AtmelStudio62Toolchain('6.2', 'com.Atmel.ARMGCC.C', 'Native')
        self.assertEquals('../Atmel Toolchain/ARM GCC/Native/4.8.1437/arm-gnu-toolchain/bin',
                          ast.toolchain())

        ast = asninja.AtmelStudio62Toolchain('6.2', 'com.Atmel.ARMGCC.C', 'AS7')
        self.assertEquals('C:/Program Files (x86)/Atmel/Studio/7.0/toolchain/arm/arm-gnu-toolchain/bin',
                          ast.toolchain())

    def test_cc(self):
        ast = asninja.AtmelStudio62Toolchain('6.2', 'com.Atmel.ARMGCC.C', 'Native')
        self.assertTrue('gcc' in ast.cc())

    def test_cxx(self):
        ast = asninja.AtmelStudio62Toolchain('6.2', 'com.Atmel.ARMGCC.C', 'Native')
        self.assertTrue('g++' in ast.cxx())


class TestAtmelStudioProject(unittest.TestCase):

    def setUp(self):
        self.asp = asninja.AtmelStudioProject('Korsar3.cproj', 'Korsar3')

    def tearDown(self):
        self.asp = None

    def test_init(self):
        self.assertIsNone(self.asp.config_group)
        self.assertFalse(self.asp.is_cpp)
        self.assertFalse(self.asp.is_lib)
        self.assertEquals('Korsar3', self.asp.output_name)
        self.assertEquals('.elf', self.asp.output_ext)
        self.assertEquals('ArmGcc', self.asp.toolchain_settings)
        self.assertIsNotNone(self.asp.ref_libs)
        self.assertIsInstance(self.asp.ref_libs, list)
        self.assertLess(0, len(self.asp.ref_libs))

    def test_output(self):
        self.assertEquals('Korsar3.elf', self.asp.output())

    def test_toolchain(self):
        self.assertIsNotNone(self.asp.toolchain())

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

        self.assertEquals('bla-Maximum (-g3)',
                          self.asp.key_as_str('armgcc.compiler.optimization.DebugLevel', 'bla-{}', '',))
        self.assertEquals('Dummy', self.asp.key_as_str('NonExists', 'bla-{}', 'Dummy',))

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
        self.assertEquals(0, len(keys))

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

        flags = self.asp.compiler_flags('armgcc', add_defs=['TestDef'])
        self.assertIsNotNone(flags)
        self.assertIsInstance(flags, list)
        self.assertLess(0, len(flags))

        self.assertTrue('-DTestDef' in flags)

    def test_compiler_flags_with_empty_def(self):
        self.assertTrue(self.asp.select_config('Debug'))

        flags = self.asp.compiler_flags('armgcc', add_defs=[''])
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
        self.assertEquals(1, len(flags))
        self.assertEquals('-r', flags[0])


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


class TestConvert(unittest.TestCase):

    def test_(self):
        pass


if __name__ == '__main__':
    unittest.main()
