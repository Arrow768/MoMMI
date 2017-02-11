import random
import re
from discord import Message
from typing import re as typing_re
from ..commands import command
#from ..server import MChannel


@command("airplane", "\u2708", flags=re.UNICODE|re.IGNORECASE, roles=["bot"])
async def plane(channel: "MChannel", match: typing_re.Match, message: Message):
    await channel.send(random.choice(channel.module_config(__name__, "responses")))

async def unload():
    from logging import info
    info("yes")
