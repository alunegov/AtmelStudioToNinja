import os
from xml.etree import ElementTree
import re
import ninja_syntax

def get_config_group(prj, config_name):
    for group in prj.findall('PropertyGroup'):
        if group.attrib.get('Condition', '__none') == " '$(Configuration)' == '{}' ".format(config_name):
            return group


def get_src_files_group(prj):
    return prj.getroot()[4]


def get_key_as_str(config, name, fmt, default=''):
    key = config.find('.//' + name)
    if key is not None:
        return fmt.format(key.text)
    else:
        return default


def get_key_as_bool(config, name, default=False):
    key = config.find('.//' + name)
    if key is not None:
        return key.text == 'True'
    else:
        return default


def get_key_as_strarray(config, name, fmt):
    s = []
    for key in config.findall('.//' + name + '/ListValues/Value'):
        s.append(fmt.format(key.text))
    return s


cc = 'C:/Program Files (x86)/Atmel/Atmel Toolchain/ARM GCC/Native/4.8.1437/arm-gnu-toolchain/bin/arm-none-eabi-gcc.exe'
cxx = 'C:/Program Files (x86)/Atmel/Atmel Toolchain/ARM GCC/Native/4.8.1437/arm-gnu-toolchain/bin/arm-none-eabi-g++.exe'
link = 'C:/Program Files (x86)/Atmel/Atmel Toolchain/ARM GCC/Native/4.8.1437/arm-gnu-toolchain/bin/arm-none-eabi-gcc.exe'
ar = 'C:/Program Files (x86)/Atmel/Atmel Toolchain/ARM GCC/Native/4.8.1437/arm-gnu-toolchain/bin/arm-none-eabi-ar.exe'

asProject = ElementTree.parse(os.path.join('tests', 'Korsar3.cproj'))
nw = ninja_syntax.Writer(open('build.ninja', 'w'), 120)

nw.variable('ninja_required_version', '1.3')
nw.newline()

nw.variable('root', '..')
nw.variable('builddir', 'build')
nw.newline()

output = 'Korsar3'
ccflags = ['-mthumb', '-mcpu=cortex-m4', '-D__SAM4S8C__']
lflags = ['-mthumb', '-mcpu=cortex-m4']

config_group = get_config_group(asProject, 'Debug')
if config_group is not None:
    # ARM/GNU C Compiler
    # General
    if get_key_as_bool(config_group, 'armgcc.compiler.general.ChangeDefaultCharTypeUnsigned'):
        ccflags.append('-funsigned-char')
    if get_key_as_bool(config_group, 'armgcc.compiler.general.ChangeDefaultBitFieldUnsigned'):
        ccflags.append('-funsigned-bitfields')
    # Preprocessor
    if get_key_as_bool(config_group, 'armgcc.compiler.general.DoNotSearchSystemDirectories'):
        ccflags.append('-nostdinc')
    if get_key_as_bool(config_group, 'armgcc.compiler.general.PreprocessOnly'):
        ccflags.append('-E')
    # Symbols
    ccflags += get_key_as_strarray(config_group, 'armgcc.compiler.symbols.DefSymbols', '-D{}')
    # Directories
    ccflags += get_key_as_strarray(config_group, 'armgcc.compiler.directories.IncludePaths', '-I"{}"')
    # Optimization
    # Optimization Level: -O[0,1,2,3,s]
    item = config_group.find('.//armgcc.compiler.optimization.level')
    if item is not None:
        opt_level = re.search('(-O[0|1|2|3|s])', item.text)
        if opt_level:
            ccflags.append(opt_level.group(0))
    else:
        ccflags.append('-O0')
    ccflags += [get_key_as_str(config_group, 'armgcc.compiler.optimization.OtherFlags', '{}')]
    if get_key_as_bool(config_group, 'armgcc.compiler.optimization.PrepareFunctionsForGarbageCollection'):
        ccflags.append('-ffunction-sections')
    if get_key_as_bool(config_group, 'armgcc.compiler.optimization.PrepareDataForGarbageCollection'):
        ccflags.append('-fdata-sections')
    if get_key_as_bool(config_group, 'armgcc.compiler.optimization.EnableUnsafeMatchOptimizations'):
        ccflags.append('-funsafe-math-optimizations')
    if get_key_as_bool(config_group, 'armgcc.compiler.optimization.EnableFastMath'):
        ccflags.append('-ffast-math')
    if get_key_as_bool(config_group, 'armgcc.compiler.optimization.GeneratePositionIndependentCode'):
        ccflags.append('-fpic')
    if get_key_as_bool(config_group, 'armgcc.compiler.optimization.EnableFastMath'):
        ccflags.append('-ffast-math')
    if get_key_as_bool(config_group, 'armgcc.compiler.optimization.EnableLongCalls', True):
        ccflags.append('-mlong-calls')
    # Debugging
    # Debug Level: None and -g[1,2,3]
    item = config_group.find('.//armgcc.compiler.optimization.DebugLevel')
    if item is not None:
        debug_level = re.search('-g[1|2|3]', item.text)
        if debug_level:
            ccflags.append(debug_level.group(0))
    ccflags.append(get_key_as_str(config_group, 'armgcc.compiler.optimization.OtherDebuggingFlags', '{}'))
    if get_key_as_bool(config_group, 'armgcc.compiler.optimization.GenerateGprofInformation'):
        ccflags.append('-pg')
    if get_key_as_bool(config_group, 'armgcc.compiler.optimization.GenerateProfInformation'):
        ccflags.append('-p')
    # Warnings
    if get_key_as_bool(config_group, 'armgcc.compiler.warnings.AllWarnings'):
        ccflags.append('-Wall')
    if get_key_as_bool(config_group, 'armgcc.compiler.warnings.ExtraWarnings'):
        ccflags.append('-Wextra')
    if get_key_as_bool(config_group, 'armgcc.compiler.warnings.Undefined'):
        ccflags.append('-Wundef')
    if get_key_as_bool(config_group, 'armgcc.compiler.warnings.WarningsAsErrors'):
        ccflags.append('-Werror')
    if get_key_as_bool(config_group, 'armgcc.compiler.warnings.CheckSyntaxOnly'):
        ccflags.append('-fsyntax-only')
    if get_key_as_bool(config_group, 'armgcc.compiler.warnings.Pedantic'):
        ccflags.append('-pedentic')
    if get_key_as_bool(config_group, 'armgcc.compiler.warnings.PedanticWarningsAsErrors'):
        ccflags.append('-pedantic-errors')
    if get_key_as_bool(config_group, 'armgcc.compiler.warnings.InhibitAllWarnings'):
        ccflags.append('-w')
    # Miscellaneous
    ccflags.append(get_key_as_str(config_group, 'armgcc.compiler.miscellaneous.OtherFlags', '{}'))
    if get_key_as_bool(config_group, 'armgcc.compiler.miscellaneous.Verbose'):
        ccflags.append('-v')
    if get_key_as_bool(config_group, 'armgcc.compiler.miscellaneous.SupportAnsiPrograms'):
        ccflags.append('-ansi')
    # ARM/GNU Linker
    # General
    if get_key_as_bool(config_group, 'armgcc.linker.general.DoNotUseStandardStartFiles'):
        lflags.append('-nostartfiles')
    if get_key_as_bool(config_group, 'armgcc.linker.general.DoNotUseDefaultLibraries'):
        lflags.append('-nodefaultlibs')
    if get_key_as_bool(config_group, 'armgcc.linker.general.NoStartupOrDefaultLibs'):
        lflags.append('-nostdlib')
    if get_key_as_bool(config_group, 'armgcc.linker.general.OmitAllSymbolInformation'):
        lflags.append('-s')
    if get_key_as_bool(config_group, 'armgcc.linker.general.NoSharedLibraries'):
        lflags.append('-static')
    if get_key_as_bool(config_group, 'armgcc.linker.general.GenerateMAPFile', True):
        lflags.append('-Wl,-Map="' + output + '.map"')
    if get_key_as_bool(config_group, 'armgcc.linker.general.UseNewlibNano'):
        lflags.append('--specs=nano.specs')
    # AdditionalSpecs: if you want it - read it from './/armgcc.linker.general.AdditionalSpecs'
    # Libraries
    lflags.append('-Wl,--start-group -lm -lBalancing -lCenter -lHelpersInCppK3 -lRosMath_Static -Wl,--end-group')
    lflags += get_key_as_strarray(config_group, 'armgcc.linker.libraries.LibrarySearchPaths', '-L"{}"')
    lflags.append('-L"C:/Work/Korsar3Mini-trunk/Balancing/Debug"')
    lflags.append('-L"C:/Work/Korsar3Mini-trunk/Center/Debug"')
    lflags.append('-L"C:/Work/Korsar3Mini-trunk/HelpersInCppK3/Debug"')
    lflags.append('-L"C:/Work/Korsar3Mini-trunk/_ext/RosMath/project/RosMath_Static_AS62/Debug"')
    # Optimization
    if get_key_as_bool(config_group, 'armgcc.linker.optimization.GarbageCollectUnusedSections'):
        lflags.append('-Wl,--gc-sections')
    if get_key_as_bool(config_group, 'armgcc.linker.optimization.EnableUnsafeMatchOptimizations'):
        lflags.append('-funsafe-math-optimizations')
    if get_key_as_bool(config_group, 'armgcc.linker.optimization.EnableFastMath'):
        lflags.append('-ffast-math')
    if get_key_as_bool(config_group, 'armgcc.linker.optimization.GeneratePositionIndependentCode'):
        lflags.append('-fpic')
    # Memory Settings
    # Miscellaneous
    lflags.append(get_key_as_str(config_group, 'armgcc.linker.miscellaneous.LinkerFlags', '{}'))
    lflags += get_key_as_strarray(config_group, 'armgcc.linker.miscellaneous.OtherOptions', '-Xlinker {}')
    lflags += get_key_as_strarray(config_group, 'armgcc.linker.miscellaneous.OtherObjects', '{}')

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

src_files_group = get_src_files_group(asProject)
obj_files = []
if src_files_group is not None:
    for item in src_files_group.findall('Compile'):
        file = item.attrib['Include'].replace('\\', '/')
        filename, file_ext = os.path.splitext(file)
        while filename.find('..') == 0:
            filename = filename[3:]
        if file_ext == '.c':
            obj_files += nw.build('$builddir/' + filename + '.o', 'cc', '$root/' + file)
        else:
            if file_ext == '.cpp':
                obj_files += nw.build('$builddir/' + filename + '.o', 'cxx', '$root/' + file)
            # else:
                # print('Skipping file {}'.format(file))
    nw.newline()

linker_script = ''
for lflag in lflags:
    pos = lflag.find(' -T')
    if pos != -1:
        linker_script = lflag[pos + 3:]
print('linker_script =' + linker_script)

nw.build(output + '.elf', 'link', obj_files,
         implicit=[linker_script])
nw.newline()

nw.build('all', 'phony', output + '.elf')
nw.newline()

nw.default('all')

nw.close()
