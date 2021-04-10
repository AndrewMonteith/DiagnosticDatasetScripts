import subprocess
import tempfile

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


def checkout(project: Path, commit: str):
    subprocess.run(["git", "checkout", "."], cwd=project)
    subprocess.run(["git", "clean", "-fd"], cwd=project)
    #    stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    subprocess.run(["git", "pull", "origin", "master"], cwd=project)
    #    stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    subprocess.run(["git", "checkout", commit], cwd=project)
    #    stdout=subprocess.PIPE, stderr=subprocess.PIPE)


def get_all_files_in_commit(project: Path, commit: str):
    proc = subprocess.run(["git", "ls-tree", "--full-tree", "-r", commit],
                          cwd=project, stdout=subprocess.PIPE)

    def get_file_name(line):
        if len(line) == 0:
            return None

        by_spaces = line.split(" ")
        return by_spaces[2].split("	")[-1]

    return set((get_file_name(line)
                for line in proc.stdout.decode("utf-8").split("\n")))
