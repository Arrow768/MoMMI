from ..client import client
from ..commands import command, command_help
from ..util import output
import logging
import random
import discord

logger = logging.getLogger(__name__)
random.seed()

@command_help("roll", "roll a random number between 2 arguments.", "roll <number 1> <number2>")
@command("roll\s*(-?\d+)\s*(-?\d+)")
async def roll(content, match, message):
    msg = str(random.randint(int(match.group(1)), int(match.group(2))))
    await client.send_message(message.channel, msg)

@command_help("pick", "Picks a random item from a provided list of choices.", "pick(<choice>, <choice>[, choice...])")
@command("(?:pick|choose)\s*\((.*?)\)")
async def pick(content, match, message):
    choices = [x.strip() for x in match.group(1).split(",")]
    if len(choices) < 2:
        await client.send_message(message.channel, "You need to provide at least 2 options.")
        return

    if len(set(choices)) != len(choices):
        await client.send_message(message.channel, "If you think you're funny by spamming duplicates, you're not.")
        return


    chosen = random.choice(choices)

    await output(message.channel, "**%s**" % (chosen))

@command_help("dice", "Rolls a specific number of dice", "dice 2d20+5")
@command(r"dice\s*(\d+)?(?:d(\d+))?([\+\-]\d+)?")
async def dice_command(content, match, message):
    amount = min(1000, int(match.group(1) or "1"))
    size   = int(match.group(2) or "6")
    offset = int(match.group(3) or "0")

    rolls = [random.randint(1, size) for x in range(amount)]

    sign = "+" if offset >= 0 else ""
    added = sign + str(offset)
    content = "You rolled `%sd%s%s` and got `(%s)%s=%s`!" % (amount, size, added, "+".join([str(x) for x in rolls]),
        added, sum(rolls) + offset)

    try:
        await client.send_message(message.channel, content)
    except discord.errors.HTTPException:
        await client.send_message(message.channel, "You hit the message limit, good job.")
