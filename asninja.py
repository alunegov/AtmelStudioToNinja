import os
from xml.etree import ElementTree
import re
import ninja_syntax


class AtmelStudioProject(object):
    NSMAP = {'msb': 'http://schemas.microsoft.com/developer/msbuild/2003'}

    def __init__(self, file_name):
        self.prj = ElementTree.parse(file_name)
        self.config_group = None

    def select_config(self, config_name):
        self.config_group = None
        for group in self.prj.findall('msb:PropertyGroup', self.NSMAP):
            if group.attrib.get('Condition', '__none') == " '$(Configuration)' == '{}' ".format(config_name):
                self.config_group = group
                break
        return self.config_group is not None

    def key_raw(self, name):
        assert self.config_group is not None
        return self.config_group.find('.//msb:' + name, self.NSMAP)

    def key_as_bool(self, name, default=False):
        assert self.config_group is not None
        key = self.config_group.find('.//msb:' + name, self.NSMAP)
        if key is not None:
            return key.text == 'True'
        else:
            return default

    def key_as_str(self, name, fmt, default=''):
        assert self.config_group is not None
        key = self.config_group.find('.//msb:' + name, self.NSMAP)
        if key is not None:
            return fmt.format(key.text)
        else:
            return default

    def key_as_strlist(self, name, fmt):
        assert self.config_group is not None
        s = []
        for key in self.config_group.findall('.//msb:' + name + '/msb:ListValues/msb:Value', self.NSMAP):
            s.append(fmt.format(key.text))
        return s

    def src_files(self):
        src_files = []
        for node in self.prj.findall('.//msb:ItemGroup/msb:Compile', self.NSMAP):
            src_files.append(node.attrib['Include'].replace('\\', '/'))
        return src_files

    def ref_libs(self):
        ref_libs = []
        for node in self.prj.findall('.//msb:ItemGroup/msb:ProjectReference', self.NSMAP):
            print(node.attrib['Include'].replace('\\', '/'))
            #node.
            os.path.split()
            ref_libs.append(RefLibrary('', ''))
        return ref_libs


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
    fn = file_name
    while fn.find('..', 0) == 0:
        fn = fn[3:]
    return fn


def detect_linker_script(lflags):
    for lflag in lflags:
        pos = lflag.find('-T')
        if pos != -1:
            # linker script in linker flags is relative to makefile (build dir)
            return lflag[pos + 2 + 3:]


def convert(toolchain, prj, config, output, flags, defs, undefs, config_postfix=''):
    cc = os.path.join(toolchain, 'arm-none-eabi-gcc.exe')
    # cxx = os.path.join(toolchain, 'arm-none-eabi-g++.exe')
    link = os.path.join(toolchain, 'arm-none-eabi-gcc.exe')
    # ar = os.path.join(toolchain, 'arm-none-eabi-ar.exe')

    asp = AtmelStudioProject(prj)

    ccflags = [] + ninja_syntax.as_list(flags)
    lflags = [] + ninja_syntax.as_list(flags)

    asp.ref_libs()
    # ItemGroup/ProjectReference
    ref_libs = [
        RefLibrary('../Balancing', 'Balancing'),
        RefLibrary('../Center', 'Center'),
        RefLibrary('../HelpersInCppK3', 'HelpersInCppK3'),
        RefLibrary('../_ext/RosMath/project/RosMath_Static_AS62', 'RosMath_Static')
    ]

    if asp.select_config(config):
        # ARM/GNU C Compiler
        # General
        if asp.key_as_bool('armgcc.compiler.general.ChangeDefaultCharTypeUnsigned'):
            ccflags.append('-funsigned-char')
        if asp.key_as_bool('armgcc.compiler.general.ChangeDefaultBitFieldUnsigned'):
            ccflags.append('-funsigned-bitfields')
        # Preprocessor
        if asp.key_as_bool('armgcc.compiler.general.DoNotSearchSystemDirectories'):
            ccflags.append('-nostdinc')
        if asp.key_as_bool('armgcc.compiler.general.PreprocessOnly'):
            ccflags.append('-E')
        # Symbols
        inc_defs = ninja_syntax.as_list(defs)
        inc_defs += asp.key_as_strlist('armgcc.compiler.symbols.DefSymbols', '{}')
        for undef in ninja_syntax.as_list(undefs):
            if inc_defs.count(undef) > 0:
                assert inc_defs.count(undef) == 1
                inc_defs.remove(undef)
        ccflags.extend('-D{}'.format(inc_def) for inc_def in inc_defs)
        # Directories
        ccflags += asp.key_as_strlist('armgcc.compiler.directories.IncludePaths', '-I"{}"')
        # Optimization
        # Optimization Level: -O[0,1,2,3,s]
        key = asp.key_raw('armgcc.compiler.optimization.level')
        if key is not None:
            opt_level = re.search('(-O[0|1|2|3|s])', key.text)
            if opt_level:
                ccflags.append(opt_level.group(0))
        else:
            ccflags.append('-O0')
        ccflags += [asp.key_as_str('armgcc.compiler.optimization.OtherFlags', '{}')]
        if asp.key_as_bool('armgcc.compiler.optimization.PrepareFunctionsForGarbageCollection'):
            ccflags.append('-ffunction-sections')
        if asp.key_as_bool('armgcc.compiler.optimization.PrepareDataForGarbageCollection'):
            ccflags.append('-fdata-sections')
        if asp.key_as_bool('armgcc.compiler.optimization.EnableUnsafeMatchOptimizations'):
            ccflags.append('-funsafe-math-optimizations')
        if asp.key_as_bool('armgcc.compiler.optimization.EnableFastMath'):
            ccflags.append('-ffast-math')
        if asp.key_as_bool('armgcc.compiler.optimization.GeneratePositionIndependentCode'):
            ccflags.append('-fpic')
        if asp.key_as_bool('armgcc.compiler.optimization.EnableFastMath'):
            ccflags.append('-ffast-math')
        if asp.key_as_bool('armgcc.compiler.optimization.EnableLongCalls', True):
            ccflags.append('-mlong-calls')
        # Debugging
        # Debug Level: None and -g[1,2,3]
        key = asp.key_raw('armgcc.compiler.optimization.DebugLevel')
        if key is not None:
            debug_level = re.search('-g[1|2|3]', key.text)
            if debug_level:
                ccflags.append(debug_level.group(0))
        ccflags.append(asp.key_as_str('armgcc.compiler.optimization.OtherDebuggingFlags', '{}'))
        if asp.key_as_bool('armgcc.compiler.optimization.GenerateGprofInformation'):
            ccflags.append('-pg')
        if asp.key_as_bool('armgcc.compiler.optimization.GenerateProfInformation'):
            ccflags.append('-p')
        # Warnings
        if asp.key_as_bool('armgcc.compiler.warnings.AllWarnings'):
            ccflags.append('-Wall')
        if asp.key_as_bool('armgcc.compiler.warnings.ExtraWarnings'):
            ccflags.append('-Wextra')
        if asp.key_as_bool('armgcc.compiler.warnings.Undefined'):
            ccflags.append('-Wundef')
        if asp.key_as_bool('armgcc.compiler.warnings.WarningsAsErrors'):
            ccflags.append('-Werror')
        if asp.key_as_bool('armgcc.compiler.warnings.CheckSyntaxOnly'):
            ccflags.append('-fsyntax-only')
        if asp.key_as_bool('armgcc.compiler.warnings.Pedantic'):
            ccflags.append('-pedentic')
        if asp.key_as_bool('armgcc.compiler.warnings.PedanticWarningsAsErrors'):
            ccflags.append('-pedantic-errors')
        if asp.key_as_bool('armgcc.compiler.warnings.InhibitAllWarnings'):
            ccflags.append('-w')
        # Miscellaneous
        ccflags.append(asp.key_as_str('armgcc.compiler.miscellaneous.OtherFlags', '{}'))
        if asp.key_as_bool('armgcc.compiler.miscellaneous.Verbose'):
            ccflags.append('-v')
        if asp.key_as_bool('armgcc.compiler.miscellaneous.SupportAnsiPrograms'):
            ccflags.append('-ansi')
        # ARM/GNU Linker
        # General
        if asp.key_as_bool('armgcc.linker.general.DoNotUseStandardStartFiles'):
            lflags.append('-nostartfiles')
        if asp.key_as_bool('armgcc.linker.general.DoNotUseDefaultLibraries'):
            lflags.append('-nodefaultlibs')
        if asp.key_as_bool('armgcc.linker.general.NoStartupOrDefaultLibs'):
            lflags.append('-nostdlib')
        if asp.key_as_bool('armgcc.linker.general.OmitAllSymbolInformation'):
            lflags.append('-s')
        if asp.key_as_bool('armgcc.linker.general.NoSharedLibraries'):
            lflags.append('-static')
        if asp.key_as_bool('armgcc.linker.general.GenerateMAPFile', True):
            lflags.append('-Wl,-Map="' + output + '.map"')
        if asp.key_as_bool('armgcc.linker.general.UseNewlibNano'):
            lflags.append('--specs=nano.specs')
        # AdditionalSpecs: if you want it - read it from './/armgcc.linker.general.AdditionalSpecs'
        # Libraries
        inc_libs = asp.key_as_strlist('armgcc.linker.libraries.Libraries', '{}')
        for ref_lib in ref_libs:
            inc_libs.append(ref_lib.raw_name)
        inc_libs_group = ''
        for inc_lib in inc_libs:
            inc_libs_group += ' -l' + RefLibrary.extract_name(inc_lib)
        lflags.append('-Wl,--start-group{} -Wl,--end-group'.format(inc_libs_group))
        lflags += asp.key_as_strlist('armgcc.linker.libraries.LibrarySearchPaths', '-L"{}"')
        for lib in ref_libs:
            lflags.append('-L"../{}/{}"'.format(lib.path, config + config_postfix))
        # Optimization
        if asp.key_as_bool('armgcc.linker.optimization.GarbageCollectUnusedSections'):
            lflags.append('-Wl,--gc-sections')
        if asp.key_as_bool('armgcc.linker.optimization.EnableUnsafeMatchOptimizations'):
            lflags.append('-funsafe-math-optimizations')
        if asp.key_as_bool('armgcc.linker.optimization.EnableFastMath'):
            lflags.append('-ffast-math')
        if asp.key_as_bool('armgcc.linker.optimization.GeneratePositionIndependentCode'):
            lflags.append('-fpic')
        # Memory Settings
        # Miscellaneous
        lflags.append(asp.key_as_str('armgcc.linker.miscellaneous.LinkerFlags', '{}'))
        lflags += asp.key_as_strlist('armgcc.linker.miscellaneous.OtherOptions', '-Xlinker {}')
        lflags += asp.key_as_strlist('armgcc.linker.miscellaneous.OtherObjects', '{}')

    nw = ninja_syntax.Writer(open(os.path.join(config + config_postfix, 'build.ninja'), 'w'), 120)

    nw.variable('ninja_required_version', '1.3')
    nw.newline()

    nw.variable('builddir', '.')
    nw.variable('src', '$builddir/..')
    nw.newline()

    for ref_lib in ref_libs:
        nw.comment('subninja $builddir/../{}/{}/build.ninja'.format(ref_lib.path, config + config_postfix))
    nw.newline()

    nw.variable('ccflags', ccflags)
    nw.newline()
    nw.variable('lflags', lflags)
    nw.newline()

    nw.rule('cc',
            command=cc + ' -x c -c $ccflags -MD -MF $out.d -MT $out -o $out $in',
            description='cc $out',
            depfile='$out.d',
            deps='gcc')
    nw.newline()

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
                obj_files += nw.build('$builddir/' + filename + '.o', 'cxx', '$src/' + src_file)
            # else:
                # print('Skipping file {}'.format(src_file))

    implicit_dep = []
    #
    linker_script = detect_linker_script(lflags)
    if linker_script:
        print('linker_script = ' + linker_script)
        implicit_dep.append('$src/' + linker_script)
    #
    for lib in ref_libs:
        implicit_dep.append('$builddir/../' + lib.full_name(config + config_postfix))

    if obj_files:
        nw.newline()
        nw.build('$builddir/' + output + '.elf', 'link', obj_files,
                 implicit=implicit_dep)
        nw.newline()

    nw.default('$builddir/' + output + '.elf')

    nw.close()


if __name__ == '__main__':
    toolchain_path = 'C:/Program Files (x86)/Atmel/Atmel Toolchain/ARM GCC/Native/4.8.1437/arm-gnu-toolchain/bin'
    config_name = 'Debug'
    add_flags = ['-mthumb', '-mcpu=cortex-m4']
    add_defs = ['__SAM4S8C__']
    del_defs = []

    convert(toolchain=toolchain_path,
            prj=os.path.join('tests', 'Korsar3.cproj'),
            config=config_name,
            output='Korsar3',
            flags=add_flags,
            defs=add_defs,
            undefs=del_defs,
            config_postfix='')
