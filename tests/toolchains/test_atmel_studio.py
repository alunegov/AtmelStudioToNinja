import sys
import unittest
from unittest.mock import patch

from asninja.parser import AtmelStudioProject
from asninja.toolchains.atmel_studio import *


class TestAtmelStudioGccToolchain(unittest.TestCase):
    def test_constructor(self):
        tc = AtmelStudioGccToolchain('arm-')
        self.assertEqual('arm-', tc.path)
        self.assertEqual('arm', tc.tool_type)

    @patch.object(AtmelStudioGccToolchain, 'read_reg', return_value = 'DUMMY_PATH')
    def test_from_project(self, mock_method):
        asp = AtmelStudioProject('Korsar3.cproj', 'Korsar3')

        tc = AtmelStudioGccToolchain.from_project(asp)
        self.assertEqual('DUMMY_PATH\\..\\Atmel Toolchain\\ARM GCC\\Native\\4.8.1437\\arm-gnu-toolchain\\bin', tc.path)
        self.assertEqual('arm', tc.tool_type)

    @unittest.skipUnless(sys.platform.startswith("win"), "requires Windows")
    def test_read_reg(self):
        pass


if __name__ == '__main__':
    unittest.main()
