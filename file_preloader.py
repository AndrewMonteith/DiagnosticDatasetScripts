#!/bin/python3

import sys

from diag_utils import DiagnosticsFile
from matchhelper2 import FileLoader

from pathlib import Path

if __name__ == "__main__":
    project = Path(sys.argv[1])
    diag_files = DiagnosticsFile.load_all(Path("diagnostics") / project)

    fl = FileLoader(project, Path("dump") / project)
    for diag_file in diag_files:
        print(diag_file)
        for file in set(diag._file for diag in diag_file.diagnostics):
            fl.load(file, diag_file.commit)
    
    fl.format_files()