import sys
import os
from xml.etree import ElementTree
import re
import ninja_syntax


def reg_read(key):
    s = 'C:\\Program Files (x86)\\Atmel\\Studio\\7.0\\toolchain\\arm\\arm-gnu-toolchain\\bin'
    return s.replace('\\', '/')


class Toolchain(object):
    def toolchain(self):
        pass

    def cc(self):
        pass

    def cxx(self):
        pass


class AtmelStudioToolchain(Toolchain):
    AS_REG = 'HKEY_CURRENT_USER\Software\Atmel\AtmelStudio'
    AS_DIR_REG = AS_REG + '\{}_Config\InstallDir'
    USER_TOOLCHAIN_REG = AS_REG + '\{}\ToolchainPackages\{}\{}\BasePath'
    TOOLCHAIN_NAMES = ['ARMGCC', 'AVR32GCC', 'AVR8GCC']

    def __init__(self, prj_version, name, flavour):
        self.prj_version = prj_version
        # self.name = name
        self.name = 'ARMGCC'
        self.flavour = flavour

    @classmethod
    def detect(cls, prj_version, name, flavour):
        if prj_version == '6.2':
            return AtmelStudio62Toolchain(prj_version, name, flavour)
        else:
            if prj_version == '7.0':
                return AtmelStudio70Toolchain(prj_version, name, flavour)
            else:
                assert False, 'Unsupported project version'

    def toolchain(self):
        if self.flavour == 'Native':
            as_dir = ''  # reg_read(self.AS_DIR_REG.format(self.prj_version)).replace('\\', '/')
            path = as_dir + self.native_suffix()
        else:
            path = reg_read(self.USER_TOOLCHAIN_REG.format(self.prj_version, self.name, self.flavour))
        return path

    def native_suffix(self) -> str:
        pass

    def tool_prefix(self):
        prefixes = ['arm-none-eabi-', 'avr32-', 'avr8-']
        tool_type = self.TOOLCHAIN_NAMES.index(self.name)
        return prefixes[tool_type]

    def cc(self):
        return self.toolchain() + '/' + self.tool_prefix() + 'gcc'

    def cxx(self):
        return self.toolchain() + '/' + self.tool_prefix() + 'g++'


class AtmelStudio62Toolchain(AtmelStudioToolchain):
    SUFFIXES = ['../Atmel Toolchain/ARM GCC/Native/4.8.1437/arm-gnu-toolchain/bin',
                '../Atmel Toolchain/AVR32 GCC/Native/3.4.1067/avr32-gnu-toolchain/bin',
                '../Atmel Toolchain/AVR8 GCC/Native/3.4.1061/avr8-gnu-toolchain/bin']

    def native_suffix(self) -> str:
        tool_type = self.TOOLCHAIN_NAMES.index(self.name)
        return self.SUFFIXES[tool_type]


class AtmelStudio70Toolchain(AtmelStudioToolchain):
    SUFFIXES = ['toolchain/arm/arm-gnu-toolchain/bin',
                'toolchain/avr32/avr32-gnu-toolchain/bin',
                'toolchain/avr8/avr8-gnu-toolchain/bin']

    def native_suffix(self) -> str:
        tool_type = self.TOOLCHAIN_NAMES.index(self.name)
        return self.SUFFIXES[tool_type]


class ClangToolchain(Toolchain):
    pass


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
        if self.prj:
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
                path, prj_name = os.path.split(node.attrib['Include'].replace('\\', '/'))
                raw_name, __ = os.path.splitext(prj_name)
                self.ref_libs.append(RefLibrary(path, raw_name))

    def output(self):
        assert self.output_name is not None
        assert self.output_ext
        return self.output_name + self.output_ext

    def toolchain(self):
        key = self.prj.find('.//msb:PropertyGroup/msb:ProjectVersion', self.NSMAP)
        prj_version = key.text
        key = self.prj.find('.//msb:PropertyGroup/msb:ToolchainName', self.NSMAP)
        toolchain_name = key.text
        key = self.prj.find('.//msb:PropertyGroup/msb:ToolchainFlavour', self.NSMAP)
        toolchain_flavour = key.text

        ast = AtmelStudioToolchain.detect(prj_version, toolchain_name, toolchain_flavour)

        return ast.toolchain()

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


def convert(toolchain_path, as_prj, config, outpath, output, flags, add_defs, del_defs):
    cc = os.path.join(toolchain_path, 'arm-none-eabi-gcc.exe')
    cxx = os.path.join(toolchain_path, 'arm-none-eabi-g++.exe')
    link_cc = cc
    link_cxx = cxx
    ar = os.path.join(toolchain_path, 'arm-none-eabi-ar.exe')

    __, outdir = os.path.split(outpath)

    asp = AtmelStudioProject(as_prj, output)

    ccflags = [] + ninja_syntax.as_list(flags)
    cxxflags = [] + ninja_syntax.as_list(flags)
    lflags = [] + ninja_syntax.as_list(flags)
    arflags = []

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

        if asp.is_cpp:
            link = link_cxx
        else:
            link = link_cc

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
        if file_ext == '.c':
            obj_files += nw.build('$builddir/' + filename + '.o', 'cc', '$src/' + src_file)
        else:
            if file_ext == '.cpp':
                assert asp.is_cpp
                obj_files += nw.build('$builddir/' + filename + '.o', 'cxx', '$src/' + src_file)
                # else:
                # print('Skipping file {}'.format(src_file))

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
    _toolchain_path = 'C:/Program Files (x86)/Atmel/Atmel Toolchain/ARM GCC/Native/4.8.1437/arm-gnu-toolchain/bin'
    if len(sys.argv) > 1:
        _as_prj = sys.argv[1]
        _config = sys.argv[2]
        _outpath = sys.argv[3]
        _output = sys.argv[4]
        _flags = sys.argv[5].split(' ')
        if len(sys.argv) > 6:
            _add_defs = sys.argv[6].split(' ')
        else:
            _add_defs = []
        _del_defs = []
    else:
        _as_prj = os.path.join('tests', 'Korsar3.cproj')
        _config = 'Debug'
        _outpath = _config
        _output = 'Korsar3'
        _flags = ['-mthumb', '-mcpu=cortex-m4']
        _add_defs = ['__SAM4S8C__']
        _del_defs = []

    convert(toolchain_path=_toolchain_path,
            as_prj=_as_prj,
            config=_config,
            outpath=_outpath,
            output=_output,
            flags=_flags,
            add_defs=_add_defs,
            del_defs=_del_defs)
