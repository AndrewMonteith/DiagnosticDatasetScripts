#!/bin/python3
import sys

from pathlib import Path
from prhelper import ask_question
from matchhelper2 import FileLoader
from diag_utils import Diagnostic


def load_diagnostic(lines):
    to = lines.index("  to")
    comments = lines.index("-- Comment")

    old_diag = Diagnostic(lines[2:to])
    new_diag = Diagnostic(lines[to+1:comments])

    return old_diag, new_diag


if __name__ == "__main__":
    for file in sys.argv[1:]:
        print(file)
        lines = open(file, "r").read().split("\n")

        project = Path(lines[0])
        pre_commit, post_commit = lines[1].split(" ")

        old_diag, new_diag = load_diagnostic(lines)

        f = FileLoader(project, Path("dump") / project.name)
        f.load(old_diag._file, pre_commit)
        f.load(new_diag._file, post_commit)
        f.format_files()

        old_src = f.load(old_diag._file, pre_commit)
        new_src = f.load(new_diag._file, post_commit)

        ask_question(old_src, new_src, old_diag=old_diag, new_diag=new_diag)
