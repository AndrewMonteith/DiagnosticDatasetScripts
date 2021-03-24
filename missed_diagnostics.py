#!/bin/python3
import argparse
import sys
import subprocess
import tempfile

from pathlib import Path
from typing import List

import githelpers

from diag_utils import Diagnostic, DiagnosticsDiff, DiagnosticsFile, find_when_leaves


def merge_diagnostics(project: Path,
                      lr_diags: List[DiagnosticsFile],
                      hr_diags: List[DiagnosticsFile]) -> List[DiagnosticsFile]:
    "Merge the low and high resolution respecting ordering of all_commits"
    all_commits = githelpers.get_all_commits(project)

    def find_global_seq(diag):
        return all_commits.index(diag.commit)

    merged_unsorted = list(set([*lr_diags, *hr_diags]))

    # need to make unique since low and high res can scan the same commits
    return sorted(merged_unsorted, key=find_global_seq)


def consecutive_pairs(items):
    # [1,2,3,4] -> [(1, 2), (2, 3), (3, 4)]
    for i in range(len(items)-1):
        yield (items[i], items[i+1])


def find_commits_between(all_commits, lr_pre, lr_post):
    i1 = all_commits.index(lr_pre)
    i2 = all_commits.index(lr_post)

    if i1 == i2:
        return []

    return all_commits[i1+1:i2]


def get_diff(diffs: List[DiagnosticsDiff], pre_commit: str, post_commit: str):
    return next((diff for diff in diffs
                 if diff.pre_commit == pre_commit and diff.post_commit == post_commit))


def get_diffs(diffs: List[DiagnosticsDiff], pre_commit: str, post_commit: str):
    start_diff = next(i for (i, diff) in enumerate(diffs)
                      if diff.pre_commit == pre_commit)

    end_diff = next(i for (i, diff) in enumerate(diffs)
                    if diff.post_commit == post_commit)

    return diffs[start_diff:end_diff+1]


def guess_if_compilation_failed(diags, diag, commit):
    print("leaves in commit", commit)
    i = next(i for (i, diag) in enumerate(diags)
             if diag.commit == commit)
    print("file",diags[i])
    if diag in diags[i].diagnostics:
        print("it's in this diagnostics")
        return False

    if i == 0 or i == len(diags):
        print("at endpoints")
        return False

    before = diags[i-1]
    after = diags[i+1]
    print("looking between", before.commit, after.commit)

    return diag in before.diagnostics and diag in after.diagnostics


def print_missed_interesting_stuff_2(project: Path,
                                     lr_diags: List[DiagnosticsFile],
                                     hr_diags: List[DiagnosticsFile],
                                     lr_diffs: List[DiagnosticsDiff],
                                     hr_diffs: List[DiagnosticsDiff]):
    merged_diags = merge_diagnostics(project, lr_diags, hr_diags)

    missed_diags = 0
    zombie_diags = 0

    for (lr_pre, lr_post) in consecutive_pairs(lr_diags):
        between_commits = find_commits_between(merged_diags, lr_pre, lr_post)
        if len(between_commits) == 0:
            continue

        lr_diff = get_diff(lr_diffs, lr_pre.commit, lr_post.commit)
        print("Checking higher resolution commits between", lr_diff)

        next_lr_commit = next(i for (i, diff) in enumerate(hr_diffs)
                              if diff.post_commit == lr_post.commit)

        # Interesting 1) Diagnostics that appear then disappear entirely between low res commits
        for between_commit in between_commits:
            (enters, diff) = next((i, diff) for (i, diff) in enumerate(hr_diffs)
                                  if diff.post_commit == between_commit.commit)

            # Count every diagnostic added in diff but leaves but ss_diffs[ss_end]
            for added_diag in diff.unmatched_new:
                leaves = find_when_leaves(
                    hr_diffs, added_diag, start=enters, end=next_lr_commit)

                if leaves != next_lr_commit:
                    print(
                        f"Following diagnostic lost by lower resolution between {lr_diff}")
                    print(added_diag)
                    print(
                        f"It enters at {hr_diffs[enters].pre_commit} then leaves at {hr_diffs[leaves].post_commit}")
                    missed_diags += 1

        # Interesting 2) Diagnostics that leave and reenter in a high res commit
        between_hr_diffs = get_diffs(hr_diffs, lr_pre.commit, lr_post.commit)
        print("Between diffs:", between_hr_diffs)
        for (old, _) in lr_diff.matches.items():
            leaves = find_when_leaves(between_hr_diffs, old)
            if leaves != len(between_hr_diffs) and not guess_if_compilation_failed(merged_diags, old, between_hr_diffs[leaves].post_commit):
            # if leaves != len(between_hr_diffs):
                zombie_diags += 1

                print("Diagnostic:", old)
                print("Was tracked between low res ", lr_diff)
                print("However was unmatched across lower res",
                      between_hr_diffs[leaves])


    print("Missed diagnostics", missed_diags)
    print("Zombie diagnostics", zombie_diags)

if __name__ == "__main__":
    project = Path(sys.argv[1])
    print("Loading diagnostics")
    lowres_diags = DiagnosticsFile.load_all(Path(sys.argv[2]))
    highres_diags = DiagnosticsFile.load_all(Path(sys.argv[3]))

    print("Loading comparisons")
    lr_comparisons = DiagnosticsDiff.load_all(Path(sys.argv[4]))
    hr_comparisons = DiagnosticsDiff.load_all(Path(sys.argv[5]))

    print_missed_interesting_stuff_2(
        project,
        lowres_diags,
        highres_diags,
        lr_comparisons,
        hr_comparisons)