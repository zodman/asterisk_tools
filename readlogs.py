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

prefix_begin_line = "    -- "
begin_line = prefix_begin_line + "Executing"
context_line = " \\[%{GREEDYDATA:extension}@%{GREEDYDATA:context}:%{INT:priority}\\] "
function_line = r"%{WORD:op}\(%{QS:channel},"
greedy_line = r" %{GREEDYDATA:value}\)"

end_line = " in new stack\r\n"

pattern = begin_line + context_line + function_line + greedy_line + end_line

grok = Grok(pattern, fullmatch=True)

grok_message = Grok(
    (begin_line + context_line + function_line + "%{GREEDYDATA:any}"),
    fullmatch=False,
)


channels = {}
output = []


def parse(ln):
    r = grok.match(ln)
    return r


def main(lines, is_debug, no_gosub, expand_json):
    for idx, ln in enumerate(lines):
        txt = process(idx, ln, is_debug, no_gosub, expand_json)
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

    if "jsonvariables" == r["op"]:
        try:
            r["value"] = rich.json.JSON(r["value"][1:-1]).text.markup
        except Exception:
            c.print('ERROR parsing json {r["value"]}')
    else:
        for op in ["set"]:
            if op in r["op"].lower():
                r["value"] = r["value"][1:-1]
            value = r["value"]
            # DISPLAY ICP message
            if "IIX:BORROW" in value and r["op"].lower() == "set":
                r["value"] = "\n".join(r["value"].split("\r")[:-1])

    for op in ["noop", "verbose"]:
        if op in r["op"].lower():
            r["value"] = f"[yellow]{r['value']}[/yellow]"
            if "==" in r["value"]:
                r["value"] = f":arrow_forward: [bold]{r['value']}[/bold]"
    r["op"] = r["op"].rjust(13 if expand else 0)
    for op in ["conf", "dial", "hangup", "originate"]:
        if op in r["op"].lower():
            r["op"] = f"[bold yellow]{r['op']}[/bold yellow]"

    ext = r["extension"]
    if "C-" in ext:
        offset = 10
        ext = ext[:offset] + "..." + ext[-1 * (offset - 1):]
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
    txt = padding + r"\[" + f"{ctx_}] [cyan]{r['op']
                                             }[/cyan]({chan}, {r['value']})"
    return txt


buffer = []


def process(idx, ln, is_debug, no_gosub, expand_json=False):
    global buffer
    r = parse(ln)
    if not r and is_debug:
        txt = ln.strip()

        if len(buffer) > 0:
            buffer.append(ln)
        if txt.startswith(begin_line.strip()) and not txt.endswith(end_line.strip()):
            # message detected
            r2 = grok_message.match(ln)
            if r2 is not None:
                buffer.append(ln)
        if not txt.startswith(begin_line.strip()) and txt.endswith(end_line.strip()):
            new_line = "".join(buffer)
            new_line = new_line.replace("\r\n" + prefix_begin_line, "\r")
            buffer = []
            r = parse(new_line)

        if "exited non-zero on" in txt:
            txt = "[yellow bold on red ] ERROR: [/yellow bold on red ]" + txt
        padding = " " * 32
        if "Asterisk Ready" in txt:
            c.rule(txt)
            return
        if not r and len(buffer) == 0:
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
        c.print(f"generate  {args.write}",
                soft_wrap=False, overflow="ellipsis")


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
    arg.add_argument("--expand-json", action="store_true")

    args = arg.parse_args()
    is_write_json = args.write is not None
    is_debug = args.debug
    no_gosub = args.no_gosub

    try:
        main(sys.stdin, is_debug, no_gosub, args.expand_json)
    except KeyboardInterrupt:
        pass
    finally:
        write_file(is_write_json)
