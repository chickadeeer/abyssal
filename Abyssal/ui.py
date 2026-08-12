from __future__ import annotations
_A='#0d9488'
from rich.align import Align
from rich.console import Console
from rich.text import Text
from rich.theme import Theme
from.config import APP_NAME,APP_VERSION
THEME=Theme({'info':_A,'warning':'yellow','error':'bold red','success':'#14b8a6','thinking':'dim italic #64748b','search':'bold #2dd4bf','user':'bold #5eead4','system':'dim italic #99f6e4','accent':_A,'mcp':'bold #14b8a6','dim':'dim'})
console=Console(theme=THEME,highlight=True)
def print_banner():A=Text('\n  ▄▄▄▄   ▄▄                            ▄▄ \n▄██▀▀██▄ ██                            ██ \n███  ███ ████▄ ██ ██ ▄█▀▀▀ ▄█▀▀▀  ▀▀█▄ ██ \n███▀▀███ ██ ██ ██▄██ ▀███▄ ▀███▄ ▄█▀██ ██ \n███  ███ ████▀  ▀██▀ ▄▄▄█▀ ▄▄▄█▀ ▀█▄██ ██ \n                 ██                       \n               ▀▀▀\n',style='bold #0d9488');console.print(Align.center(A));console.print(Align.center(Text(f"{APP_NAME} v{APP_VERSION} — chat.deepseek.com",style='dim italic #115e59')));console.print()