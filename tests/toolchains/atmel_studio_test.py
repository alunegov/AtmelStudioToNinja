import unittest

from asninja.parser import AtmelStudioProject
from asninja.toolchains.atmel_studio import *


class TestAtmelStudioGccToolchain(unittest.TestCase):
    def test_constructor(self):
        tc = AtmelStudioGccToolchain('arm-')
        self.assertEqual('arm-', tc.path)
        self.assertEqual('arm', tc.tool_type)

    def test_from_project(self):
        asp = AtmelStudioProject('Korsar3.cproj', 'Korsar3')

        tc = AtmelStudioGccToolchain.from_project(asp)
        self.assertEqual('C:\\Program Files (x86)\\Atmel\\Atmel Studio 6.2\\..\\Atmel Toolchain\\ARM GCC\\Native\\'
                         '4.8.1437\\arm-gnu-toolchain\\bin', tc.path)
        self.assertEqual('arm', tc.tool_type)

    def test_read_reg(self):
        pass


if __name__ == '__main__':
    unittest.main()
