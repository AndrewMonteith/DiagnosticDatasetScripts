#!/bin/python3
import matplotlib.pyplot as plt
import numpy as np
import sys

from pathlib import Path

from diag_utils import Diagnostic, DiagnosticsDiff, find_when_leaves


SCALE_FACTOR = 1


def recover_original_diagnostics(file: DiagnosticsDiff):
    return [*file.unmatched_old, *file.matches.keys()]


def diag_lifetime(diag_and_lifetime):
    (_, (enter, leave)) = diag_and_lifetime
    return leave-enter


def scale(factor, d):
    result = []
    for i in d:
        result.extend((i for _ in range(factor)))
    return result


def gen_pixel_row(enter, leave, total):
    def pixel(i):
        if enter <= i <= leave:
            return 0  # black for yes
        else:
            return 1  # white for no

    return scale(SCALE_FACTOR, [pixel(i) for i in range(1, total+1)])


def generate_image_plot(commit_and_diag_info):
    result = []
    for diag_and_lifetimes in commit_and_diag_info:
        if len(diag_and_lifetimes) == 0:
            continue

        diag_and_lifetimes = sorted(diag_and_lifetimes,
                                    reverse=True,
                                    key=diag_lifetime)

        for (_, (enter, leave)) in diag_and_lifetimes:
            result.append(gen_pixel_row(
                enter+1, leave+1, len(commit_and_diag_info)-1))

    return result


def show_image(bitmask):
    num_of_commits = len(bitmask[0]) / SCALE_FACTOR

    plt.title(
        f"Induvidual diagnostics tracked over {num_of_commits} commits", fontsize=18)
    plt.xticks(np.arange(1, len(bitmask[0])+2, SCALE_FACTOR), rotation=90)
    plt.xlabel("Commit", fontsize=15)
    plt.ylabel("Diagnostic", fontsize=15)
    plt.pcolormesh(bitmask, cmap=plt.cm.gray)

    plt.show()


def gen_diag_timeline(project: Path):
    if not project.exists():
        raise Exception(project + " is not a folder")

    print("Generating for project " + project.stem)
    all_diffs = DiagnosticsDiff.load_all(project)

    starting_diags = recover_original_diagnostics(all_diffs[0])
    max_commit = max(diff.post for diff in all_diffs)

    # Find where all the starting diagnostics leave
    commit_and_diag_info = [[] for _ in range(max_commit)]
    for diag in starting_diags:
        commit_and_diag_info[0].append(
            (diag, (0, find_when_leaves(all_diffs, diag))))

    # Find when any diffs added in the future leaves
    for (i, diff) in enumerate(all_diffs):
        for added_diag in diff.unmatched_new:
            leaves = find_when_leaves(all_diffs, added_diag, start=i+1)
            commit_and_diag_info[diff.pre].append((added_diag, (i, leaves)))

    bitmask = generate_image_plot(commit_and_diag_info)

    show_image(bitmask)


def gen_total_timeline(proj: Path):
    all_diffs = DiagnosticsDiff.load_all(proj)

    labels = [i for i in range(1, len(all_diffs)+1)]
    number_of_diags_in_commit = [len(diff.matches.values()) + len(diff.unmatched_new)
                                 for diff in all_diffs]
    x_pos = [i for i, _ in enumerate(labels)]

    plt.bar(x_pos, number_of_diags_in_commit, color='black')
    plt.xlabel("Commit", fontsize=15)
    plt.ylabel("Number of diagnostics", fontsize=15)
    plt.title("Total number of diagnostics over 40 sequential commits", fontsize=18)

    plt.xticks(x_pos, labels)

    plt.show()


if __name__ == "__main__":
    cmd = sys.argv[1]
    proj = Path(sys.argv[2])

    if cmd == "diagnostics":
        gen_diag_timeline(proj)
    elif cmd == "totals":
        gen_total_timeline(proj)
    else:
        raise Exception("Unrecognised command " + cmd)
