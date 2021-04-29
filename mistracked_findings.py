#!/bin/python3
import sys

from diag_utils import DiagnosticsDiff, Diagnostic, find_when_leaves
from pathlib import Path
from missed_diagnostics_2 import find_missed_commits

Trackers = ["character_line_tracker", "token_line_tracker", "ijm_pos_tracker", "ijm_start_and_end", "ijm_joint"]

def find_between_diffs(interleaved_diffs, lowres_diffs):
    assert len(lowres_diffs) <= len(interleaved_diffs) 

    il_i = 0
    for lr_diff in lowres_diffs:
        il_diff = interleaved_diffs[il_i]

        if il_diff.post_commit != lr_diff.post_commit:
            ir_missing_region = []

            while interleaved_diffs[il_i].post_commit != lr_diff.post_commit:
                ir_missing_region.append(interleaved_diffs[il_i])
                il_i += 1

            ir_missing_region.append(interleaved_diffs[il_i])

            yield (lr_diff, ir_missing_region)

        assert lr_diff.post_commit == lr_diff.post_commit

        il_i += 1


if __name__ == "__main__":
    project = sys.argv[1]
    comparisons_folder = Path(sys.argv[2])

    for tracker in Trackers:
        print("Checking", tracker)
        interleaved_comparisons = DiagnosticsDiff.load_all(
            comparisons_folder / (project + "_" + tracker))

        low_res_comparisons = DiagnosticsDiff.load_all(
            comparisons_folder / (project + "_" + tracker + "_lowres"))

        for (lr_diff, between_diffs) in find_between_diffs(interleaved_comparisons, low_res_comparisons):
            print("Checking low res diff", lr_diff)
            for (old, new) in lr_diff.matches.items():
                leaves = find_when_leaves(between_diffs, old) 
                if leaves != len(between_diffs):
                    print(f"Mistracked finding in {lr_diff}")
                    print(old)
                    print(" to ")
                    print(new)
                    print(f"  But was not tracked over {between_diffs[leaves]}")
                    print()
