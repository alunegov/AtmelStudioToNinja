import os
import sys

import ninja_syntax

import asninja.helpers
from .parser import AtmelStudioProject
from .toolchains.atmel_studio import AtmelStudioGccToolchain
from .toolchains.gcc import GccToolchain


class Converter(object):
    @classmethod
    def detect_linker_script(cls, lflags):
        """Search '-T' params in lflags, in finded value strips first '../'"""
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

    @classmethod
    def convert(cls, as_prj, config, outpath, output, flags, add_defs, del_defs, custom_toolchain=None):
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

        if not outpath:
            outpath = config
        __, outdir = os.path.split(outpath)

        if asp.select_config(config):
            # ARM/GNU C Compiler
            ccflags += asp.compiler_flags(True, add_defs, del_defs, [])
            # ARM/GNU C++ Compiler
            if asp.is_cpp:
                cxxflags += asp.compiler_flags(False, add_defs, del_defs, [])
            if asp.is_lib:
                # ARM/GNU Archiver
                arflags += asp.archiver_flags()
            else:
                # ARM/GNU Linker
                lflags += asp.linker_flags(outdir)
        else:
            raise Exception('Undefined config in project {0}'.format(config))

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
                    command=ar + ' $arflags -o $out $in',
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
            filename = asninja.helpers.strip_updir(filename)
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
                linker_script = cls.detect_linker_script(lflags)
                if linker_script:
                    sys.stdout.write('linker_script = ' + linker_script)
                    implicit_dep.append('$src/' + linker_script)
                #
                for lib in asp.ref_libs:
                    implicit_dep.append('$builddir/../' + lib.full_name(outdir))

                def_target = nw.build('$builddir/' + asp.output(), 'link', obj_files,
                                      implicit=implicit_dep)
                nw.newline()

            nw.default(def_target)

        nw.close()
