#!/bin/python3
import sys
import githelpers
import shutil
import re
import os

from diag_utils import DiagnosticsFile, Diagnostic
from pathlib import Path

from typing import List

ENDS_WITH_NUMBERS = re.compile(r".*_(\d+)$")


def get_commit(file: Path):
    _, commit = file.stem.split(" ")
    return commit


def get_granularity(file: Path):
    folder = file.parent.name
    match = ENDS_WITH_NUMBERS.match(folder)

    if match:
        return match.group(1)
    else:
        return "0"


def stitch_together(project, output, folders):
    files = [file for folder in folders
             for file in folder.glob("*")
             if file.is_file() and not file.name.endswith(".skip")]

    all_commits = githelpers.get_all_commits(project)

    def get_commit_index(file: Path):
        return all_commits.index(get_commit(file))

    sorted_files = sorted(files, key=get_commit_index)

    commit_grains = {get_commit(file): [] for file in sorted_files}
    for file in sorted_files:
        commit_grains[get_commit(file)].append(get_granularity(file))

    processed = set([])
    seq = 0
    for file in sorted_files:
        commit = get_commit(file)
        if commit in processed:
            continue

        shutil.copy(file, output /
                    f"{seq} {commit}.{'-'.join(commit_grains[commit])}")

        seq += 1
        processed.add(commit)


def weird(folder1: Path, folder2: Path):
    diagnostics1 = DiagnosticsFile.load_all(folder1)
    diagnostics2 = DiagnosticsFile.load_all(folder2)

    commits = list(set([*[diag.commit for diag in diagnostics1],
                        *[diag.commit for diag in diagnostics2]]))

    d = {commit: [] for commit in commits}

    for diag in [*diagnostics1, *diagnostics2]:
        d[diag.commit].append(diag)

    for (commit, diags) in d.items():
        if len(diags) <= 1:
            continue
        if len(diags[0].diagnostics) != len(diags[1].diagnostics):
            print(commit, len(diags[0].diagnostics), len(diags[1].diagnostics))


def consensus(folders):
    files = [file for folder in folders
             for file in DiagnosticsFile.load_all(folder)]

    # Group by commit
    commits = {}
    for file in files:
        if file.commit not in commits.keys():
            commits[file.commit] = []
        commits[file.commit].append(file)

    # For any tie copy largest file
    for (_, files) in commits.items():
        if len(files) <= 1:
            continue

        # Do all files agree?
        if len(set((len(file.diagnostics) for file in files))) == 1:
            continue

        most_diags = sorted(files, key=lambda file: len(file.diagnostics))[-1]
        for diag_file in files:
            if most_diags.file == diag_file.file:
                continue

            if not most_diags.file.endswith(".skip") and diag_file.file.endswith(".skip"):
                shutil.copy(most_diags.file, diag_file.file.with_suffix(""))
            else:
                shutil.copy(most_diags.file, diag_file.file)


def print_file_diff(file1: Path, file2: Path):
    diag_file_1 = DiagnosticsFile.load(file1)
    diag_file_2 = DiagnosticsFile.load(file2)

    # Compare difference at file level
    files_1 = [diag._file for diag in diag_file_1.diagnostics]
    files_2 = [diag._file for diag in diag_file_2.diagnostics]

    freqs_1 = {file: files_1.count(file) for file in files_1}
    freqs_2 = {file: files_2.count(file) for file in files_2}

    shared_files = freqs_1.keys() & freqs_2.keys()
    for file in shared_files:
        freq_1 = freqs_1[file]
        freq_2 = freqs_2[file]

        if freq_1 != freq_2:
            print(file, freq_1, "->", freq_2)

    for (file, freq) in freqs_1.items():
        if file not in shared_files:
            print('File "deleted"', file, freq)

    for (file, freq) in freqs_2.items():
        if file not in shared_files:
            print('File "added" ', file, freq)


def file_mutator(mutate_diag_file):
    def map_files(files: List[Path], *args):
        diag_files = [DiagnosticsFile.load(file)
                      for file in files
                      if not ".skip" in file.suffix]

        for diag_file in diag_files:
            mutate_diag_file(diag_file, *args)
            suffix = ".skip.new" if diag_file.file.suffix == ".skip" else ".new"
            diag_file.save(diag_file.file.with_suffix(suffix))

    return map_files


@file_mutator
def remove_diag_type(diag_file: DiagnosticsFile, diag_type: str):
    diag_file.diagnostics = [
        diag
        for diag in diag_file.diagnostics
        if diag_type not in diag._type
    ]


@file_mutator
def remove_file(diag_file: DiagnosticsFile, filename: str):
    diag_file.diagnostics = [
        diag
        for diag in diag_file.diagnostics
        if filename not in diag._file
    ]


@file_mutator
def filter_file(diag_file: DiagnosticsFile, filename: str):
    diag_file.diagnostics = [
        diag
        for diag in diag_file.diagnostics
        if filename in diag._file
    ]


cache = {}

last_commit = ""


def does_file_exist(project: Path, commit: str, file: str):
    global last_commit, cache

    if last_commit != commit:
        githelpers.checkout(project, commit)

    last_commit = commit

    fid = commit + file
    if fid not in cache:
        cache[fid] = (project / file).is_file()

    return cache[fid]


@file_mutator
def remove_missing_files(diag_file: DiagnosticsFile, project: Path):
    print(f"{diag_file.seq} {diag_file.commit}")

    files = githelpers.get_all_files_in_commit(project, diag_file.commit)

    diag_file.diagnostics = [
        diag
        for diag in diag_file.diagnostics
        if diag._file in files
    ]


def get_relative_file(filepath):
    if not "java-corpus" in str(filepath):
        return filepath

    split = filepath.split("/")
    corpus_i = split.index("java-corpus")

    return '/'.join(split[corpus_i+2:])  # skip ROOT/java-corpus/<project-name>


@file_mutator
def relative_files(diag_file):
    for diag in diag_file.diagnostics:
        diag._file = get_relative_file(diag._file)


@file_mutator
def stitch_files(diag_file, other_files: List[Path]):
    other_file = DiagnosticsFile.load(next((file for file in other_files
                                            if diag_file.commit in file.name)))

    diag_file.diagnostics = [*diag_file.diagnostics, *other_file.diagnostics]


@file_mutator
def sort_diag_descriptions(diag_file, diag_type: str):
    def sort_diag_desc(diag: Diagnostic):
        diag._raw = [
            diag._raw[0],
            diag._raw[1],
            *sorted(diag._raw[2:])
        ]

        return diag

    diag_file.diagnostics = [
        sort_diag_desc(diag) if diag_type in diag._type else diag
        for diag in diag_file.diagnostics
    ]


@file_mutator
def filter_diag_type(diag_file, diag_type: str):
    diag_file.diagnostics = [
        diag 
        for diag in diag_file.diagnostics
        if diag_type in diag._type
    ]


def list_files(folder: Path):
    return [folder / file
            for file in os.listdir(folder)
            if os.path.isfile(os.path.join(folder, file))]


if __name__ == "__main__":
    cmd = sys.argv[1]

    if cmd == "stitch":
        project = Path(sys.argv[2])
        output = Path(sys.argv[3])
        folders = [Path(folder) for folder in sys.argv[4:]]

        if any(not folder.exists() for folder in folders):
            raise Exception("one folder doesn't exist")

        stitch_together(project, output, folders)
    elif cmd == "consensus":
        consensus([Path(folder) for folder in sys.argv[2:]])
    elif cmd == "file-diff":
        print_file_diff(Path(sys.argv[2]), Path(sys.argv[3]))
    elif cmd == "remove-diag-type":
        remove_diag_type([Path(file) for file in sys.argv[3:]], sys.argv[2])
    elif cmd == "remove-file":
        remove_file([Path(file) for file in sys.argv[3:]], sys.argv[2])
    elif cmd == "filter-diag-type":
        filter_diag_type([Path(file) for file in sys.argv[3:]], sys.argv[2])
    elif cmd == "filter-file":
        filter_file([Path(file) for file in sys.argv[3:]], sys.argv[2])
    elif cmd == "remove-missing-files":
        remove_missing_files([Path(file)
                              for file in sys.argv[3:]], Path(sys.argv[2]))
    elif cmd == "relative-files":
        relative_files([Path(file) for file in sys.argv[2:]])
    elif cmd == "merge":
        stitch_files([Path(file) for file in sys.argv[3:]],
                     list_files(Path(sys.argv[2])))
    elif cmd == "sort-diag-desc":
        sort_diag_descriptions([Path(file)
                                for file in sys.argv[3:]], sys.argv[2])
    else:
        raise Exception(cmd + " does not exist")
