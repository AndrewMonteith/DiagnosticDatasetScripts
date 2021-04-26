import subprocess
import shutil
import tempfile
import re

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


def get_changed_java_files(project: Path, pre_commit: str, post_commit: str):
    proc = subprocess.run(["git", "diff", "--name-only", pre_commit, post_commit],
                          cwd=project, stdout=subprocess.PIPE)

    changed_files = proc.stdout.decode("utf-8").split("\n")

    return set((changed_file
                for changed_file in changed_files
                if len(changed_file) > 0 and Path(changed_file).suffix == ".java"))


def load_file(project: Path, commit: str, file: str):
    proc = subprocess.run(["git", "show", commit + ":" + str(file)],
                          cwd=project, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

    src = proc.stdout.decode("utf-8")
    if f"'{commit}'" in src:
        return "Does not exist", False
    else:
        return src, True


def init(project: Path):
    git_folder = project / ".git"
    if git_folder.is_dir():
        shutil.rmtree(git_folder)

    subprocess.run(["git", "init"], cwd=project, stdout=subprocess.PIPE)


extract_commit_re = re.compile(r" (\w+)\]")


def commit_all(project: Path):
    subprocess.run(["git", "add", "-A"], cwd=project, stdout=subprocess.PIPE)

    proc = subprocess.run(
        ["git", "commit", "-m", "'commit'"], cwd=project, stdout=subprocess.PIPE)
    commit_match = re.search(extract_commit_re, proc.stdout.decode("utf-8"))
    short_commit = commit_match.group(1)

    all_commits = get_all_commits(project)
    
    return next(commit for commit in all_commits
                if commit.startswith(short_commit))
