import sys
import json
from rich.console import Console
from rich.console import Group
from rich.columns import Columns
from rich.panel import Panel
from rich.text import Text
from readlogs import subprocess


def get_display(e):
    text = subprocess(e)
    ln = e.get("ln", "")
    return Text.from_markup(ln.rjust(3) + " " + text, overflow="ellipsis")
    # return Text.from_markup(text, overflow="ellipsis")


_, filename, *_ = sys.argv
with open(filename) as f:
    data = json.loads(f.read())

stack = {}
for idx, entry in enumerate(data):
    entry.update({"ln": str(idx)})
    chan = entry.get("channel")
    stack.setdefault(chan, [])
    stack[chan].append(get_display(entry))

cons = Console(force_terminal=True)

c = Columns([Panel(Group(*i)) for i in stack.values()], expand=True)
cons.print(c, soft_wrap=False, overflow="ellipsis")
