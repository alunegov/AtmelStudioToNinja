import unittest

from asninja.toolchains.gcc import *


class TestGccToolchain(unittest.TestCase):
    def test_constructor(self):
        tc = GccToolchain('arm-')
        self.assertEquals('arm-', tc.path)
        self.assertEquals('arm', tc.tool_type)

        tc = GccToolchain('TestPath', 'TestToolType')
        self.assertEquals('TestPath', tc.path)
        self.assertEquals('TestToolType', tc.tool_type)

        # self.assertRaises(Exception, GccToolchain('PathWithoutToolchainMarker'))

    def test_tool_type(self):
        self.assertEquals('arm', GccToolchain.tool_type('arm-'))
        self.assertEquals('avr32', GccToolchain.tool_type('avr32-'))
        self.assertEquals('avr8', GccToolchain.tool_type('avr8-'))
        # self.assertRaises(Exception, GccToolchain.tool_type('PathWithoutToolchainMarker'))

    def test_tool_prefix(self):
        tc = GccToolchain('', 'arm')
        self.assertEquals('arm-none-eabi', tc.tool_prefix())
        tc = GccToolchain('', 'avr32')
        self.assertEquals('avr32', tc.tool_prefix())
        tc = GccToolchain('', 'avr8')
        self.assertEquals('avr8', tc.tool_prefix())

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
