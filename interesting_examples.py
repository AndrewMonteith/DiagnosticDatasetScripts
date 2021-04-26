#!/bin/python3
import sys
import githelpers
import itertools

from prhelper import ask_question
from diag_utils import DiagnosticsDiff
from pathlib import Path
from matchhelper2 import FileLoader
from meyersdiff import *
from functools import lru_cache


@lru_cache
def load_diff(old_src, new_src):
    return myers_diff(old_src.split("\n"), new_src.split("\n"))


def on_deleted_line(src_diff, line):
    old_line = 0
    for line_diff in src_diff:
        if isinstance(line_diff, Keep) or isinstance(line_diff, Remove):
            old_line += 1

        if old_line == line:
            return isinstance(line_diff, Remove)


def get_interesting_diags(project, diff, changed_diags):
    # 1. Preload all files
    print("Preloading files")
    f = FileLoader(project, Path("dump") / project.name)

    files = set((d._file for (d, _) in changed_diags))
    print(len(files)*2)

    for (old, new) in changed_diags:
        f.load(old._file, diff.pre_commit)
        f.load(new._file, diff.post_commit)
    print("Formatting files")
    f.format_files()

    print("Looking for interesting")

    # 2. Look for ones on a deleted line
    interesting = []
    for (old, new) in changed_diags:
        if "BooleanParameter" in old._type:
            continue

        old_src = f.load(old._file, diff.pre_commit)
        new_src = f.load(old._file, diff.post_commit)

        src_diff = load_diff(old_src, new_src)

        if on_deleted_line(src_diff, old._line):
            interesting.append((old, new))

    return f, interesting


if __name__ == "__main__":
    project = Path(sys.argv[1])
    diff_path = Path(sys.argv[2])

    print("Loading diffs")
    diffs = DiagnosticsDiff.load_all(diff_path)

    intereting_candidates = []

    for diff in diffs:
        print("Checking", diff)
        changed_java_files = githelpers.get_changed_java_files(
            project, diff.pre_commit, diff.post_commit)

        if len(changed_java_files) == 0:
            continue

        print("Found changed files")
        tracked_in_changed_files = {(old, new)
                                    for (old, new) in diff.matches.items()
                                    if old._file in changed_java_files}

        if len(tracked_in_changed_files) == 0:
            continue
        
        file_loader, interesting_diags = get_interesting_diags(
            project, diff, tracked_in_changed_files)

        if len(interesting_diags) == 0:
            continue

        candidate = (diff, file_loader, interesting_diags)        
        intereting_candidates.append(candidate)

        print(len(intereting_candidates[-1][2]))

    print(len(intereting_candidates[-1][2]))

    for (diff, file_loader, diags) in intereting_candidates:
        for (old, new) in diags:
            print(old)
            print(new)
            ask_question(file_loader.load(old._file, diff.pre_commit),
                         file_loader.load(new._file, diff.post_commit),
                         old_diag=old,
                         new_diag=new)
