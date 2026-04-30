#!/usr/bin/env nix-shell
#!nix-shell -i python3

import argparse
import itertools
import json
import re
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

_prefix_begin_line = r"\s*-- "
prefix_begin_line = _prefix_begin_line
begin_line = prefix_begin_line + "Executing"
context_line = " \\[%{GREEDYDATA:extension}@%{GREEDYDATA:context}:%{INT:priority}\\] "
function_line = r"%{WORD:op}\(%{QS:channel},"
greedy_line = r" %{GREEDYDATA:value}\)"

_end_line = " in new stack("
end_line = _end_line + "\n|\r\n)"

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
            c.print(f'ERROR parsing json {r["value"]}')
    else:
        for op in ["set"]:
            if op in r["op"].lower():
                r["value"] = r["value"][1:-1]
            value = r["value"]
            # DISPLAY ICP message
            if "IIX:BORROW" in value and r["op"].lower() == "set":
                r["value"] = r["value"].replace("\r", " ").replace("\n", " ")

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
    txt = padding + r"\[" + f"{ctx_}] [cyan]{r['op']}[/cyan]({chan}, {r['value']})"
    return txt


buffer = []


def process(idx, ln, is_debug, no_gosub, expand_json=False):
    global buffer
    
    # Identify if this line starts a new execution block
    if re.search(r'^\s*-- Executing', ln):
        if buffer and is_debug:
            # Flush previous incomplete buffer as debug text
            # (Note: we can't easily return multiple lines here without changing main, 
            # so we just print them and return None)
            for b_ln in buffer:
                c.print(" " * 32 + b_ln.strip())
        buffer = [ln]
        # If it also ends in the same line, process it immediately
        if " in new stack" not in ln:
            return None
    
    if buffer:
        if ln not in buffer: # Avoid double adding if begin_line check already added it
            buffer.append(ln)
        
        if " in new stack" not in ln:
            return None
        
        # Block is complete
        current_buffer = buffer
        buffer = []
        
        # Normalize: Join lines and remove prefix "-- " from subsequent lines
        normalized = current_buffer[0].rstrip("\r\n")
        for extra in current_buffer[1:]:
            # Use space to keep the entire block on one line
            cleaned = re.sub(r'^\s*--\s*', '', extra)
            normalized += " " + cleaned.strip()
        
        if not normalized.endswith("\n"):
            normalized += "\n"
        
        r = parse(normalized)
        if r:
            output.append(r.copy())
            if "gosub" in r["context"] and no_gosub:
                return None
            return subprocess(r)
        elif is_debug:
            # Return joined block as raw text
            return "\n".join([" " * 32 + b.strip() for b in current_buffer])
        return None

    # Not in a block
    if is_debug:
        txt = ln.strip()
        if "exited non-zero on" in txt:
            txt = "[yellow bold on red ] ERROR: [/yellow bold on red ]" + txt
        padding = " " * 32
        if "Asterisk Ready" in txt:
            c.rule(txt)
            return None
        return padding + txt
    
    return None


def write_file(is_write_json):
    if is_write_json:
        with open(args.write, "w") as f:
            json.dump(output, f)
        c.print(f"generate  {args.write}",
                soft_wrap=False, overflow="ellipsis")


if __name__ == "__main__":
    arg = argparse.ArgumentParser(prog="asterisk-logger-viewer")
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
    arg.add_argument("--expand-json", action="store_true", default=False)

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
