#!/bin/python3
import sys
import os
import random

from pathlib import Path

from diag_utils import DiagnosticsDiff, Diagnostic


def inplace_filter(diff: DiagnosticsDiff):
    diff.matches = {old: new
                    for (old, new) in diff.matches.items()
                    if old != new}


def inplace_strat(diff: DiagnosticsDiff, num: int):
    diff.matches = {old: new
                    for (old, new) in strat(list(diff.matches.items()), num)}
    diff.unmatched_old = strat(diff.unmatched_old, num)
    diff.unmatched_new = strat(diff.unmatched_new, num)


def filter_exact_matches(file: Path):
    if not file.exists():
        raise Exception(file + " does not exist")

    diff = DiagnosticsDiff(file)
    inplace_filter(diff)

    diff.write(file.with_suffix(".filtered"))


def strat(items, factor):
    random.shuffle(items)
    return random.sample(items, k=len(items)//factor)


def stratify_findings(file: Path, num: int):
    if not file.exists():
        raise Exception(file + " does not exist")

    diff = DiagnosticsDiff(file)
    inplace_strat(diff, num)
    diff.write(file.with_suffix(".strat"))


def strat_filter(file: Path, num: int):
    if not file.exists():
        raise Exception(file + " does not exist")

    diff = DiagnosticsDiff(file)
    inplace_filter(diff)
    inplace_strat(diff, num)
    diff.write(file.with_suffix(".strat_filtered"))


def remove_overlapping_matches(diff, diff2):
    shared_keys = diff.matches.keys() & diff2.matches.keys()
    if len(shared_keys) == 0:
        return

    dup_keys = set((diag for diag in shared_keys
                    if diff.matches[diag] == diff2.matches[diag]))

    # Uncomment to see examples of transitive tracking
    # if len(shared_keys) > 0 and len(dup_keys) == 0:
    #     print("They both claim to track")
    #     for diag in shared_keys:
    #         print(diag)

    #         print("Here's where", diff, "tracks it")
    #         print(diff.matches[diag])
    #         print("and here's where", diff2, "tracks it")
    #         print(diff2.matches[diag])
    #     print()

    diff2.matches = {old: new
                     for (old, new) in diff2.matches.items()
                     if old not in dup_keys}


def gen_pr_file(dirr: Path, num: int):
    if not dirr.is_dir():
        raise Exception(dirr + " is not a dir")

    # Filter & stratify
    diffs = DiagnosticsDiff.load_all(dirr)
    for diff in diffs:
        inplace_filter(diff)
        inplace_strat(diff, num)

    # Avoid double counting
    for diff in diffs:
        for other in diffs:
            if other == diff:
                continue

            remove_overlapping_matches(diff, other)

    # Write to file
    with open(dirr / "pr_sample", "w") as out:
        def writeln(s): return print(s, file=out)
        for diff in diffs:
            writeln("Sample " + str(diff))
            writeln("Check these are tracked properly:")
            for (old, new) in sorted(diff.matches.items(), key=lambda p: p[0]):
                writeln("  Old " + repr(old))
                writeln("  New " + repr(new))
            writeln("")
            writeln("Check these were removed:")
            for removed in sorted(diff.unmatched_old):
                writeln("  " + repr(removed))
            writeln("")
            writeln("Check these were added:")
            for added in sorted(diff.unmatched_new):
                writeln("  " + repr(added))
            writeln("")


if __name__ == "__main__":
    cmd = sys.argv[1]
    if cmd == "filter":
        filter_exact_matches(Path(sys.argv[2]))
    elif cmd == "strat":
        stratify_findings(Path(sys.argv[2]), int(sys.argv[3]))
    elif cmd == "strat-filter":
        strat_filter(Path(sys.argv[2]), int(sys.argv[3]))
    elif cmd == "gen-pr":
        gen_pr_file(Path(sys.argv[2]), int(
            sys.argv[3]) if len(sys.argv) == 4 else 5)
    else:
        raise Exception("unknown command " + cmd)
