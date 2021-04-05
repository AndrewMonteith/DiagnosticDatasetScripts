import subprocess

from pathlib import Path
from typing import List


def get_all_commits(project: Path) -> List[str]:
    proc = subprocess.run(["git", "log", "--pretty=oneline"],
                          cwd=project, stdout=subprocess.PIPE)

    return [
        line.strip().split(" ")[0]
        for line in proc.stdout.decode("utf-8").strip().split("\n")
    ][::-1]


def is_renamed(project: Path, file1: Path, file2: Path):
    git_stat = subprocess.run(["git", "log", "--oneline", "--name-only", "--follow", "--", str(file2)],
                              cwd=project, stdout=subprocess.PIPE)

    return any(str(file2) in line for line in git_stat.stdout.decode("utf-8").split("\n"))

