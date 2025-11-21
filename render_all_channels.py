import sys
import json
from rich.console import Console
from rich.console import Group
from rich.columns import Columns
from rich.panel import Panel
from rich.text import Text
from rich import print
from readlogs import subprocess
import argparse


def get_display(e):
    text = subprocess(e)
    ln = e.get("ln", "")
    return Text.from_markup(ln.rjust(3) + " " + text, overflow="ellipsis")
    # return Text.from_markup(text, overflow="ellipsis")


def main(filename):
    if "-" == filename:
        data = json.loads(sys.stdin.read())
    else:
        with open(filename) as f:
            data = json.loads(f.read())

    stack = {}
    for idx, entry in enumerate(data):
        entry.update({"ln": str(idx)})
        chan = entry.get("channel")
        stack.setdefault(chan, [])
        line = get_display(entry)
        stack[chan].append(line)

    cons = Console(force_terminal=True)

    c = Columns([Panel(Group(*i)) for i in stack.values()], expand=True)
    cons.print(c, overflow="ellipsis", no_wrap=True, soft_wrap=True)


if __name__ == "__main__":
    par = argparse.ArgumentParser("render_all_channels")
    par.add_argument("filename", help="dialplan in json format")
    main(par.parse_args().filename)
