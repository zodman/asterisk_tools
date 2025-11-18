import argparse
import itertools
import json
import sys
import warnings

import rich.console
import rich.json
import rich.text
from pygrok import Grok

# Suppress only UserWarning messages
warnings.filterwarnings("ignore", category=UserWarning)
warnings.filterwarnings("ignore", category=SyntaxWarning)


colors = itertools.cycle(
    ["red", "blue_violet", "plum2", "blue", "magenta", "cyan", "dark_green"]
)
c = rich.console.Console(force_terminal=True)
pattern = "    -- Executing \\[%{GREEDYDATA:extension}@%{GREEDYDATA:context}:%{INT:priority}\\] %{WORD:op}\(%{QS:channel}, %{GREEDYDATA:value}\) in new stack\r\n"
grok = Grok(pattern, fullmatch=False)
channels = {}
output = []


def parse(ln):
    r = grok.match(ln)
    return r


def main(lines, is_debug, no_gosub):
    for idx, ln in enumerate(lines):
        txt = process(idx, ln, is_debug, no_gosub)
        if txt:
            c.print(txt.ljust(4), overflow="ellipsis")


def subprocess(r, expand=True):
    padding = ""
    if "gosub" in r["context"]:
        if expand:
            padding = " " * 20

    if r["channel"] not in channels:
        if colors:
            channels[r["channel"]] = next(colors)

    if "jsonvariable" == r["op"]:
        r["value"] = rich.json.JSON(r["value"][1:-1]).text.markup
    else:
        for op in ["set"]:
            if op in r["op"].lower():
                r["value"] = r["value"][1:-1]

    for op in ["noop", "verbose"]:
        if op in r["op"].lower():
            r["value"] = f"[yellow]{r['value']}[/yellow]"
            if "==" in r["value"]:
                r["value"] = f":arrow_forward: [bold]{r['value']}[/bold]"
    r["op"] = r["op"].rjust(13 if expand else 0)
    for op in ["conf", "dial", "hangup"]:
        if op in r["op"].lower():
            r["op"] = f"[bold yellow]{r['op']}[/bold yellow]"

    ext = r["extension"]
    if "C-" in ext:
        offset = 10
        ext = ext[:offset] + "..." + ext[-1 * (offset - 1) :]
    raw_ctx = f"{ext}@{r['context']}:{str(r['priority']).rjust(3)}".rjust(
        40 if expand else 0
    )
    ctx_ = rich.text.Text(
        raw_ctx,
        style=channels.get(r["channel"].strip(), ""),
    ).markup
    channel_txt = r["channel"].rjust(24 if expand else 0)
    chan = rich.text.Text(
        channel_txt, style=channels.get(r["channel"].strip(), "")
    ).markup
    txt = padding + r"\[" + f"{ctx_}] [cyan]{r['op']}[/cyan]({chan}, {r['value']})"
    return txt


def process(idx, ln, is_debug, no_gosub):
    r = parse(ln)
    if not r and is_debug:
        txt = ln.strip()
        if "exited non-zero on" in txt:
            txt = "[yellow bold on red ] ERROR: [/yellow bold on red ]" + txt
        padding = " " * 32
        if "Asterisk Ready" in txt:
            c.rule(txt)
            return
        c.print(padding + txt)
    if not r:
        return

    output.append(r.copy())
    if "gosub" in r["context"] and no_gosub:
        return
    return subprocess(r)


def write_file(is_write_json):
    if is_write_json:
        with open(args.write, "w") as f:
            json.dump(output, f)
        c.print(f"generate  {args.write}", soft_wrap=False, overflow="ellipsis")


if __name__ == "__main__":
    arg = argparse.ArgumentParser(prog="asterisk-loggger-viewer")
    arg.add_argument(
        "--debug", "-d", action="store_true", help="show non dialplan instructions"
    )
    arg.add_argument(
        "--write",
        "-w",
        default=None,
        help="write dialplan json to a file output.json",
    )

    arg.add_argument("--no-gosub", action="store_true")

    args = arg.parse_args()
    is_write_json = args.write is not None
    is_debug = args.debug
    no_gosub = args.no_gosub

    try:
        main(sys.stdin, is_debug, no_gosub)
    except KeyboardInterrupt:
        pass
    finally:
        write_file(is_write_json)
