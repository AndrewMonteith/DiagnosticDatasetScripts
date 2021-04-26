#!/bin/python3

import sys
import githelpers
import os
import multiprocess as mp
import shutil
import subprocess

from pathlib import Path
from diag_utils import DiagnosticsFile

if __name__ == "__main__":
    project = Path(sys.argv[1])
    diag_files = DiagnosticsFile.load_all(Path(sys.argv[2]))
    new_repo = Path(sys.argv[1] + "_formatted")

    githelpers.init(new_repo)
    for diag_file in diag_files:
        files = set((diag._file for diag in diag_file.diagnostics))

        # Delete all non-git files
        for f in new_repo.glob("*"):
            if f.name.endswith(".git"):
                continue
            if f.is_dir():
                shutil.rmtree(f)
            else:
                os.remove(f)

        # Load all new src
        pool = mp.Pool(8)

        def load_src(file):
            (src, loaded) = githelpers.load_file(
                project, diag_file.commit, file)
            if not loaded:
                raise Exception(f"Could not load {file} in {diag_file.commit}")
            return (file, src)

        files_to_format = []
        for (file, src) in pool.map(load_src, files):
            p = new_repo / file
            files_to_format.append(str(p))
            p.parents[0].mkdir(parents=True, exist_ok=True)
            open(p, "w").write(src)

        subprocess.run(["java", "-jar", "google-format.jar", "-i",
                        "--skip-sorting-imports", "--skip-removing-unused-imports", *files_to_format])

        # Format files
        new_commit = githelpers.commit_all(new_repo)
        print(diag_file.commit, "->", new_commit)
