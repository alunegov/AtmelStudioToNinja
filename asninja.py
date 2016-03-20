import os
from xml.etree import ElementTree
import ninja_syntax


def get_config_group(prj_root, config_name):
    for group in prj_root.findall('PropertyGroup'):
        if group.attrib.get('Condition', '__none') == " '$(Configuration)' == '{}' ".format(config_name):
            return group


def get_src_files_group(prj_root):
    return prj_root.getroot()[4]


asProject = ElementTree.parse(os.path.join('tests', 'Korsar3.cproj'))
nw = ninja_syntax.Writer(open('build.ninja', 'w'), 120)

nw.variable('ninja_required_version', '1.3')
nw.newline()

nw.variable('root', '.')
nw.variable('builddir', 'build')
nw.newline()

cflags = '-x c -mthumb -O0 -mcpu=cortex-m4 -c'
lflags = ''

config_group = get_config_group(asProject, 'Debug')
if config_group is not None:
    #
    for define in config_group.findall('.//armgcc.compiler.symbols.DefSymbols/ListValues/Value'):
        cflags += ' -D{}'.format(define.text)
    #
    for include in config_group.findall('.//armgcc.compiler.directories.IncludePaths/ListValues/Value'):
        cflags += ' -I"{}"'.format(include.text)
    #
    item = config_group.find('.//armgcc.compiler.optimization.OtherFlags')
    if item is not None:
        cflags += ' {}'.format(item.text)

    #
    item = config_group.find('.//armgcc.compiler.optimization.PrepareFunctionsForGarbageCollection')
    if item is not None:
        if item.text == 'True':
            cflags += ' -ffunction-sections'
    #
    item = config_group.find('.//armgcc.compiler.optimization.DebugLevel')
    if item is not None:
        if item.text.find('-g3') != -1:
            cflags += ' -g3'
    #
    item = config_group.find('.//armgcc.compiler.warnings.AllWarnings')
    if item is not None:
        if item.text == 'True':
            cflags += ' -Wall'
    #
    item = config_group.find('.//armgcc.compiler.warnings.ExtraWarnings')
    if item is not None:
        if item.text == 'True':
            cflags += ' -Wextra'
    #
    item = config_group.find('.//armgcc.compiler.miscellaneous.OtherFlags')
    if item is not None:
        cflags += ' {}'.format(item.text)

nw.variable('cflags', cflags)
nw.variable('lflags', lflags)
nw.newline()

nw.rule('cc',
        command='arm-none-eabi-gcc.cmd -MD -MP -MT $out -MF $out.d $cflags -o $out $in',
        description='cc $out',
        depfile='$out.d',
        deps='gcc')
nw.newline()

nw.rule('link',
        command='arm-none-eabi-gcc.cmd -o$out @$out.rsp $lflags',
        description='LINK $out',
        rspfile='$out.rsp',
        rspfile_content='$in')
nw.newline()

src_files_group = get_src_files_group(asProject)
obj_files = []
if src_files_group is not None:
    for item in src_files_group.findall('Compile'):
        file = item.attrib['Include']
        filename, file_ext = os.path.splitext(file)
        obj_filename = filename
        while obj_filename.find('..') == 0:
            obj_filename = obj_filename[3:]
        if file_ext == '.c':
            obj_files += nw.build(os.path.join('$builddir', obj_filename + '.o'), 'cc', os.path.join('$root', file))
        else:
            if file_ext == '.cpp':
                obj_files += nw.build(os.path.join('$builddir', obj_filename + '.o'), 'cxx', os.path.join('$root', file))
            else:
                print('Skipped file {}'.format(file))
    nw.newline()

nw.build(os.path.join('$builddir', 'Korsar3.elf'), 'link', obj_files)
nw.newline()

nw.build('all', 'phony', os.path.join('$builddir', 'Korsar3.elf'))
nw.newline()

nw.default(os.path.join('$builddir', 'Korsar3.elf'))

nw.close()
