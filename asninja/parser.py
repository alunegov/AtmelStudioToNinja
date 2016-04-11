import os
import re
from xml.etree import ElementTree

import asninja.helpers


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
        self.toolchain_settings = 'ArmGccCpp' if self.is_cpp else 'ArmGcc'
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
        return key.text == 'True' if key is not None else default

    def key_as_str(self, name, fmt, default=''):
        assert self.config_group is not None
        key = self.key_raw(name)
        return fmt.format(key.text) if key is not None else default

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

    def compiler_flags(self, c_compiler, add_defs, del_defs, add_undefs):
        assert self.config_group is not None
        assert isinstance(add_defs, list)
        assert isinstance(del_defs, list)
        assert isinstance(add_undefs, list)
        flags = []
        prefix = 'armgcc' if c_compiler else 'armgcccpp'
        prefix += '.compiler.'
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
        inc_defs = asninja.helpers.strip_empty_symbols(add_defs)
        inc_defs += self.key_as_strlist(prefix + 'symbols.DefSymbols', '{}')
        for del_def in del_defs:
            if inc_defs.count(del_def) > 0:
                assert inc_defs.count(del_def) == 1
                inc_defs.remove(del_def)
        flags.extend('-D{}'.format(inc_def) for inc_def in inc_defs)
        inc_undefs = asninja.helpers.strip_empty_symbols(add_undefs)
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
            flags.append('-pedantic')
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
