from rich import print_json
from rich.text import Text
import rich.console
import argparse
import subprocess

parser = argparse.ArgumentParser(description="Show active Asterisk channels")
parser.add_argument("container", help="Asterisk docker container name")
parser.add_argument("--json", action="store_true",
                    help="Output in JSON format")
parser.add_argument("--devsys3", action="store_true", help="Run on devsys3")
parser.add_argument("--plain", action="store_true", help="plain")

args, unknown = parser.parse_known_args()

container = args.container
is_json = args.json
is_devsys3 = args.devsys3
is_voip = "voip" in container
is_plain = args.plain


def run(cmd):
    if is_devsys3:
        cmd_run = f'ssh devsys3 -t "sudo {cmd}"'
    else:
        cmd_run = cmd

    return subprocess.run(
        cmd_run,
        shell=True,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()


c = rich.console.Console()

DATA = {}

bridge_key = "Bridge ID"


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
    # bridge_name = d.get("Data").split(",")[0]
    bridge_name = d.get(bridge_key)
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

    if is_json:
        return

    c.print(
        f"{who}{ast} ({from_}) Caller: [blue]{caller_display[:30].ljust(30)}{
            '...' if len(caller_display) > 30 else '   '
        }[/blue]"
        r"\[" + f"{ext}[yellow]@[/yellow]{ctx}: {prior}]"
        f" App: {app} "
        f"[green]=>[/green] "
        f"Chan: {channel} {link}"
    )


cmd = f"docker exec {container} asterisk -rx 'core show channels concise'"
concise = run(cmd)
lines = concise.splitlines()
results = []

for line in lines:
    if "LC_ALL" in line:
        continue
    ln = line.split("!")
    channel_name, ctx, exten, context, *_ = ln
    bridge_id = ln[-2]
    # if "Message/ast" in channel_name or "CBAnn" in channel_name:
    #     continue
    cmd = f" docker exec {
        container}  asterisk -rx 'core show channel {channel_name}'"
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

results = sorted(results, key=lambda x: x.get(bridge_key, ""))
last_data = ""
for d in results:
    data = d.get(bridge_key, "").strip()
    tmp_data = data
    if "," in data:
        data = data.split(",")[0]
    if data != last_data:
        c.rule(f"{bridge_key}: {tmp_data}")
        last_data = data
    display(d)

if is_json:
    print_json(data=DATA)
# vim: set ft=python:
