"""Test extra SYR–CHS–SYR morning turn before R178's RDU service.
Keep ten-leg draft builder unchanged; this is an optional expanded scenario.
"""
from pathlib import Path
code=Path("scripts/build_schedule_7_v1_4_3_candidate.py").read_text()
needle=' # R178 connects RDU to the Hartford corridor via Syracuse'
assert needle in code
code=code.replace(needle,
 ' (178,"SYR","CHS",310,430),(178,"CHS","SYR",470,590),\n'+needle)
exec(compile(code,"scripts/build_schedule_7_v1_4_3_candidate.py","exec"),{"__name__":"__main__"})
