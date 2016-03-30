import os

__all__ = ["GccToolchain"]


class GccToolchain(object):
    def __init__(self, path, tool_type=None):
        self.path = path
        self.tool_type = tool_type if tool_type else self.tool_type(path)

    @classmethod
    def tool_type(cls, path) -> str:
        if 'arm-' in path:
            tool_type = 'arm'
        elif 'avr32-' in path:
            tool_type = 'avr32'
        elif 'avr8-' in path:
            tool_type = 'avr8'
        else:
            raise Exception('Unsupported toolchain {0}'.format(path))
        return tool_type

    def tool_prefix(self) -> str:
        prefixes = {'arm': 'arm-none-eabi',
                    'avr32': 'avr32',
                    'avr8': 'avr8'}
        return prefixes[self.tool_type]

    def ar(self) -> str:
        tool = self.tool_prefix() + '-ar'
        return os.path.join(self.path, tool)

    def cc(self) -> str:
        tool = self.tool_prefix() + '-gcc'
        return os.path.join(self.path, tool)

    def cxx(self) -> str:
        tool = self.tool_prefix() + '-g++'
        return os.path.join(self.path, tool)

    def objdump(self) -> str:
        tool = self.tool_prefix() + '-objdump'
        return os.path.join(self.path, tool)

    def size(self) -> str:
        tool = self.tool_prefix() + '-size'
        return os.path.join(self.path, tool)
