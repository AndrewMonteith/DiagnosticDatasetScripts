#!/bin/python3
import sys

from diag_utils import DiagnosticsDiff, Diagnostic
import githelpers

import random
import subprocess
from pathlib import Path
from functools import lru_cache

PROJECT_URLS = {
    "guice": "http://github.com/google/guice"
}


def stratify_diff(diff: DiagnosticsDiff, strat: int):
    matches = [(old, new)
               for (old, new) in diff.matches.items()
               if old != new]

    random.shuffle(matches)

    sorted_tuples = sorted(matches[::strat], key=lambda p: p[0]._file)
    diff.matches = {old: new for (old, new) in sorted_tuples}


def write_helpful_diff(project: Path, diff: DiagnosticsDiff, strat: int):
    output = Path("stratified_comparisons") / project.name / \
        (diff.file.name + f".strat_{strat}")

    diff.write(output)


class FileLoader:
    def __init__(self, project: Path, output: Path):
        self._project = project
        self._output = output
        self._files = []
        self._loaded = set()

    @staticmethod
    def get_file_name(file: Path, commit: str):
        return commit + "-" + (str(file).replace("/", "-"))

    @staticmethod
    def format(files):
        subprocess.run(["java", "-jar", "google-format.jar", "-i",
                        "--skip-sorting-imports", "--skip-removing-unused-imports",
                        *files])

    def _load_formatted(self, file: Path, commit: str):
        src, loaded = githelpers.load_file(self._project, commit, file)

        output_file = self._output / FileLoader.get_file_name(file, commit)
        self._files.append((output_file, loaded))

        with open(output_file, "w") as f:
            f.write(src)

        return loaded

    def load(self, file: str, commit: str):
        file = Path(file)

        filename = FileLoader.get_file_name(file, commit)
        if filename not in self._loaded:
            self._loaded.add(FileLoader.get_file_name(file, commit))
            self._load_formatted(file, commit)

        return open(self._output / FileLoader.get_file_name(file, commit), "r").read()


    @property
    def formattable_files(self):
        return [
            file
            for (file, loaded) in self._files
            if loaded
        ]

    def format_files(self):
        FileLoader.format(self.formattable_files)
        


def write_touched_files(project: Path, diff: DiagnosticsDiff, output: Path):
    # Step 1 load them onto disk
    f = FileLoader(project, output)
    for (old, new) in diff.matches.items():
        f.load(old._file, diff.pre_commit)
        f.load(new._file, diff.post_commit)

    for unmatched_old in diff.unmatched_old:
        f.load(unmatched_old._file, diff.pre_commit)
        f.load(unmatched_old._file, diff.post_commit)

    for unmatched_new in diff.unmatched_new:
        f.load(unmatched_new._file, diff.pre_commit)
        f.load(unmatched_new._file, diff.post_commit)

    return f.formattable_files


def gen_check_file(project: Path, diffs_folder: Path, strat: int):
    diffs = DiagnosticsDiff.load_all(diffs_folder)
    for diff in diffs:
        stratify_diff(diff, strat)

    print("Going to check " + str(sum((len(diff.matches) for diff in diffs))))

    files_to_format = []

    for diff in diffs:
        write_helpful_diff(project, diff, strat)
        files_to_format.extend(write_touched_files(project, diff, Path(
            "stratified_comparisons") / project.name / "files"))

    FileLoader.format(files_to_format)


if __name__ == "__main__":
    gen_check_file(Path(sys.argv[1]), Path(sys.argv[2]), int(sys.argv[3]))
