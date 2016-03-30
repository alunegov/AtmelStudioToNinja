import os
import winreg

from ..toolchains.gcc import GccToolchain


class AtmelStudioGccToolchain(GccToolchain):
    def __init__(self, path):
        super().__init__(path)

    @classmethod
    def from_project(cls, asp):
        as62_suffixes = {'arm': '..\\Atmel Toolchain\\ARM GCC\\Native\\4.8.1437\\arm-gnu-toolchain\\bin',
                         'avr32': '..\\Atmel Toolchain\\AVR32 GCC\\Native\\3.4.1067\\avr32-gnu-toolchain\\bin',
                         'avr8': '..\\Atmel Toolchain\\AVR8 GCC\\Native\\3.4.1061\\avr8-gnu-toolchain\\bin'}
        as70_suffixes = {'arm': 'toolchain\\arm\\arm-gnu-toolchain\\bin',
                         'avr32': 'toolchain\\avr32\\avr32-gnu-toolchain\\bin',
                         'avr8': 'toolchain\\avr8\\avr8-gnu-toolchain\\bin'}

        assert asp
        prj_version, name, flavour = asp.toolchain_id()

        if flavour == 'Native':
            if 'ARMGCC' in name:
                tool_type = 'arm'
            elif 'AVR32GCC' in name:
                tool_type = 'avr32'
            elif 'AVR8GCC' in name:
                tool_type = 'avr8'
            else:
                exc_text = 'Unsupported Native toolchain name {0}.'.format(name)
                exc_text += ' You can set toolchain explicitly with --gcc_toolchain'
                raise Exception(exc_text)

            if prj_version == '6.2':
                suffix = as62_suffixes[tool_type]
            elif prj_version == '7.0':
                suffix = as70_suffixes[tool_type]
            else:
                exc_text = 'Unsupported project version {0}.'.format(prj_version)
                exc_text += ' You can set toolchain explicitly with --gcc_toolchain'
                raise Exception(exc_text)

            reg_key_name = 'Software\\Atmel\\AtmelStudio\\{}_Config'.format(prj_version)
            as_dir = cls.read_reg(reg_key_name, 'InstallDir')
            if len(as_dir) == 0:
                exc_text = 'Path to Atmel Studio not detected.'
                exc_text += ' You can set toolchain explicitly with --gcc_toolchain'
                raise Exception(exc_text)

            path = os.path.join(as_dir, suffix)
        else:
            reg_key_name = 'Software\\Atmel\\AtmelStudio\\{}\\ToolchainPackages\\{}\\{}'.format(prj_version, name,
                                                                                                flavour)
            path = cls.read_reg(reg_key_name, 'BasePath')
            if len(path) == 0:
                exc_text = 'Path to non-native toolchain flavour not detected.'
                exc_text += ' You can set toolchain explicitly with --gcc_toolchain'
                raise Exception(exc_text)

        return AtmelStudioGccToolchain(path)

    @classmethod
    def read_reg(cls, key_name, value_name):
        try:
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, key_name) as key:
                value, __ = winreg.QueryValueEx(key, value_name)
        except WindowsError:
            value = ''
        return value
