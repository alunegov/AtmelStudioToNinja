import os
from xml.etree import ElementTree
import re
import ninja_syntax


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
        import winreg

        try:
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, key_name) as key:
                value, __ = winreg.QueryValueEx(key, value_name)
        except WindowsError:
            value = ''
        return value


class AtmelStudioProject(object):
    NSMAP = {'msb': 'http://schemas.microsoft.com/developer/msbuild/2003'}

    def __init__(self, file_name, output):
        self.prj = ElementTree.parse(file_name)
        self.config_group = None
        self.is_cpp = None
        self.is_lib = None
        self.output_name = None
        self.output_ext = None
        self.toolchain_settings = None
        self.ref_libs = None
        self.detect(output)

    def detect(self, output):
        if not self.prj:
            pass
        key = self.prj.find('.//msb:PropertyGroup/msb:SchemaVersion', self.NSMAP)
        assert (key is not None) and (key.text == '2.0'), 'Unsupported project schema version'
        key = self.prj.find('.//msb:PropertyGroup/msb:Language', self.NSMAP)
        self.is_cpp = key.text == 'CPP'
        key = self.prj.find('.//msb:PropertyGroup/msb:OutputType', self.NSMAP)
        self.is_lib = key.text == 'StaticLibrary'
        key = self.prj.find('.//msb:PropertyGroup/msb:OutputFileName', self.NSMAP)
        self.output_name = key.text.replace('$(MSBuildProjectName)', output)
        key = self.prj.find('.//msb:PropertyGroup/msb:OutputFileExtension', self.NSMAP)
        self.output_ext = key.text
        if self.is_cpp:
            self.toolchain_settings = 'ArmGccCpp'
        else:
            self.toolchain_settings = 'ArmGcc'
        self.ref_libs = []
        for node in self.prj.findall('.//msb:ItemGroup/msb:ProjectReference', self.NSMAP):
            path, prj_name = os.path.split(node.attrib['Include'])
            raw_name, __ = os.path.splitext(prj_name)
            self.ref_libs.append(RefLibrary(path.replace('\\', '/'), raw_name))

    def output(self):
        assert self.output_name is not None
        assert self.output_ext
        return self.output_name + self.output_ext

    def toolchain_id(self):
        key = self.prj.find('.//msb:PropertyGroup/msb:ProjectVersion', self.NSMAP)
        prj_version = key.text
        key = self.prj.find('.//msb:PropertyGroup/msb:ToolchainName', self.NSMAP)
        toolchain_name = key.text
        key = self.prj.find('.//msb:PropertyGroup/msb:ToolchainFlavour', self.NSMAP)
        toolchain_flavour = key.text

        return prj_version, toolchain_name, toolchain_flavour

    def select_config(self, config_name):
        self.config_group = None
        for group in self.prj.findall('msb:PropertyGroup', self.NSMAP):
            if group.attrib.get('Condition', '__') == " '$(Configuration)' == '{}' ".format(config_name):
                self.config_group = group
                break
        return self.config_group is not None

    def key_raw(self, name):
        assert self.config_group is not None
        key_xpath = './/msb:{}/msb:{}'.format(self.toolchain_settings, name)
        return self.config_group.find(key_xpath, self.NSMAP)

    def key_as_bool(self, name, default=False):
        assert self.config_group is not None
        key = self.key_raw(name)
        if key is not None:
            return key.text == 'True'
        else:
            return default

    def key_as_str(self, name, fmt, default=''):
        assert self.config_group is not None
        key = self.key_raw(name)
        if key is not None:
            return fmt.format(key.text)
        else:
            return default

    def key_as_strlist(self, name, fmt):
        assert self.config_group is not None
        s = []
        key_xpath = './/msb:{}/msb:{}/msb:ListValues/msb:Value'.format(self.toolchain_settings, name)
        for key in self.config_group.findall(key_xpath, self.NSMAP):
            s.append(fmt.format(key.text))
        return s

    def src_files(self):
        src_files = []
        for node in self.prj.findall('.//msb:ItemGroup/msb:Compile', self.NSMAP):
            src_files.append(node.attrib['Include'].replace('\\', '/'))
        return src_files

    @staticmethod
    def strip_empty_symbols(symbols):
        assert isinstance(symbols, list)
        new_symbols = []
        for symbol in symbols:
            if len(symbol) != 0:
                new_symbols.append(symbol)
        return new_symbols

    def compiler_flags(self, compiler, add_defs=None, del_defs=None, add_undefs=None):
        assert self.config_group is not None
        flags = []
        prefix = compiler + '.compiler.'
        # General
        if self.key_as_bool(prefix + 'general.ChangeDefaultCharTypeUnsigned'):
            flags.append('-funsigned-char')
        if self.key_as_bool(prefix + 'general.ChangeDefaultBitFieldUnsigned'):
            flags.append('-funsigned-bitfields')
        # Preprocessor
        if self.key_as_bool(prefix + 'general.DoNotSearchSystemDirectories'):
            flags.append('-nostdinc')
        if self.key_as_bool(prefix + 'general.PreprocessOnly'):
            flags.append('-E')
        # Symbols
        if add_defs:
            inc_defs = self.strip_empty_symbols(ninja_syntax.as_list(add_defs))
        else:
            inc_defs = []
        inc_defs += self.key_as_strlist(prefix + 'symbols.DefSymbols', '{}')
        for undef in ninja_syntax.as_list(del_defs):
            if inc_defs.count(undef) > 0:
                assert inc_defs.count(undef) == 1
                inc_defs.remove(undef)
        flags.extend('-D{}'.format(inc_def) for inc_def in inc_defs)
        if add_undefs:
            inc_undefs = self.strip_empty_symbols(ninja_syntax.as_list(add_undefs))
        else:
            inc_undefs = []
        inc_undefs += self.key_as_strlist(prefix + 'preprocessor.UndefSymbols', '{}')
        flags.extend('-U{}'.format(inc_undef) for inc_undef in inc_undefs)
        # Directories
        # if self.key_as_bool(prefix + 'directories.DefaultIncludePath', True):
        #     flags += []
        flags += self.key_as_strlist(prefix + 'directories.IncludePaths', '-I"{}"')
        # Optimization
        # Optimization Level: -O[0,1,2,3,s]
        key = self.key_raw(prefix + 'optimization.level')
        if key is not None:
            opt_level = re.search('(-O[0|1|2|3|s])', key.text)
            if opt_level:
                flags.append(opt_level.group(0))
        else:
            flags.append('-O0')
        flags += [self.key_as_str(prefix + 'optimization.OtherFlags', '{}')]
        if self.key_as_bool(prefix + 'optimization.PrepareFunctionsForGarbageCollection'):
            flags.append('-ffunction-sections')
        if self.key_as_bool(prefix + 'optimization.PrepareDataForGarbageCollection'):
            flags.append('-fdata-sections')
        if self.key_as_bool(prefix + 'optimization.EnableUnsafeMatchOptimizations'):
            flags.append('-funsafe-math-optimizations')
        if self.key_as_bool(prefix + 'optimization.EnableFastMath'):
            flags.append('-ffast-math')
        if self.key_as_bool(prefix + 'optimization.GeneratePositionIndependentCode'):
            flags.append('-fpic')
        if self.key_as_bool(prefix + 'optimization.EnableFastMath'):
            flags.append('-ffast-math')
        if self.key_as_bool(prefix + 'optimization.EnableLongCalls', True):
            flags.append('-mlong-calls')
        # Debugging
        # Debug Level: None and -g[1,2,3]
        key = self.key_raw(prefix + 'optimization.DebugLevel')
        if key is not None:
            debug_level = re.search('-g[1|2|3]', key.text)
            if debug_level:
                flags.append(debug_level.group(0))
        flags.append(self.key_as_str(prefix + 'optimization.OtherDebuggingFlags', '{}'))
        if self.key_as_bool(prefix + 'optimization.GenerateGprofInformation'):
            flags.append('-pg')
        if self.key_as_bool(prefix + 'optimization.GenerateProfInformation'):
            flags.append('-p')
        # Warnings
        if self.key_as_bool(prefix + 'warnings.AllWarnings'):
            flags.append('-Wall')
        if self.key_as_bool(prefix + 'warnings.ExtraWarnings'):
            flags.append('-Wextra')
        if self.key_as_bool(prefix + 'warnings.Undefined'):
            flags.append('-Wundef')
        if self.key_as_bool(prefix + 'warnings.WarningsAsErrors'):
            flags.append('-Werror')
        if self.key_as_bool(prefix + 'warnings.CheckSyntaxOnly'):
            flags.append('-fsyntax-only')
        if self.key_as_bool(prefix + 'warnings.Pedantic'):
            flags.append('-pedentic')
        if self.key_as_bool(prefix + 'warnings.PedanticWarningsAsErrors'):
            flags.append('-pedantic-errors')
        if self.key_as_bool(prefix + 'warnings.InhibitAllWarnings'):
            flags.append('-w')
        # Miscellaneous
        flags.append(self.key_as_str(prefix + 'miscellaneous.OtherFlags', '{}'))
        if self.key_as_bool(prefix + 'miscellaneous.Verbose'):
            flags.append('-v')
        if self.key_as_bool(prefix + 'miscellaneous.SupportAnsiPrograms'):
            flags.append('-ansi')
        return flags

    def linker_flags(self, outdir):
        assert self.config_group is not None
        flags = []
        prefix = self.toolchain_settings.lower() + '.linker.'
        # General
        if self.key_as_bool(prefix + 'general.DoNotUseStandardStartFiles'):
            flags.append('-nostartfiles')
        if self.key_as_bool(prefix + 'general.DoNotUseDefaultLibraries'):
            flags.append('-nodefaultlibs')
        if self.key_as_bool(prefix + 'general.NoStartupOrDefaultLibs'):
            flags.append('-nostdlib')
        if self.key_as_bool(prefix + 'general.OmitAllSymbolInformation'):
            flags.append('-s')
        if self.key_as_bool(prefix + 'general.NoSharedLibraries'):
            flags.append('-static')
        if self.key_as_bool(prefix + 'general.GenerateMAPFile', True):
            flags.append('-Wl,-Map="' + self.output_name + '.map"')
        if self.key_as_bool(prefix + 'general.UseNewlibNano'):
            flags.append('--specs=nano.specs')
        # AdditionalSpecs: if you want it - read it from './/armgcc.linker.general.AdditionalSpecs'
        # Libraries
        inc_libs = self.key_as_strlist(prefix + 'libraries.Libraries', '{}')
        for ref_lib in self.ref_libs:
            inc_libs.append(ref_lib.raw_name)
        inc_libs_group = ''
        for inc_lib in inc_libs:
            inc_libs_group += ' -l' + RefLibrary.extract_name(inc_lib)
        flags.append('-Wl,--start-group{} -Wl,--end-group'.format(inc_libs_group))
        flags += self.key_as_strlist(prefix + 'libraries.LibrarySearchPaths', '-L"{}"')
        for lib in self.ref_libs:
            flags.append('-L"../{}/{}"'.format(lib.path, outdir))
        # Optimization
        if self.key_as_bool(prefix + 'optimization.GarbageCollectUnusedSections'):
            flags.append('-Wl,--gc-sections')
        if self.key_as_bool(prefix + 'optimization.EnableUnsafeMatchOptimizations'):
            flags.append('-funsafe-math-optimizations')
        if self.key_as_bool(prefix + 'optimization.EnableFastMath'):
            flags.append('-ffast-math')
        if self.key_as_bool(prefix + 'optimization.GeneratePositionIndependentCode'):
            flags.append('-fpic')
        # Memory Settings
        # Miscellaneous
        flags.append(self.key_as_str(prefix + 'miscellaneous.LinkerFlags', '{}'))
        flags += self.key_as_strlist(prefix + 'miscellaneous.OtherOptions', '-Xlinker {}')
        flags += self.key_as_strlist(prefix + 'miscellaneous.OtherObjects', '{}')
        return flags

    def archiver_flags(self):
        assert self.config_group is not None
        flags = []
        prefix = self.toolchain_settings.lower() + '.archiver.'
        flags.append(self.key_as_str(prefix + 'general.ArchiverFlags', '{}', '-r'))
        return flags


class RefLibrary(object):
    LIB_PREFIX = 'lib'
    LIB_EXT = '.a'

    def __init__(self, path, raw_name):
        assert raw_name.find(self.LIB_PREFIX) == -1
        assert raw_name.find(self.LIB_EXT) == -1
        self.path = path
        self.raw_name = raw_name

    def lib_name(self, with_ext=False):
        if with_ext:
            return self.LIB_PREFIX + self.raw_name + self.LIB_EXT
        else:
            return self.LIB_PREFIX + self.raw_name

    def full_name(self, config):
        return '{}/{}/{}'.format(self.path, config, self.lib_name(True))

    @classmethod
    def extract_name(cls, lib_name):
        s = lib_name
        if cls.LIB_PREFIX in s:
            s = s[len(cls.LIB_PREFIX):]
        if s.endswith(cls.LIB_EXT):
            s = s[:len(s) - len(cls.LIB_EXT)]
        return s


def strip_updir(file_name):
    """Strips all '../' from start of file_name"""
    fn = file_name
    while fn.find('..', 0) == 0:
        fn = fn[3:]
    return fn


def detect_linker_script(lflags):
    """Search '-T' params in lflags, strips first '../' from finded value"""
    linker_script = None
    for lflag in lflags:
        pos = lflag.find('-T')
        if pos != -1:
            linker_script = lflag[pos + len('-T'):]
            pos = linker_script.find(' ')
            if pos != -1:
                linker_script = linker_script[:pos]
            # linker script in linker flags is relative to makefile (build dir) - striping '../'
            linker_script = linker_script[3:]
    return linker_script


def convert(as_prj, config, outpath, output, flags, add_defs, del_defs, custom_toolchain=None):
    asp = AtmelStudioProject(as_prj, output)

    if custom_toolchain:
        toolchain = GccToolchain(custom_toolchain)
    else:
        toolchain = AtmelStudioGccToolchain.from_project(asp)
    cc = toolchain.cc()
    cxx = toolchain.cxx()
    link_cc = cc
    link_cxx = cxx
    ar = toolchain.ar()

    ccflags = [] + ninja_syntax.as_list(flags)
    cxxflags = [] + ninja_syntax.as_list(flags)
    lflags = [] + ninja_syntax.as_list(flags)
    arflags = []

    __, outdir = os.path.split(outpath)

    if asp.select_config(config):
        # ARM/GNU C Compiler
        ccflags += asp.compiler_flags('armgcc', add_defs, del_defs, [])
        # ARM/GNU C++ Compiler
        if asp.is_cpp:
            cxxflags += asp.compiler_flags('armgcccpp', add_defs, del_defs, [])
        if asp.is_lib:
            # ARM/GNU Archiver
            arflags += asp.archiver_flags()
        else:
            # ARM/GNU Linker
            lflags += asp.linker_flags(outdir)

    os.makedirs(outpath, exist_ok=True)
    nw = ninja_syntax.Writer(open(os.path.join(outpath, 'build.ninja'), 'w'), 120)

    nw.variable('ninja_required_version', '1.3')
    nw.newline()

    nw.variable('builddir', '.')
    nw.variable('src', '$builddir/..')
    nw.newline()

    if asp.ref_libs:
        for ref_lib in asp.ref_libs:
            nw.comment('subninja $builddir/../{}/{}/build.ninja'.format(ref_lib.path, outdir))
        nw.newline()

    nw.variable('ccflags', ccflags)
    nw.newline()

    nw.rule('cc',
            command=cc + ' -x c -c $ccflags -MD -MF $out.d -MT $out -o $out $in',
            description='cc $out',
            depfile='$out.d',
            deps='gcc')
    nw.newline()

    if asp.is_cpp:
        nw.variable('cxxflags', cxxflags)
        nw.newline()

        nw.rule('cxx',
                command=cxx + ' -c $cxxflags -MD -MF $out.d -MT $out -o $out $in',
                description='cxx $out',
                depfile='$out.d',
                deps='gcc')
        nw.newline()

    if asp.is_lib:
        nw.variable('arflags', arflags)
        nw.newline()

        nw.rule('ar',
                command=ar + ' $arflags -c -o $out $in',
                description='ar $out')
    else:
        nw.variable('lflags', lflags)
        nw.newline()

        link = link_cxx if asp.is_cpp else link_cc

        nw.rule('link',
                command=link + ' -o $out @$out.rsp $lflags',
                description='link $out',
                rspfile='$out.rsp',
                rspfile_content='$in')
    nw.newline()

    obj_files = []
    for src_file in asp.src_files():
        filename, file_ext = os.path.splitext(src_file)
        filename = strip_updir(filename)
        filename = '$builddir/' + filename + '.o'
        if file_ext == '.c':
            obj_files += nw.build(filename, 'cc', '$src/' + src_file)
        elif file_ext == '.cpp':
            assert asp.is_cpp
            obj_files += nw.build(filename, 'cxx', '$src/' + src_file)
        # else:
        #     print('Skipping file {}'.format(src_file))

    if obj_files:
        nw.newline()

        if asp.is_lib:
            def_target = nw.build('$builddir/' + asp.output(), 'ar', obj_files)
            nw.newline()
        else:
            implicit_dep = []
            #
            linker_script = detect_linker_script(lflags)
            if linker_script:
                print('linker_script = ' + linker_script)
                implicit_dep.append('$src/' + linker_script)
            #
            for lib in asp.ref_libs:
                implicit_dep.append('$builddir/../' + lib.full_name(outdir))

            def_target = nw.build('$builddir/' + asp.output(), 'link', obj_files,
                                  implicit=implicit_dep)
            nw.newline()

        nw.default(def_target)

    nw.close()


if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser(description='asninja')
    parser.add_argument('--prj', type=str, help='Atmel Studio project file')
    parser.add_argument('--config', type=str, help='Configuration (Debug, Release, ...)', default='Debug')
    parser.add_argument('--outpath', type=str, help='Output path (if absent when same as configuration name)',
                        default=None)
    parser.add_argument('--output', type=str, help='Output filename')
    parser.add_argument('--flags', type=str, help='Additional compiler and linker flags (like -mthumb)', default=None)
    parser.add_argument('--add_defs', type=str, help='Additional compiler defines (like __SAM4S8C__)', default=None)
    parser.add_argument('--del_defs', type=str, help='Defines to remove from compiler defines', default=None)
    parser.add_argument('--gcc_toolchain', type=str, help='Custom GCC toolchain path', default=None)

    # get all data from command line
    args = parser.parse_args()
    # print(args)

    _outpath = args.outpath if args.outpath else args.config
    _flags = args.flags.split(' ') if args.flags else []
    _add_defs = args.add_defs.split(' ') if args.add_defs else []
    _del_defs = args.del_defs.split(' ') if args.del_defs else []
    # print(_flags, _add_defs, _del_defs)

    convert(as_prj=args.prj, config=args.config, outpath=_outpath, output=args.output, flags=_flags,
            add_defs=_add_defs, del_defs=_del_defs, custom_toolchain=args.gcc_toolchain)
