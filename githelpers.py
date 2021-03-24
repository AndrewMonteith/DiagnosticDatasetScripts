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