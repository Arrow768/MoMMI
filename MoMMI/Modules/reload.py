from discord import Message
from typing import re as typing_re
from MoMMI.commands import command
from MoMMI.master import master
from MoMMI.server import MChannel

@command("reload", "reload", roles=["owner"])
async def reload(channel: MChannel, match: typing_re.Match, message: Message):
    await master.reload_modules()

@command("modules", "modules", roles=["owner"])
async def modules(channel: MChannel, match: typing_re.Match, message: Message):
    msg = "```"
    for module in channel.server.master.modules.values():
        msg += f"{module.name}:\n"
        for handler in module.handlers.values():
            msg += f"* {handler.name} ({type(handler)})\n"

    msg += "```"

    await channel.send(msg)
