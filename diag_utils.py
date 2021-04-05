#!/bin/python3
import sys
import os
import os.path

from pathlib import Path
from typing import List

from githelpers import get_all_commits


def get_relative_file(filepath):
    split = filepath.split("/")
    corpus_i = split.index("java-corpus")

    return '/'.join(split[corpus_i+2:])  # skip ROOT/java-corpus/<project-name>


def get_diag_type(diag_msg):
    return diag_msg.split(" ")[0]  # "[Diag-Type] other information"


class Diagnostic:
    def __init__(self, lines):
        loc_info = lines[1].split(" ")

        self._raw = lines[:]
        self._file = get_relative_file(loc_info[0])
        self._line = int(loc_info[1])
        self._col = int(loc_info[2])
        self._start = int(loc_info[3])
        self._pos = int(loc_info[4])
        self._end = int(loc_info[5])
        self._type = get_diag_type(lines[2])
        self._message = lines[2]

    def __eq__(self, other):
        return self._file == other._file and \
            self._line == other._line and \
            self._col == other._col and \
            self._message == other._message and \
            (self._end - self._start) == (other._end - other._start)

    def __repr__(self):
        return f"({self._file} {self._type} {self._line} {self._col} {self._start} {self._end})"

    def __str__(self):
        return '\n'.join(self._raw)

    def __hash__(self):
        return hash((self._file, self._line, self._col, self._type, self._end - self._start))

    def __lt__(self, other):
        if self._file != other._file:
            return self._file < other._file

        return self._line < other._line


def consecutive_pairs(items):
    # [1,2,3,4] -> [(1, 2), (2, 3), (3, 4)]
    for i in range(len(items)-1):
        yield (items[i], items[i+1])


def by_delim(items, delim):
    matches = [i for (i, item) in enumerate(items)
               if item == delim]

    if len(matches) == 0:
        yield items

    for (i, j) in consecutive_pairs(matches):
        yield items[i:j]

    if len(matches) > 0:
        yield items[matches[-1]:]


def parse_diagnostics(lines):
    if len(lines) == 0:
        return []

    for diag_lines in by_delim(lines, "----DIAGNOSTIC"):
        if len(diag_lines) <= 1:
            continue

        yield Diagnostic(diag_lines)


def read_stripped_lines(file):
    return [line.strip() for line in open(file).readlines()]


class DiagnosticsFile:
    def __init__(self, file: Path, seq:int, commit: str, diagnostics: List[Diagnostic]):
        self.file = file
        self.seq = seq
        self.commit = commit
        self.diagnostics = diagnostics

    @classmethod
    def load(cls, file: Path):
        seq, commit = file.stem.split(" ")
        diagnostics = list(parse_diagnostics(read_stripped_lines(file)))

        return cls(file, int(seq), commit, diagnostics)

    @classmethod
    def load_all(cls, folder: Path):
        return sorted([
            cls.load(file)
            for file in folder.glob("*")
            if file.is_file() and not file.name.endswith(".skip")
        ])

    def save(self, out: Path):
        with open(out, "w") as f:
            f.write(f"{self.commit} {len(self.diagnostics)}\n")
            for diag in self.diagnostics:
                f.write(str(diag) + "\n")



    def __eq__(self, other):
        return self.commit == other.commit

    def __lt__(self, other):
        return self.seq < other.seq

    def __hash__(self):
        return hash((self.commit,))

    def __repr__(self):
        return self.commit


class DiagnosticsDiff:
    "Describes the differences in diagnostics between two commits"

    def __init__(self, file: Path):
        # "<pre> [commit] -> <post> [commit]"
        file_split = file.stem.split(" ")
        if len(file_split) == 5:
            self.pre = int(file_split[0])
            self.pre_commit = file_split[1]
            self.post = int(file_split[3])
            self.post_commit = file_split[4]
        else:
            self.pre = int(file_split[0])
            self.post = int(file_split[2])

        self.matches = {}
        self.unmatched_old = []
        self.unmatched_new = []

        self._read_file(file)

    def _read_matches(self, lines):
        for match in by_delim(lines, "--------Matches"):
            delim = match.index("to")
            old_diag = Diagnostic(match[1:delim])
            new_diag = Diagnostic(match[delim+1:])

            self.matches[old_diag] = new_diag

    def _read_file(self, file):
        lines = [line.strip() for line in open(file).readlines()]

        self._read_matches(lines)

        unmatched_old = lines.index("--------Unmatched old")
        unmatched_new = lines.index("--------Unmatched new")

        self.unmatched_old.extend([diag for diag in
                                   parse_diagnostics(lines[unmatched_old+1:unmatched_new])])
        self.unmatched_new.extend([diag for diag in
                                   parse_diagnostics(lines[unmatched_new+1:])])

    def write(self, path: Path):
        with open(path, "w") as file:
            def write_line(s): return print(s, file=file)

            write_line(f"Total {len(self.matches)}")
            for (old, new) in self.matches.items():
                write_line("--------Matches")
                write_line(old)
                write_line("  to")
                write_line(new)

            write_line("--------Unmatched old")
            write_line(f"Total {len(self.unmatched_old)}")
            for diag in self.unmatched_old:
                write_line(diag)

            write_line("--------Unmatched new")
            write_line(f"Total {len(self.unmatched_new)}")
            for diag in self.unmatched_new:
                write_line(diag)

    def __lt__(self, other):
        return self.pre < other.pre

    def __eq__(self, other):
        return self.pre == other.pre and self.post == other.post

    def __repr__(self):
        pre = f"{self.pre} {'' if self.pre_commit is None else self.pre_commit}"
        post = f"{self.post} {'' if self.post_commit is None else self.post_commit}"
        return f"{pre} -> {post}"

    @classmethod
    def load_all(cls, folder: Path):
        return sorted((cls(file)
                       for file in folder.glob("* -> *")))


def get_added_diagnostics(diffs: List[DiagnosticsDiff], commit: str):
    diff = next(diff for diff in diffs
                if diff.post_commit == commit)

    return diff.unmatched_new


def get_removed_diagnostics(diffs: List[DiagnosticsDiff], commit: str):
    diff = next(diff for diff in diffs
                if diff.post_commit == commit)

    return diff.unmatched_old


def find_when_leaves(diffs: List[DiagnosticsDiff],
                     diagnostic: Diagnostic,
                     start: int = 0,
                     end: int = None) -> int:
    if end is None:
        end = len(diffs)

    if diagnostic in diffs[start].unmatched_new:
        start += 1

    if start == len(diffs)-1:
        # Added at end
        return start

    for cur in range(start, min(end, len(diffs))):
        file = diffs[cur]

        # Does it leave in this commit?
        if diagnostic in file.unmatched_old:
            return cur
        else:
            diagnostic = file.matches[diagnostic]

    return end
