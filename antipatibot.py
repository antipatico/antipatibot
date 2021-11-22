#!/usr/bin/env python3
"""antipatibot, the smart discord server."""
import asyncio
import logging
import os
import secrets
import base64
import gzip

import discord
from discord.ext import commands
import youtube_dl

youtube_dl.utils.bug_reports_message = lambda: ''

ytdl_format_options = {
    'format': 'bestaudio/best',
    'outtmpl': '%(extractor)s-%(id)s-%(title)s.%(ext)s',
    'restrictfilenames': True,
    'noplaylist': True,
    'nocheckcertificate': True,
    'ignoreerrors': False,
    'logtostderr': False,
    'quiet': True,
    'no_warnings': True,
    'default_search': 'auto',
    'source_address': '0.0.0.0'  # bind to ipv4 since ipv6 addresses cause issues sometimes
}

ffmpeg_options = {
    'options': '-vn'
}

ytdl = youtube_dl.YoutubeDL(ytdl_format_options)


class YTDLSource(discord.PCMVolumeTransformer):
    """Youtube source class, which allows the bot to play youtube videos"""

    def __init__(self, source, *, data, volume=0.5):
        super().__init__(source, volume)

        self.data = data

        self.title = data.get('title')
        self.url = data.get('url')

    @classmethod
    async def from_url(cls, url, *, loop=None, stream=False):
        """Returns an audio from a youtube link."""
        loop = loop or asyncio.get_event_loop()
        data = await loop.run_in_executor(None, lambda: ytdl.extract_info(url, download=not stream))

        if 'entries' in data:
            # take first item from a playlist
            data = data['entries'][0]

        filename = data['url'] if stream else ytdl.prepare_filename(data)
        return cls(discord.FFmpegPCMAudio(filename, **ffmpeg_options), data=data)


# pylint: disable=R0201
class AntipatiBot(commands.Cog):
    """AntipatiBot's collection of command."""

    def __init__(self, bot, log):
        self.bot = bot
        self.log = log

    async def cog_command_error(self, ctx, error):
        message = ctx.message.content.encode()
        if len(message) > 50:
            message = gzip.compress(message, mtime=0)
        message = base64.b64encode(message).decode()
        error = base64.b64encode(str(error).encode()).decode()
        self.log.error(f"command_error:{ctx.guild.id}:{self.log.sanitize(ctx.author)}" +
                       f":{ctx.command}:{ctx.author.id}:{message}:{error}")
        await ctx.message.reply("Invalid command.")

    async def cog_before_invoke(self, ctx):
        self.log.info(
            f"command:{ctx.guild.id}:{self.log.sanitize(ctx.author)}:{ctx.author.id}:{ctx.command}")

    @commands.command()
    async def join(self, ctx, *, channel: discord.VoiceChannel = None):
        """
        Either join a given voice channel.
        If no channel is specified, connect to the user's current voice channel.
        """""
        if channel is None:
            if ctx.author.voice is None:
                return await ctx.message.reply("You are not connected to a voice channel.")
            channel = ctx.author.voice.channel
        if ctx.voice_client is not None:
            return await ctx.voice_client.move_to(channel)
        await channel.connect()

    @commands.command(aliases=["cicca"])
    async def cichero(self, ctx):
        """Great classic."""
        return await self.play(ctx, song_link="https://www.youtube.com/watch?v=DAuPe14li4g")

    @commands.command(aliases=["p", "youtube", "yt"])
    async def play(self, ctx, *, song_link: str):
        """Plays a youtube stream given a song link."""
        async with ctx.typing():
            player = await YTDLSource.from_url(song_link, loop=self.bot.loop, stream=True)
            ctx.voice_client.play(player,
                                  after=lambda e: print('Player error: %s' % e) if e else None)
        await ctx.message.reply(f"Now playing: {player.title}")

    @commands.command()
    async def stop(self, ctx):
        """Stop playing music and disconnect from the voice channel."""
        if ctx.voice_client is not None:
            await ctx.voice_client.disconnect()

    @commands.command(aliases=["next"])
    async def skip(self, ctx):
        """Skip the song that is currently playing."""
        if ctx.voice_client is not None and ctx.voice_client.is_playing():
            ctx.voice_client.stop()

    @commands.command(aliases=["die", "roll"])
    async def dice(self, ctx, *, sides: int = 20, show_sides: bool = True):
        """Roll an n sided dice"""
        if sides < 1 or sides > 0x1337:
            return await ctx.message.reply("You have been added to a list.")
        await ctx.message.reply((f"[d{sides}] " if show_sides else "") +
                                f"You rolled a {secrets.randbelow(sides) + 1}")

    @commands.command()
    async def d6(self, ctx):
        """Roll a 6-sided dice"""
        await self.dice(ctx, sides=6, show_sides=False)

    @commands.command()
    async def d10(self, ctx):
        """Roll a 10-sided dice"""
        await self.dice(ctx, sides=10, show_sides=False)

    @commands.command()
    async def d20(self, ctx):
        """Roll a 20-sided dice"""
        await self.dice(ctx, sides=20, show_sides=False)

    @commands.command()
    async def d100(self, ctx):
        """Roll a 100-sided dice"""
        await self.dice(ctx, sides=100, show_sides=False)

    @play.before_invoke
    @cichero.before_invoke
    async def ensure_voice(self, ctx):
        """Pre-hook used to ensure you the bot is connected to a voice channel before starting to
        play music."""
        if ctx.voice_client is None:
            if ctx.author.voice:
                await ctx.author.voice.channel.connect()
            else:
                await ctx.send("You are not connected to a voice channel.")
                raise commands.CommandError("Author not connected to a voice channel.")
        elif ctx.voice_client.is_playing():
            ctx.voice_client.stop()


def main():
    """Entrypoint for antipatibot program"""
    logging.basicConfig(level=logging.INFO)
    logging.getLogger("discord").setLevel(logging.WARNING)
    log = logging.getLogger("antipatibot")
    bot = commands.Bot(command_prefix=commands.when_mentioned_or("!"), description="AntipatiBot")

    log.sanitize = lambda message: str(message).replace(":", "_")\
                                               .replace("\r", "\\r")\
                                               .replace("\n", "\\n")\
                                               .replace("\t", "\\t")

    @bot.event
    async def on_ready():
        log.info("login:%s", bot.user)
        for guild in bot.guilds:
            log.info("joined_guild:%d:%s", guild.id, log.sanitize(guild.name))

    bot.add_cog(AntipatiBot(bot, log))
    try:
        bot.run(os.getenv("ANTIPATIBOT_DISCORD_TOKEN", ""))
    except discord.errors.LoginFailure:
        log.error("invalid_discord_token:Please set a valid discord bot API token.")


if __name__ == "__main__":
    main()
