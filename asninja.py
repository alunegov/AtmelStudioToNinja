import os
from xml.etree import ElementTree
import re
import ninja_syntax


class AtmelStudioProject(object):
    def __init__(self, file_name):
        self.NSMAP = {'msb': 'http://schemas.microsoft.com/developer/msbuild/2003'}
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

    def key_as_str_array(self, name, fmt):
        assert self.config_group is not None
        s = []
        for key in self.config_group.findall('.//msb:' + name + '/msb:ListValues/msb:Value', self.NSMAP):
            s.append(fmt.format(key.text))
        return s

    def src_files(self):
        src_files = []
        src_files_group = self.prj.getroot()[4]
        if src_files_group is not None:
            for node in src_files_group.findall('msb:Compile', self.NSMAP):
                src_files.append(node.attrib['Include'].replace('\\', '/'))
        return src_files


class RefLibrary(object):
    def __init__(self, path, name):
        self.path = path
        self.name = name

    def lib_name(self):
        return 'lib' + self.name

    def full_name(self):
        return '{}/{}.a'.format(self.path, self.lib_name())

    @classmethod
    def extract_name(cls, lib_name):
        # assert lib_name.lenght() > 3
        return lib_name[3:]


def strip_updir(file_name):
    fn = file_name
    while fn.find('..', 0) == 0:
        fn = fn[3:]
    return fn


def detect_linker_script(lflags):
    for lflag in lflags:
        pos = lflag.find('-T')
        if pos != -1:
            return lflag[pos + 2:]


def convert(toolchain, prj, config, output):
    cc = os.path.join(toolchain, 'arm-none-eabi-gcc.exe')
    # cxx = os.path.join(toolchain, 'arm-none-eabi-g++.exe')
    link = os.path.join(toolchain, 'arm-none-eabi-gcc.exe')
    # ar = os.path.join(toolchain, 'arm-none-eabi-ar.exe')

    asp = AtmelStudioProject(prj)

    ccflags = ['-mthumb', '-mcpu=cortex-m4', '-D__SAM4S8C__']
    lflags = ['-mthumb', '-mcpu=cortex-m4']

    ref_libs = [
        RefLibrary('C:/Work/Korsar3Mini-trunk/Balancing/Debug', 'Balancing'),
        RefLibrary('C:/Work/Korsar3Mini-trunk/Center/Debug', 'Center'),
        RefLibrary('C:/Work/Korsar3Mini-trunk/HelpersInCppK3/Debug', 'HelpersInCppK3'),
        RefLibrary('C:/Work/Korsar3Mini-trunk/_ext/RosMath/project/RosMath_Static_AS62/Debug', 'RosMath_Static')
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
        ccflags += asp.key_as_str_array('armgcc.compiler.symbols.DefSymbols', '-D{}')
        # Directories
        ccflags += asp.key_as_str_array('armgcc.compiler.directories.IncludePaths', '-I"{}"')
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
        prj_libs = asp.key_as_str_array('armgcc.linker.libraries.Libraries', '{}')
        inc_libs = []
        for lib in prj_libs:
            inc_libs.append('-l' + RefLibrary.extract_name(lib))
        for lib in ref_libs:
            inc_libs.append('-l' + lib.name)
        lflags.append('-Wl,--start-group {} -Wl,--end-group'.format(' '.join(inc_libs)))
        lflags += asp.key_as_str_array('armgcc.linker.libraries.LibrarySearchPaths', '-L"{}"')
        for lib in ref_libs:
            lflags.append('-L"{}"'.format(lib.path))
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
        lflags += asp.key_as_str_array('armgcc.linker.miscellaneous.OtherOptions', '-Xlinker {}')
        lflags += asp.key_as_str_array('armgcc.linker.miscellaneous.OtherObjects', '{}')

    nw = ninja_syntax.Writer(open('build.ninja', 'w'), 120)

    nw.variable('ninja_required_version', '1.3')
    nw.newline()

    nw.variable('root', '..')
    nw.variable('builddir', 'build')
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
            obj_files += nw.build('$builddir/' + filename + '.o', 'cc', '$root/' + src_file)
        else:
            if file_ext == '.cpp':
                obj_files += nw.build('$builddir/' + filename + '.o', 'cxx', '$root/' + src_file)
            # else:
                # print('Skipping file {}'.format(src_file))

    implicit_dep = []
    #
    linker_script = detect_linker_script(lflags)
    if linker_script:
        print('linker_script =' + linker_script)
        implicit_dep.append(linker_script)
    #
    for lib in ref_libs:
        implicit_dep.append(lib.full_name())

    if obj_files:
        nw.newline()
        nw.build(output + '.elf', 'link', obj_files,
                 implicit=implicit_dep)
        nw.newline()

    nw.build('all', 'phony', output + '.elf')
    nw.newline()

    nw.default('all')

    nw.close()


if __name__ == '__main__':
    toolchain_path = 'C:/Program Files (x86)/Atmel/Atmel Toolchain/ARM GCC/Native/4.8.1437/arm-gnu-toolchain/bin'

    convert(toolchain_path, os.path.join('tests', 'Korsar3.cproj'), 'Debug', 'Korsar3')
