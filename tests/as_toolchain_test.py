import unittest

from asninja import as_project
from asninja.as_toolchain import *


class TestAtmelStudioGccToolchain(unittest.TestCase):
    def test_constructor(self):
        tc = AtmelStudioGccToolchain('arm-')
        self.assertEquals('arm-', tc.path)
        self.assertEquals('arm', tc.tool_type)

    def test_from_project(self):
        asp = as_project.AtmelStudioProject('Korsar3.cproj', 'Korsar3')

        tc = AtmelStudioGccToolchain.from_project(asp)
        self.assertEquals('C:\\Program Files (x86)\\Atmel\\Atmel Studio 6.2\\..\\Atmel Toolchain\\ARM GCC\\Native\\'
                          '4.8.1437\\arm-gnu-toolchain\\bin', tc.path)
        self.assertEquals('arm', tc.tool_type)

    def test_read_reg(self):
        pass


if __name__ == '__main__':
    unittest.main()
