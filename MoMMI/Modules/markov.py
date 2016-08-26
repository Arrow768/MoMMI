from ..config import get_config
from ..commands import always_command, command
from ..client import client
from collections import defaultdict
import os
import re
import pickle
import logging
import random
import aiofiles


logger = logging.getLogger(__name__)
markov_chain = None
sentence_re = re.compile("([.,?\n]|(?<!@)!)")
parent_re = re.compile("[[\]{}()\"']")

def zero():
    return 0

def zero_dict():
    return defaultdict(zero)


class Chain(object):
    def __init__(self, filename):
        self.db = None
        self.filename = filename

    async def load(self):
        async with aiofiles.open(self.filename, "rb") as f:
            try:
                bytes = await f.read()
                self.db = pickle.loads(bytes)

            except EOFError:
                logger.exception("Unable to load markov database.")

            if not self.db:
                self.db = defaultdict(zero_dict)

    async def dump(self):
        try:
            async with aiofiles.open(self.filename, "wb") as f:
                bytes = pickle.dumps(self.db)
                await f.write(bytes)
        except:
            logger.exception("Unable to dump markov database.")

    def read(self, words):
        for sentence in self.sentences(words):
            words = sentence.split()
            if len(words) < 7:
                continue

            last = ""

            for word in words:
                word = word.strip()
                chain = self.db[last]
                chain[word] += 1
                last = word

            self.db[last][""] += 1

    def sentences(self, words):
        last = 0
        for match in sentence_re.finditer(words):
            string = words[last:match.start()].strip()
            if string:
                yield string

            last = match.end()

        if last < len(words):
            string = words[last:].strip()
            if string:
                yield string

    def generate(self, seed=""):
        message = []
        if seed != "":
            if seed not in self.db.keys():
                return "Cannot make markov chain: unknown word"

            message.append(seed.title())

        for i in range(100): # Prevent infinite loop.
            # Basic pickweight based on https://stackoverflow.com/questions/3679694/a-weighted-version-of-random-choice
            chain = self.db[seed]
            # logger.info(chain)
            total = sum(chain.values())
            picked = random.randint(0, total)

            for word in chain.keys():
                picked -= chain[word]
                if picked <= 0:
                    seed = word
                    break

            message.append(seed)

            if seed == "":
                break

        # Remove trailing "".
        message.pop()
        logger.info(message)
        return " ".join(message) + "."

@always_command(True)
async def markov_reader(message):
    markov_chain.read(parent_re.sub(" ", message.content.lower()))

@command("markov\s*(?:\((\S*)\))?")
async def markov(content, match, message):
    msg = ""
    if match.group(1):
        msg = markov_chain.generate(match.group(1))
    else:
        msg = markov_chain.generate()

    await client.send_message(message.channel, msg)

@command("wipemarkov")
async def markov_wipe(content, match, message):
    if int(get_config("owner.id", 97089048065097728)) != int(message.author.id):
        await client.send_message(message.channel, "You don't have permission, fuck off.")
        return

    markov_chain.db = defaultdict(zero_dict)
    await client.send_message(message.channel, "Wiped.")

async def load():
    logger.info("LOADING MARKOV")
    global markov_chain
    markov_chain = Chain("markovdb")
    await markov_chain.load()

async def unload():
    logger.info("UNLOADING MARKOV")
    await markov_chain.dump()

async def save():
    logger.info("Saving markov")
    await markov_chain.dump()
