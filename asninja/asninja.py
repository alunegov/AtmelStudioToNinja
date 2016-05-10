import argparse

from asninja.converter import Converter


def main():
    parser = argparse.ArgumentParser(description='asninja')
    parser.add_argument('--prj', type=str, help='Atmel Studio project file')
    parser.add_argument('--config', type=str, help='Configuration (Debug, Release, ...)', default='Debug')
    parser.add_argument('--outpath', type=str, help='Output path (if absent when same as config name)', default=None)
    parser.add_argument('--output', type=str, help='Output filename')
    parser.add_argument('--flags', type=str, help='Additional compiler and linker flags (like -mthumb)', default=None)
    parser.add_argument('--add_defs', type=str, help='Additional compiler defines (like __SAM4S8C__)', default=None)
    parser.add_argument('--del_defs', type=str, help='Defines to remove from compiler defines', default=None)
    parser.add_argument('--gcc_toolchain', type=str, help='Custom GCC toolchain path', default=None)

    # get all data from command line
    args = parser.parse_args()
    # print(args)

    _flags = args.flags.split(' ') if args.flags else []
    _add_defs = args.add_defs.split(' ') if args.add_defs else []
    _del_defs = args.del_defs.split(' ') if args.del_defs else []
    # print(_flags, _add_defs, _del_defs)

    Converter.convert(as_prj=args.prj, config=args.config, outpath=args.outpath, output=args.output, flags=_flags,
                      add_defs=_add_defs, del_defs=_del_defs, custom_toolchain=args.gcc_toolchain)


if __name__ == '__main__':
    main()
