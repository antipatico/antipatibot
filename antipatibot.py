#!/usr/bin/env python3
"""antipatibot, the smart discord server."""
import asyncio
import logging
import os
import secrets

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
    def __init__(self, bot):
        self.bot = bot

    async def cog_command_error(self, ctx, error):
        await ctx.message.reply("Invalid command.")

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

    @commands.command()
    async def cichero(self, ctx):
        """Great classic."""
        return await self.play(ctx, song_link="https://www.youtube.com/watch?v=DAuPe14li4g")

    @commands.command()
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

    @commands.command()
    async def skip(self, ctx):
        if ctx.voice_client is not None and ctx.voice_client.is_playing():
            await ctx.voice_client.stop()

    @commands.command()
    async def dice(self, ctx, *, sides: int = 20):
        if sides < 1 or sides > 0x1337:
            return await ctx.message.reply(f"You have been added to a list.")
        await ctx.message.reply(f"[d{sides}] You rolled a {secrets.randbelow(sides)+1}")

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

    @bot.event
    async def on_ready():
        log.info(f"Logged on as {bot.user}")
        for guild in bot.guilds:
            log.info(f"Joined guild: {guild.name}")

    bot.add_cog(AntipatiBot(bot))
    bot.run(os.getenv("ANTIPATIBOT_DISCORD_TOKEN", ""))


if __name__ == "__main__":
    main()
