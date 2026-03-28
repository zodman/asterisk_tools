import sys
from rich import print, print_json
from rich.text import Text
import rich.console

import subprocess

is_voip = False
for i in sys.argv:
    if "voip" in i:
        is_voip = True

container = sys.argv[1]

is_json = False
if "--json" in sys.argv:
    is_json = True

preffix = ""
if len(sys.argv) > 2:
    preffix = sys.argv[2]


def run(cmd):
    return subprocess.run(
        cmd,
        shell=True,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()


c = rich.console.Console()

DATA = {}


def get_who(channel_name):
    who = " " * 10
    ast = " "
    dis = "[bold red]DISPATCHER[/bold red]"
    client = "[cyan]CLIENT    [/cyan]"
    if is_voip:
        if "PJSIP" in channel_name:
            ast = "*"
            who = dis
        if "IAX2" in channel_name:
            who = client
    else:
        if "PJSIP" in channel_name:
            who = client
        if "IAX2" in channel_name:
            ast = "*"
            who = dis
    return who, ast


def get_link(channel_name):
    link = ""
    where = "in pbx" if is_voip else "in voip"
    if "IAX2" in channel_name:
        cmd = run(f"docker exec {container} asterisk -rx 'iax2 show channels'")
        for i in cmd.splitlines():
            if channel_name in i:
                chan = i.split()
                _, _, trunk, link_ids, *_ = chan
                _, id_to = link_ids.split("/")
                link = f"~ [magenta]IAX2/{trunk}-{
                    int(id_to)}[/magenta] {where}"
    return link


def display(d):
    bridge_name = d.get("Data").split(",")[0]
    DATA.setdefault(bridge_name, [])
    DATA[bridge_name].append(d)
    channel_name = d.get("Name")
    caller_display = f"{d.get('Caller ID')} - {d.get('Caller ID Name')} "
    who, ast = get_who(channel_name)
    link = get_link(channel_name)
    ext = d.get("Extension", "")
    len_ext = 15
    size = 6
    if len(ext) > len_ext:
        ext = f"{ext[0:size]}...{ext[-1 * size:]}"
    ext = ext.rjust(len_ext)
    is_bold = "CBAnn" not in channel_name
    style = f"yellow {'bold' if is_bold else ''}"
    channel = Text(channel_name.rjust(23), style=style).markup
    ctx = d.get("Context", "").ljust(15)
    app = d.get("Application", "").ljust(10)
    prior = d.get("Priority", "").rjust(2)
    from_ = d.get("FROM", d.get("from", "")).rjust(8)

    if "--json" in sys.argv:
        return

    c.print(
        f"{who}{ast} ({from_}) Caller: [blue]{caller_display.ljust(32)}[/blue]"
        r"\[" + f"{ext}[yellow]@[/yellow]{ctx}: {prior}] {app} "
        "[green]=>[/green] Chan: "
        f"{channel} {link}"
    )


concise = run(
    f"{preffix} docker exec {container} asterisk -rx 'core show channels concise'"
)
lines = concise.splitlines()
results = []
for line in lines:
    ln = line.split("!")
    channel_name, ctx, exten, context, *_ = ln
    bridge_id = ln[-2]
    # print([channel_name, exten, bridge_id])
    if "Message/ast" in channel_name or "CBAnn" in channel_name:
        continue
    cmd = f"{preffix} docker exec {container}  asterisk -rx 'core show channel {
        channel_name
    }'"
    show = run(cmd)
    d = {}
    for ln in show.splitlines():
        if ":" in ln:
            char = ":"
        elif "=" in ln:
            char = "="
        else:
            continue
        key, value, *_ = ln.split(char)
        d.setdefault(key.strip(), value.strip())
    if d != {}:
        results.append(d)

results = sorted(results, key=lambda x: x.get("Data"))
last_data = ""
for d in results:
    data = d.get("Data").strip()
    tmp_data = data
    if "," in data:
        data = data.split(",")[0]
    if data != last_data:
        c.rule(f"Data: {tmp_data}")
        last_data = data
    display(d)

if is_json:
    print_json(data=DATA)

# vim: set ft=python:
