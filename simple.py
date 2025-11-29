import argparse
import itertools
import json
import sys
import warnings

import rich.console
import rich.json
import rich.text
from rich import print_json as p
from pygrok import Grok


from signal import signal, SIGPIPE, SIG_DFL

signal(SIGPIPE, SIG_DFL)

# Suppress only UserWarning messages
warnings.filterwarnings("ignore", category=UserWarning)
warnings.filterwarnings("ignore", category=SyntaxWarning)

pattern = (
    "    "
    "-- Executing "
    "\\[%{EXTENSION:extension}@%{GREEDYDATA:context}:%{INT:priority}\\]"
    " %{WORD:op}"
    r"\(\"%{CHANNEL:channel}\", %{GREEDYDATA:value}\)"
    " in new stack\r\n"
)

extension_patterns = {
    "EXT_S": r"\w",
    "EXT_NAMED": r"\b[A-Za-z]+\b",
    "EXT_BRIDGE_NAME": "[0-9]?C-%{WORD}",
    "EXTENSION": "(:?%{EXT_S:start}|%{EXT_BRIDGE_NAME:ext_bridge_name}"
    "|%{EXT_NAMED:ext_named}|%{GREEDYDATA})",
}

channel_patterns = {
    "AST": r"Message\/ast_msg_queue",
    "PJSIP": r"PJSIP\/[0-9\-]+",
    "IAX2": r"IAX2\/%{WORD:chan_iax2_trunk}-%{INT}",
    "CHANNEL": r"(:?%{PJSIP:chan_pjsip}|%{IAX2:chan_iax2}|%{AST:chan_ast}|\S+)",
}

grok = Grok(
    pattern, custom_patterns=extension_patterns | channel_patterns, fullmatch=False
)
channels = {}
output = []

for ln in sys.stdin:
    resp = grok.match(ln)
    if resp:
        p(data=resp)
