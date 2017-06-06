import aiohttp
import asyncio
import json
import logging
import re
import os
import subprocess
from typing import re as typing_re
from colorhash import ColorHash
from discord import Colour, Embed, Message
from urllib.parse import quote
from MoMMI.commloop import comm_event
from MoMMI.commands import always_command
from MoMMI.server import MServer, MChannel
from MoMMI.master import master

logger = logging.getLogger(__name__)

# Taken from https://github.com/d3athrow/vgstation13/blob/Bleeding-Edge/bot/plugins/GitHub.py
REG_PATH = re.compile(r"\[([a-zA-Z\-_/][a-zA-Z0-9\- _/]*\.[a-zA-Z]+)(#L\d+(?:-L\d+)?)?\]", re.I)
REG_ISSUE = re.compile(r"\[#?([0-9]+)\]")
REG_BRACKETS = re.compile(r"\[(.+?)\]")

COLOR_GITHUB_RED = Colour(0xFF4444)
COLOR_GITHUB_GREEN = Colour(0x6CC644)
COLOR_GITHUB_PURPLE = Colour(0x6E5494)
MAX_BODY_LENGTH = 200
MD_COMMENT_RE = re.compile(r"<!--.*-->", flags=re.DOTALL)

REQUEST_HEADERS = {"Authorization": f"token {master.config.modules['github']['token']}"} 

# handling of stuff like [2000] and [world.dm]
def github_url(sub: str) -> str:
    return "https://api.github.com" + sub


def colour_extension(filename: str) -> Colour:
    ext = filename.split(".")[-1]
    c = ColorHash(ext)
    return Colour(int(c.hex[1:], 16))


@comm_event("github_event")
async def github_event(channel, message, meta):
    event = message['event']
    logger.debug(f"Handling GitHub event '$YELLOW{event}$RESET' to '$YELLOW{meta}$RESET'")

    # Find a function by the name of `on_github_{event}` in globals and call it.
    func = globals().get(f"on_github_{event}")
    if func is None:
        logger.debug("No handler for this event, ignoring.")
        return

    await func(channel, message["data"], meta)


async def on_github_issues(channel, message, repo):
    logger.debug("yes")


# Indent 2: the indent
@always_command("github_issue")
async def issue(channel: MChannel, match: typing_re.Match, message: Message):
    if "github" not in channel.server.config["modules"]:
        return

    repo = channel.server.config["modules"]["github"]["repo"]
    branchname = channel.server.config["modules"]["github"]["branch"]

    async with aiohttp.ClientSession() as session:
        for match in REG_ISSUE.finditer(message.content):
            id = int(match.group(1))
            if id < 10:
                continue

            url = github_url(f"/repos/{repo}/issues/{id}")
            async with session.get(url, headers=REQUEST_HEADERS) as resp:
                content = json.loads(await resp.text())

            # God forgive me.
            embed = Embed()
            emoji = ""
            if content.get("pull_request") is not None:
                if content["state"] == "open":
                    emoji = "<:PRopened:245910125041287168>"
                    embed.colour = COLOR_GITHUB_GREEN
                else:
                    url = github_url(f"/repos/{repo}/pulls/{id}")
                    async with session.get(url, headers=REQUEST_HEADERS) as resp:
                        prcontent = json.loads(await resp.text())
                        if prcontent["merged"]:
                            emoji = "<:PRmerged:245910124781240321>"
                            embed.colour = COLOR_GITHUB_PURPLE
                        else:
                            emoji = "<:PRclosed:246037149839917056>"
                            embed.colour = COLOR_GITHUB_RED

            else:
                if content["state"] == "open":
                    emoji = "<:ISSopened:246037149873340416>"
                    embed.colour = COLOR_GITHUB_GREEN
                else:
                    emoji = "<:ISSclosed:246037286322569216>"
                    embed.colour = COLOR_GITHUB_RED

            embed.title = emoji + content["title"]
            embed.url = content["html_url"]
            embed.set_footer(text=f"{repo}#{content['number']} by {content['user']['login']}", icon_url=content["user"]["avatar_url"])
            if len(content["body"]) > MAX_BODY_LENGTH:
                embed.description = content["body"][:MAX_BODY_LENGTH] + "..."
            else:
                embed.description = content["body"]
            embed.description += "\n\u200B"

            await channel.send(embed=embed)

        if REG_PATH.search(message.content):
            url = github_url(f"/repos/{repo}/branches/{branchname}")
            async with session.get(url, headers=REQUEST_HEADERS) as resp:
                branch = json.loads(await resp.text())

            url = github_url(f"/repos/{repo}/git/trees/{branch['commit']['sha']}")
            async with session.get(url, headers=REQUEST_HEADERS, params={"recursive": 1}) as resp:
                tree = json.loads(await resp.text())

            paths = []  # type: List[str]
            for match in REG_PATH.finditer(message.content):
                path = match.group(1).lower()
                logger.info(path)
                paths.append(path)

            for hash in tree["tree"]:
                # logger.debug(hash["path"])

                for path in paths:
                    if hash["path"].lower().endswith(path):
                        thepath = hash["path"]  # type: str
                        html_url = f"https://github.com/{repo}"
                        logger.info(html_url)
                        logger.info(branchname)
                        logger.info(quote(thepath))
                        logger.info(match.group(2))
                        file_url_part = quote(thepath) + (match.group(2) or '')
                        url = f"{html_url}/blob/{branchname}/{file_url_part}"

                        embed = Embed()
                        embed.colour = colour_extension(thepath)
                        embed.set_footer(text=f"{repo}")
                        embed.url = url
                        embed.title = thepath.split("/")[-1]
                        embed.description = f"`{thepath}`"

                        await channel.send(embed=embed)
                        paths.remove(path)
