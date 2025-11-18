import sys
import json
from rich import print
from rich.console import Console
from rich.console import Group
from rich.columns import Columns
from rich.panel import Panel
from rich.text import Text
from readlogs import subprocess


def get_display(entry):
    text = subprocess(entry, expand=False)
    ln = entry.get("ln", "")
    return Text.from_markup(ln.rjust(3) + " " + text, overflow="ellipsis")
    # return Text.from_markup(text, overflow="ellipsis")


_, filename, chan_number, *_ = sys.argv
with open(filename) as f:
    data = json.loads(f.read())

stack = {}
for idx, entry in enumerate(data):
    entry.update({"ln": str(idx)})
    chan = entry.get("channel")
    stack.setdefault(chan, [])
    stack[chan].append(get_display(entry))

cons = Console(force_terminal=True)

for idx, entry in enumerate(data):
    entry.update({"ln": str(idx)})
    chan = entry.get("channel")
    if chan == list(stack.keys())[int(chan_number)]:
        c = get_display(entry)
    else:
        ln = entry.get("ln", "")
        c = ln.rjust(3)
    cons.print(c, no_wrap=True, overflow="ellipsis")
