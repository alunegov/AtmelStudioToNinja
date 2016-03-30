__all__ = ["strip_empty_symbols", "strip_updir"]


def strip_empty_symbols(symbols):
    assert isinstance(symbols, list)
    new_symbols = []
    for symbol in symbols:
        if len(symbol) != 0:
            new_symbols.append(symbol)
    return new_symbols


def strip_updir(file_name):
    """Strips all '../' from start of file_name"""
    fn = file_name
    while fn.find('..', 0) == 0:
        fn = fn[3:]
    return fn
