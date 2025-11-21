import pyparsing as pp
import unittest

basic_one = """
[from-trunk]
; Handle incoming calls
exten => _X.,1,NoOp(Incoming call from ${CALLERID(num)})
same => n,Answer()
same => n,Playback(hello-world)
same => n,Echo()

same => n,Hangup()
[internal]
; Internal extensions
exten => 100,1,Answer()
same => n,Playback(hello-world)
same => n,Echo()
same => n,Hangup()
"""


comment = pp.Combine(pp.Char(";") + pp.rest_of_line)
context = pp.Combine(
    pp.Char("[") + pp.Word(pp.alphas + "-", pp.alphanums + "-") + pp.Char("]")
)

exten = pp.Word("exten")
arrow = pp.Word("=>")
priority = pp.Word(pp.nums) | pp.Char("n")

application_args = pp.OneOrMore(pp.Word(pp.printables))
application = pp.Word(pp.alphas) + pp.Char("(") + \
    application_args + pp.Char(")")


comment.run_tests("; my comment ")
context.run_tests(["[internal]", "[foo-bar]", "[foo1-bar]"])
application.run_tests(
    [
        "Noop(Incoming Call)",
        "Echo()",
        "Hangup( )",
    ]
)
