import os
from xml.etree import ElementTree
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
    s = ''
    for key in config.findall('.//' + name + '/ListValues/Value'):
        s += fmt.format(key.text)
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
ccflags = '-mthumb -mcpu=cortex-m4 -D__SAM4S8C__'
lflags = '-mthumb -mcpu=cortex-m4'

config_group = get_config_group(asProject, 'Debug')
if config_group is not None:
    # ARM/GNU C Compiler
    # General
    if get_key_as_bool(config_group, 'armgcc.compiler.general.ChangeDefaultCharTypeUnsigned'):
        ccflags += ' -funsigned-char'
    if get_key_as_bool(config_group, 'armgcc.compiler.general.ChangeDefaultBitFieldUnsigned'):
        ccflags += ' -funsigned-bitfields'
    # Preprocessor
    if get_key_as_bool(config_group, 'armgcc.compiler.general.DoNotSearchSystemDirectories'):
        ccflags += ' -nostdinc'
    if get_key_as_bool(config_group, 'armgcc.compiler.general.PreprocessOnly'):
        ccflags += ' -E'
    # Symbols
    ccflags += get_key_as_strarray(config_group, 'armgcc.compiler.symbols.DefSymbols', ' -D{}')
    # Directories
    ccflags += get_key_as_strarray(config_group, 'armgcc.compiler.directories.IncludePaths', ' -I"{}"')
    # Optimization
    # Optimization Level: -O[0,1,2,3,s]
    item = config_group.find('.//armgcc.compiler.optimization.level')
    if item is not None:
        if item.text.find('-O0') != -1:
            ccflags += ' -O0'
    ccflags += get_key_as_str(config_group, 'armgcc.compiler.optimization.OtherFlags', ' {}')
    if get_key_as_bool(config_group, 'armgcc.compiler.optimization.PrepareFunctionsForGarbageCollection'):
        ccflags += ' -ffunction-sections'
    if get_key_as_bool(config_group, 'armgcc.compiler.optimization.PrepareDataForGarbageCollection'):
        ccflags += ' -fdata-sections'
    if get_key_as_bool(config_group, 'armgcc.compiler.optimization.EnableUnsafeMatchOptimizations'):
        ccflags += ' -funsafe-math-optimizations'
    if get_key_as_bool(config_group, 'armgcc.compiler.optimization.EnableFastMath'):
        ccflags += ' -ffast-math'
    if get_key_as_bool(config_group, 'armgcc.compiler.optimization.GeneratePositionIndependentCode'):
        ccflags += ' -fpic'
    if get_key_as_bool(config_group, 'armgcc.compiler.optimization.EnableFastMath'):
        ccflags += ' -ffast-math'
    if get_key_as_bool(config_group, 'armgcc.compiler.optimization.EnableLongCalls', True):
        ccflags += ' -mlong-calls'
    # Debugging
    # Debug Level: None and -g[1,2,3]
    item = config_group.find('.//armgcc.compiler.optimization.DebugLevel')
    if item is not None:
        if item.text.find('-g3') != -1:
            ccflags += ' -g3'
    ccflags += get_key_as_str(config_group, 'armgcc.compiler.optimization.OtherDebuggingFlags', ' {}')
    if get_key_as_bool(config_group, 'armgcc.compiler.optimization.GenerateGprofInformation'):
        ccflags += ' -pg'
    if get_key_as_bool(config_group, 'armgcc.compiler.optimization.GenerateProfInformation'):
        ccflags += ' -p'
    # Warnings
    if get_key_as_bool(config_group, 'armgcc.compiler.warnings.AllWarnings'):
        ccflags += ' -Wall'
    if get_key_as_bool(config_group, 'armgcc.compiler.warnings.ExtraWarnings'):
        ccflags += ' -Wextra'
    if get_key_as_bool(config_group, 'armgcc.compiler.warnings.Undefined'):
        ccflags += ' -Wundef'
    if get_key_as_bool(config_group, 'armgcc.compiler.warnings.WarningsAsErrors'):
        ccflags += ' -Werror'
    if get_key_as_bool(config_group, 'armgcc.compiler.warnings.CheckSyntaxOnly'):
        ccflags += ' -fsyntax-only'
    if get_key_as_bool(config_group, 'armgcc.compiler.warnings.Pedantic'):
        ccflags += ' -pedentic'
    if get_key_as_bool(config_group, 'armgcc.compiler.warnings.PedanticWarningsAsErrors'):
        ccflags += ' -pedantic-errors'
    if get_key_as_bool(config_group, 'armgcc.compiler.warnings.InhibitAllWarnings'):
        ccflags += ' -w'
    # Miscellaneous
    ccflags += get_key_as_str(config_group, 'armgcc.compiler.miscellaneous.OtherFlags', ' {}')
    if get_key_as_bool(config_group, 'armgcc.compiler.miscellaneous.Verbose'):
        ccflags += ' -v'
    if get_key_as_bool(config_group, 'armgcc.compiler.miscellaneous.SupportAnsiPrograms'):
        ccflags += ' -ansi'
    # ARM/GNU Linker
    # General
    if get_key_as_bool(config_group, 'armgcc.linker.general.DoNotUseStandardStartFiles'):
        lflags += ' -nostartfiles'
    if get_key_as_bool(config_group, 'armgcc.linker.general.DoNotUseDefaultLibraries'):
        lflags += ' -nodefaultlibs'
    if get_key_as_bool(config_group, 'armgcc.linker.general.NoStartupOrDefaultLibs'):
        lflags += ' -nostdlib'
    if get_key_as_bool(config_group, 'armgcc.linker.general.OmitAllSymbolInformation'):
        lflags += ' -s'
    if get_key_as_bool(config_group, 'armgcc.linker.general.NoSharedLibraries'):
        lflags += ' -static'
    if get_key_as_bool(config_group, 'armgcc.linker.general.GenerateMAPFile', True):
        lflags += ' -Wl,-Map="' + output + '.map"'
    if get_key_as_bool(config_group, 'armgcc.linker.general.UseNewlibNano'):
        lflags += ' --specs=nano.specs'
    # AdditionalSpecs: None './/armgcc.linker.general.AdditionalSpecs'
    # Libraries
    lflags += ' -Wl,--start-group -lm -lBalancing -lCenter -lHelpersInCppK3 -lRosMath_Static -Wl,--end-group'
    lflags += get_key_as_strarray(config_group, 'armgcc.linker.libraries.LibrarySearchPaths', ' -L"{}"')
    lflags += ' -L"C:/Work/Korsar3Mini-trunk/Balancing/Debug"'
    lflags += ' -L"C:/Work/Korsar3Mini-trunk/Center/Debug"'
    lflags += ' -L"C:/Work/Korsar3Mini-trunk/HelpersInCppK3/Debug"'
    lflags += ' -L"C:/Work/Korsar3Mini-trunk/_ext/RosMath/project/RosMath_Static_AS62/Debug"'
    # Optimization
    if get_key_as_bool(config_group, 'armgcc.linker.optimization.GarbageCollectUnusedSections'):
        ccflags += ' -Wl,--gc-sections'
    if get_key_as_bool(config_group, 'armgcc.linker.optimization.EnableUnsafeMatchOptimizations'):
        ccflags += ' -funsafe-math-optimizations'
    if get_key_as_bool(config_group, 'armgcc.linker.optimization.EnableFastMath'):
        ccflags += ' -ffast-math'
    if get_key_as_bool(config_group, 'armgcc.linker.optimization.GeneratePositionIndependentCode'):
        ccflags += ' -fpic'
    # Memory Settings
    # Miscellaneous
    lflags += get_key_as_str(config_group, 'armgcc.linker.miscellaneous.LinkerFlags', ' {}')
    lflags += get_key_as_strarray(config_group, 'armgcc.linker.miscellaneous.OtherOptions', ' -Xlinker {}')
    lflags += get_key_as_strarray(config_group, 'armgcc.linker.miscellaneous.OtherObjects', ' {}')

nw.variable('ccflags', ccflags)
nw.newline()
nw.variable('lflags', lflags)
nw.newline()

nw.rule('cc',
        command=cc + ' -x c -c $ccflags -MD -MP -MF $out.d -MT $out -o $out $in',
        description='cc $out',
        depfile='$out.d',
        deps='gcc')
nw.newline()

nw.rule('link',
        command=link + ' -o$out @$out.rsp $lflags',
        description='LINK $out',
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
            else:
                print('Skipping file {}'.format(file))
    nw.newline()

nw.build(output + '.elf', 'link', obj_files)
nw.newline()

nw.build('all', 'phony', output + '.elf')
nw.newline()

nw.default('all')

nw.close()
