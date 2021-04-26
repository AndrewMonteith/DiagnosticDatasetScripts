#!/bin/python3

import sys

from diag_utils import DiagnosticsFile, DiagnosticsDiff, Diagnostic, find_when_leaves
from pathlib import Path


def load_files(folder):
    def extract_grains(filename):
        return tuple([int(s) for s in filename.suffix[1:].split("-")])

    loaded_files = [
        (extract_grains(file), DiagnosticsFile.load(file))
        for file in folder.glob("*")
        if file.is_file()
    ]

    return sorted(loaded_files, key=lambda grain_and_file: grain_and_file[1].seq)


def consecutive_pairs(items):
    for i in range(len(items)-1):
        yield (items[i], items[i+1])


def find_missed_commits(grains_and_files):
    max_grain = max(max(grains) for (grains, _) in grains_and_files)

    missing_subsequence = []
    for (grains, file) in grains_and_files:
        if max_grain in grains:
            missing_subsequence.append(file)
            if len(missing_subsequence) > 2:
                yield missing_subsequence
            missing_subsequence = [file]
        else:
            missing_subsequence.append(file)


def get_diff(diffs, pre_commit, post_commit):
    return next((diff for diff in diffs
                 if diff.pre_commit == pre_commit and diff.post_commit == post_commit))


def get_diffs(diffs, pre_commit, post_commit):
    start_diff = next(i for (i, diff) in enumerate(diffs)
                      if diff.pre_commit == pre_commit)

    end_diff = next(i for (i, diff) in enumerate(diffs)
                    if diff.post_commit == post_commit)

    return diffs[start_diff:end_diff+1]

if __name__ == "__main__":
    grains_and_files = load_files(Path(sys.argv[1]))
    diffs = DiagnosticsDiff.load_all(Path(sys.argv[2]))

    missed_diags = []

    for missed_commits in find_missed_commits(grains_and_files):
        between_diffs = get_diffs(
            diffs, missed_commits[0].commit, missed_commits[-1].commit)

        # Look for missed diagnostics
        for (i, between_diff) in enumerate(between_diffs[:-1]):
            for added_diag in between_diff.unmatched_new:
                leaves = find_when_leaves(between_diffs, added_diag, start=i)

                # If diagnostic doesn't leave after next scanned commit
                if leaves != len(between_diffs):
                    missed_diags.append({
                        "diag": added_diag,
                        "start_commit": f"{missed_commits[0].seq}  {missed_commits[0].commit}",
                        "end_commit": f"{missed_commits[-1].seq}  {missed_commits[-1].commit}",
                        "enters": f"{between_diff.post} {between_diff.post_commit}",
                        "leaves": f"{between_diffs[leaves].post} {between_diffs[leaves].post_commit}"
                    })

    print()
    print("---------------")
    print("--- Results ---")
    print("---------------")
    print()

    print("=== Missed Diagnostis===")
    print("Total", len(missed_diags))
    for missed in missed_diags:
        print(f"  Following diagnostic lost by {missed['start_commit']} -> {missed['end_commit']}")
        print(missed["diag"])
        print(
            f"  It enters at {missed['enters']} and leaves {missed['leaves']}")
    print()
