import argparse
import os

import ninja_syntax

from asninja.as_project import AtmelStudioProject
from asninja.as_toolchain import AtmelStudioGccToolchain
from asninja.gcc_toolchain import GccToolchain
from asninja.helpers import strip_updir

__all__ = ["detect_linker_script", "convert"]


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
