"""Module text library"""

def text_lib(name = None):
    name = name or _eponymous_name()

    filegroup(
        name = name,
        srcs = glob([
            "**/*.txt",
            "*.txt",
        ]),
    )
