import unittest

from asninja.toolchains.gcc import *


class TestGccToolchain(unittest.TestCase):
    def test_constructor(self):
        tc = GccToolchain('arm-')
        self.assertEqual('arm-', tc.path)
        self.assertEqual('arm', tc.tool_type)

        tc = GccToolchain('TestPath', 'TestToolType')
        self.assertEqual('TestPath', tc.path)
        self.assertEqual('TestToolType', tc.tool_type)

        self.assertRaises(Exception, lambda: GccToolchain('PathWithoutToolchainMarker'))

    def test_tool_type(self):
        self.assertEqual('arm', GccToolchain.tool_type('arm-'))
        self.assertEqual('avr32', GccToolchain.tool_type('avr32-'))
        self.assertEqual('avr8', GccToolchain.tool_type('avr8-'))
        self.assertRaises(Exception, lambda: GccToolchain.tool_type('PathWithoutToolchainMarker'))

    def test_tool_prefix(self):
        tc = GccToolchain('', 'arm')
        self.assertEqual('arm-none-eabi', tc.tool_prefix())
        tc = GccToolchain('', 'avr32')
        self.assertEqual('avr32', tc.tool_prefix())
        tc = GccToolchain('', 'avr8')
        self.assertEqual('avr8', tc.tool_prefix())

    def test_ar(self):
        tc = GccToolchain('arm-')
        self.assertTrue('ar' in tc.ar())

    def test_cc(self):
        tc = GccToolchain('arm-')
        self.assertTrue('gcc' in tc.cc())

    def test_cxx(self):
        tc = GccToolchain('arm-')
        self.assertTrue('g++' in tc.cxx())


if __name__ == '__main__':
    unittest.main()
