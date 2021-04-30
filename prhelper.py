#!/bin/python3
import tkinter as tk
import sys

from diag_utils import Diagnostic, DiagnosticsDiff
from pathlib import Path
from meyersdiff import *
from matchhelper2 import FileLoader

from itertools import chain

'''
    Butchered from: https://stackoverflow.com/questions/14910858/how-to-specify-where-a-tkinter-window-opens
'''


class TextLineNumbers(tk.Canvas):
    def __init__(self, *args, **kwargs):
        tk.Canvas.__init__(self, *args, **kwargs)
        self.textwidget = None

    def attach(self, text_widget):
        self.textwidget = text_widget

    def redraw(self, *args):
        '''redraw line numbers'''
        self.delete("all")

        i = self.textwidget.index("@0,0")
        while True:
            dline = self.textwidget.dlineinfo(i)
            if dline is None:
                break
            y = dline[1]
            linenum = str(i).split(".")[0]
            self.create_text(2, y, anchor="nw", text=linenum)
            i = self.textwidget.index("%s+1line" % i)


class CustomText(tk.Text):
    def __init__(self, *args, **kwargs):
        tk.Text.__init__(self, *args, **kwargs)

        # create a proxy for the underlying widget
        self._orig = self._w + "_orig"
        self.tk.call("rename", self._w, self._orig)
        self.tk.createcommand(self._w, self._proxy)

    def _proxy(self, *args):
        # let the actual widget perform the requested action
        cmd = (self._orig,) + args
        result = self.tk.call(cmd)

        # generate an event if something was added or deleted,
        # or the cursor position changed
        if (args[0] in ("insert", "replace", "delete") or
            args[0:3] == ("mark", "set", "insert") or
            args[0:2] == ("xview", "moveto") or
            args[0:2] == ("xview", "scroll") or
            args[0:2] == ("yview", "moveto") or
            args[0:2] == ("yview", "scroll")
            ):
            self.event_generate("<<Change>>", when="tail")

        # return what the actual widget returned
        return result


class Example(tk.Frame):
    def __init__(self, *args, **kwargs):
        tk.Frame.__init__(self, *args, **kwargs)
        self.configure(background='black')
        self.text = CustomText(self)
        self.vsb = tk.Scrollbar(self, orient="vertical",
                                command=self.text.yview)
        self.text.configure(yscrollcommand=self.vsb.set, font=("Arial", 14))
        self.text.tag_configure("bigfont", font=("Helvetica", "24", "bold"))
        self.text.configure(background='black', foreground='white')
        self.linenumbers = TextLineNumbers(self, width=30)
        self.linenumbers.attach(self.text)

        self.vsb.pack(side="right", fill="y")
        self.linenumbers.pack(side="left", fill="y")
        self.text.pack(side="right", fill="both", expand=True)

        self.text.bind("<<Change>>", self._on_change)
        self.text.bind("<Configure>", self._on_change)

    def _on_change(self, event):
        self.linenumbers.redraw()


class Window(tk.Frame):
    def __init__(self, dialog_text, master=None):
        tk.Frame.__init__(self, master)
        self.master = master
        self.configure(background='black')
        self.pack(fill=tk.BOTH, expand=1)

        self.text = tk.Label(self, text=dialog_text, font=(
            "Arial", 12), wraplength=(1920/2-10))
        self.text.pack()


def find_closest_line(text, index, new_text):
    diffs = myers_diff(text, new_text)

    line = 0
    new_line = 0
    for diff in diffs:
        if isinstance(diff, Keep):
            line += 1
            new_line += 1
        elif isinstance(diff, Insert):
            new_line += 1
        elif isinstance(diff, Remove):
            line += 1

        if line == index:
            return new_line


def set_line_col(text, line, col):
    tag = "tag-" + str(line+1)
    text.tag_add(tag, str(line) + ".0", str(line) + ".100")
    text.tag_config(tag, foreground=col)


def add_diff_highlighting(e_old, e_new, diffs):
    # Highlight left hand side
    line = 1

    for diff in diffs:
        if isinstance(diff, Insert):
            continue
        if isinstance(diff, Remove):
            set_line_col(e_old, line, "red")
        line += 1

    line = 1
    for diff in diffs:
        if isinstance(diff, Remove):
            continue
        if isinstance(diff, Insert):
            set_line_col(e_new, line, "green")
        line += 1


def convert_pos_to_line_col(lines, position):
    if type(lines) is str:
        lines = lines.split("\n")
    for (line_num, line) in enumerate(lines):
        line_len = len(line) + 1
        if position - line_len > 0:
            position -= line_len
        else:
            return (line_num + 1, position)


def highlight_text(textbox, src_lines, start, end):
    start_line, start_col = convert_pos_to_line_col(src_lines, start)
    end_line, end_col = convert_pos_to_line_col(src_lines, end)

    tag = "tag-" + str(start) + "-" + str(end)
    textbox.tag_add(tag, str(start_line) + "." + str(start_col),
                    str(end_line) + "." + str(end_col))
    textbox.tag_config(tag, foreground="yellow")


def set_line(text, line):
    text.text.see(str(max(0, line - 3)) + ".0")


pause = False


def ask_question(old_src: str, new_src: str, **kwargs):
    windows = []

    # Dialog showing old source code
    old_src_tk = tk.Tk()
    ws = old_src_tk.winfo_screenwidth()
    hs = old_src_tk.winfo_screenheight()
    e_old = Example(old_src_tk)
    e_old.pack(side="top", fill="both", expand=True)
    e_old.text.delete(1.0, "end")
    e_old.text.insert(1.0, ''.join(old_src))
    # e_old.text.see('158.0')
    old_src_tk.geometry("%dx%d+%d+%d" % (ws/2 - 20, 1080-250+5, 0, 200))
    windows.append(old_src_tk)

    # Dialog showing new source code
    new_src_tk = tk.Tk()
    e_new = Example(new_src_tk)
    e_new.pack(side="top", fill="both", expand=True)
    e_new.text.delete(1.0, "end")
    e_new.text.insert(1.0, ''.join(new_src))
    new_src_tk.geometry("%dx%d+%d+%d" % (ws/2 - 20, 1080-250+5, (ws/2), 200))
    windows.append(new_src_tk)

    add_diff_highlighting(e_old.text, e_new.text, myers_diff(old_src, new_src))

    old_in = "old_diag" in kwargs
    new_in = "new_diag" in kwargs

    old_diag_window = None
    if old_in:
        # Dialog showing old diagnostic
        old_diag_dialog = tk.Tk()
        old_diag_window = Window(str(kwargs["old_diag"]), old_diag_dialog)
        old_diag_dialog.wm_title("Old Diagnostic in " + kwargs["old_commit"])
        old_diag_dialog.geometry("%dx%d+%d+%d" % (ws/2 - 20, 150, 5, 10))
        windows.append(old_diag_dialog)

        highlight_text(e_old.text, old_src,
                       kwargs["old_diag"]._start, kwargs["old_diag"]._end)

    new_diag_window = None
    if new_in:
        # Dialog showing new diagnostic
        new_diag_dialog = tk.Tk()
        new_diag_window = Window(str(kwargs["new_diag"]), new_diag_dialog)
        new_diag_dialog.wm_title("New Diagnostic in " + kwargs["new_commit"])
        new_diag_dialog.geometry("%dx%d+%d+%d" %
                                 (ws/2 - 20, 150, ws/2 + 5, 10))
        windows.append(new_diag_dialog)
        highlight_text(e_new.text, new_src,
                       kwargs["new_diag"]._start, kwargs["new_diag"]._end)

    if old_in and new_in:
        set_line(e_old, kwargs["old_diag"]._line)
        set_line(e_new, kwargs["new_diag"]._line)
    elif old_in:
        set_line(e_old, kwargs["old_diag"]._line)
        set_line(e_new, find_closest_line(
            old_src, kwargs["old_diag"]._line, new_src))
    else:
        set_line(e_old, find_closest_line(
            new_src, kwargs["new_diag"]._line, old_src))
        set_line(e_new, kwargs["new_diag"]._line)

    response = None

    def key_pressed(event):
        global pause
        nonlocal response
        if event.char == '#':
            pause = not pause
        if pause:
            return
        if event.char == 'i':
            print("Interesting")
            if old_diag_window is not None:
                print(old_diag_window.text.cget("text"))
            if new_diag_window is not None:
                print(new_diag_window.text.cget("text"))
        if event.char not in ["y", "n", "s"]:
            return

        response = event.char
        for window in windows:
            window.destroy()

    old_src_tk.bind("<Key>", key_pressed)

    for window in windows:
        window.mainloop()

    if response == 'y':
        return True
    elif response == 'n':
        return False
    else:
        return None


def prelaod_file(project, diffs):
    diagnostics = set(chain([*diff.matches.keys(), *diff.matches.values(),
                             *diff.unmatched_new, *diff.unmatched_new]) for diff in diffs)

    return FileLoader.preload_diagnostics(project, diagnsotics)


if __name__ == "__main__":
    project = Path(sys.argv[1])
    diff_path = Path(sys.argv[2])
    diffs = DiagnosticsDiff.load_all(diff_path)

    matches_to_check = sum(len(diff.matches) for diff in diffs)
    # moves_to_check = sum(len(diff.unmatched_old) for diff in diffs)
    adds_to_check = sum(len(diff.unmatched_new) for diff in diffs)

    print("Total matches ", matches_to_check)
    # print("Total removes ", removes_to_check)
    print("Total adds ", adds_to_check)

    true_positives = 0
    false_positives = 0
    false_negatives = 0

    total_matches_checked = 0
    total_removes_checked = 0
    total_adds_checked = 0
    skipped = 0

    for diff in diffs:
        print("Diff", diff)

        file_loader = FileLoader.load_diff(project, diff)

        # Check matches
        for (old, new) in diff.matches.items():
            old_src = file_loader.load(old._file, diff.pre_commit)
            new_src = file_loader.load(new._file, diff.post_commit)

            if old_src == new_src and old == new:
                continue

            total_matches_checked += 1

            response = ask_question(
                old_src, new_src, old_diag=old, new_diag=new, old_commit=f"{diff.pre} {diff.pre_commit}", new_commit=f"{diff.post} {diff.post_commit}")

            if response == None:
                skipped += 1
                continue
            elif response:
                print("TP")
                print(old)
                print("  to")
                print(new)
                true_positives += 1
            else:
                print("FP")
                print(old)
                print("  to")
                print(new)
                false_positives += 1

        # Check unmatched old
        for unmatched_old in diff.unmatched_old:
            old_src = file_loader.load(unmatched_old._file, diff.pre_commit)
            new_src = file_loader.load(unmatched_old._file, diff.post_commit)

            if len(new_src) == 0:
                continue

            response = ask_question(
                old_src, new_src, old_diag=unmatched_old, old_commit=f"{diff.pre} {diff.pre_commit}")
            if response == None:
                skipped += 1
                continue

            total_removes_checked += 1

            if response == False:
                false_negatives += 1
                print("FN")
                print(unmatched_old)

        # Check unmatched new
        # for unmatched_new in diff.unmatched_new:
        #     old_src = file_loader.load(unmatched_new._file, diff.pre_commit)
        #     new_src = file_loader.load(unmatched_new._file,  diff.post_commit)

        #     if len(old_src) == 0:
        #         continue

        #     total_adds_checked += 1

        #     response = ask_question(old_src, new_src, new_diag=unmatched_new)

        #     if response == None:
        #         skipped += 1
        #         continue

        #     total_adds_checked += 1

        #     if response == False:
        #         print("FN")
        #         print(unmatched_new)
        #         false_negatives += 1

    print("True positives", true_positives)
    print("False positives", false_positives)
    print("False negatives", false_negatives)

    print("Total matches checked", total_matches_checked)
    print("Total adds checked", total_adds_checked)
    print("Total removes checked", total_removes_checked)
    print("Total skips", skipped)
