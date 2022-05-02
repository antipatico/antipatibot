#!/usr/bin/env python3
"""antipatibot, discord server."""
import asyncio
import logging
import os
import secrets
from dataclasses import dataclass

import discord
from discord.ext import commands
import yt_dlp as youtube_dl

youtube_dl.utils.bug_reports_message = lambda: ''

ytdl_format_options = {
    'format': 'bestaudio/best',
    'outtmpl': '%(extractor)s-%(id)s-%(title)s.%(ext)s',
    'restrictfilenames': True,
    'noplaylist': False,
    'extract_flat': 'in_playlist',  # don't extract stream urls / thumbnails # ... for playlists.
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
            # Take first item from a playlist.
            # This should never happen, since we handle this in the play command,
            # but better safe than sorry.
            data = data['entries'][0]
        filename = data['url'] if stream else ytdl.prepare_filename(data)
        return cls(discord.FFmpegPCMAudio(filename, **ffmpeg_options), data=data)


@dataclass()
class GuildData:
    """Data associated to each guild: song queue, music task and lock."""

    MAX_QUEUE_SIZE = 1000
    lock: asyncio.Lock = asyncio.Lock()
    task: asyncio.Task = None
    queue: asyncio.Queue = asyncio.Queue(MAX_QUEUE_SIZE)
    loop: bool = False


# pylint: disable=R0201,R0904
class AntipatiBot(commands.Cog):
    """AntipatiBot's collection of command."""

    def __init__(self, bot, log):
        self.bot = bot
        self.log = log
        self.guild_data = {}

    async def cog_command_error(self, ctx, error):
        message = ctx.message.content
        self.log.error(f"command_error:{ctx.guild.id}:{self.log.sanitize(ctx.author)}" +
                       f":{ctx.command}:{ctx.author.id}:{message}:{error}")
        await ctx.message.reply("Invalid command.")

    async def cog_before_invoke(self, ctx):
        self.log.info(
            f"command:{ctx.guild.id}:{self.log.sanitize(ctx.author)}:{ctx.author.id}:{ctx.command}")

    @commands.Cog.listener()
    async def on_ready(self):
        """Triggers when the bot is ready to run, used to log basic information."""
        self.log.info("login:%s", self.bot.user)
        for guild in self.bot.guilds:
            self.log.info("joined_guild:%d:%s", guild.id, self.log.sanitize(guild.name))
            self.guild_data[guild.id] = GuildData()

    @commands.Cog.listener()
    async def on_voice_state_update(self, member: discord.Member, before: discord.VoiceState,
                                    after: discord.VoiceState):
        """Triggers when the bot joins or leaves a voice channel.
           Starts the music_player_loop for the given guild."""
        guild_data = self.guild_data[member.guild.id]
        async with guild_data.lock:
            if after.channel is not None and \
                    after.channel != before.channel and \
                    guild_data.task is None:
                guild_data.task = asyncio.create_task(self.music_player_loop(guild_data))
            elif after.channel is None and \
                    after.channel != before.channel and \
                    guild_data.task is not None:
                guild_data.task.cancel()
                self.guild_data[member.guild.id] = GuildData()

    async def music_player_loop(self, guild_data: GuildData):
        """Task which handles the queue list, cross-guild in theory (wip)."""
        self.log.info("music_player_loop() started")
        while True:
            try:
                (song_request, ctx) = await guild_data.queue.get()
                self.log.info("song request: " + str(song_request))
                player = await YTDLSource.from_url(song_request, loop=self.bot.loop, stream=True)
                playing_current_song = asyncio.Event()

                def on_song_end(error):
                    if error is not None:
                        self.log.error("Player error: %s", error)
                    playing_current_song.set()

                ctx.voice_client.play(player, after=on_song_end)
                await ctx.send(f"Now playing: {player.title}")
                await playing_current_song.wait()
                if guild_data.loop:
                    try:
                        guild_data.queue.put_nowait((song_request, ctx))
                    except asyncio.QueueFull:
                        pass
            except asyncio.CancelledError:
                self.log.info("music_player_loop() killed")
                return
            except Exception as exception:  # pylint: disable=W0703
                self.log.warning(f"music_player_loop() uncaught exception: {exception}")

    @commands.command()
    async def join(self, ctx, *, channel: discord.VoiceChannel = None):
        """
        Either join a given voice channel or move to the author voice channel.
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
        return await self.play(ctx, song_request="https://www.youtube.com/watch?v=DAuPe14li4g")

    @commands.command(aliases=["jhon"])
    async def john(self, ctx):
        """He truly is."""
        return await self.play(ctx, song_request="https://www.youtube.com/watch?v=dALcFSyFcXs")

    @commands.command(aliases=["p", "youtube", "yt"])
    async def play(self, ctx, *, song_request: str):
        """Add youtube song to playlist."""
        async with ctx.typing():
            guild_data = self.guild_data[ctx.guild.id]
            songs = [ytdl.extract_info(song_request, download=False)]
            if "entries" in songs[0]:
                # YouTube playlist
                songs = list(song for song in songs[0]["entries"])
            for song in songs:
                try:
                    guild_data.queue.put_nowait((song["url"], ctx))
                except asyncio.QueueFull:
                    await ctx.message.reply(
                        f"Song queue is full (Max size: {guild_data.queue.maxsize})")
                    return
            await ctx.message.reply("Song added to the queue" if len(songs) == 1
                                    else f"Added {len(yt_data)} songs to the queue.")

    @commands.command(aliases=["clear", "clean", "hairottoilcazzo"])
    async def stop(self, ctx, *, reply=True):
        """Clear the queue and stop playing music"""
        guild_data = self.guild_data[ctx.guild.id]
        try:
            while True:
                guild_data.queue.get_nowait()
        except asyncio.QueueEmpty:
            await self.skip(ctx)
            if reply:
                await ctx.message.reply("Song queue cleared and music stopped")

    @commands.command(aliases=["kill", "terminate", "harakiri"])
    async def disconnect(self, ctx):
        """Clear the queue, stop playing music and disconnect from the channel"""
        await self.stop(ctx, reply=False)
        if ctx.voice_client is not None:
            await ctx.voice_client.disconnect()

    @commands.command(aliases=["next"])
    async def skip(self, ctx):
        """Skip the song that is currently playing."""
        if ctx.voice_client is not None and ctx.voice_client.is_playing():
            ctx.voice_client.stop()

    @commands.command()
    async def loop(self, ctx):
        """Toggle the loop functionality"""
        async with ctx.typing():
            guild_data = self.guild_data[ctx.guild.id]
            guild_data.loop = not guild_data.loop
        await ctx.message.reply(f"Loop {'activated' if guild_data.loop else 'deactivated'}")

    @commands.command(aliases=["die", "roll"])
    async def dice(self, ctx, num: int = 1, sides: int = 20, show_sides: bool = True):
        """Roll an n sided dice"""
        if sides < 1 or sides > 0x1337 or num < 1 or num > 40:
            return await ctx.message.reply("You have been added to a list.")
        if num == 1:
            return await ctx.message.reply((f"[d{sides}] " if show_sides else "") +
                                           f"You rolled a {secrets.randbelow(sides) + 1}")
        rolls = [secrets.randbelow(sides) + 1 for _ in range(num)]
        return await ctx.message.reply(
            f"[{num}d{sides}] You rolled {'+'.join([str(r) for r in rolls])} = {sum(rolls)}")

    # pylint: disable=C0103
    @commands.command()
    async def d4(self, ctx, n=1):
        """Roll a 4-sided dice"""
        await self.dice(ctx, sides=4, num=n, show_sides=False)

    @commands.command()
    async def d6(self, ctx, n=1):
        """Roll a 6-sided dice"""
        await self.dice(ctx, sides=6, num=n, show_sides=False)

    @commands.command()
    async def d8(self, ctx, n=1):
        """Roll a 8-sided dice"""
        await self.dice(ctx, sides=8, num=n, show_sides=False)

    @commands.command()
    async def d10(self, ctx, n=1):
        """Roll a 10-sided dice"""
        await self.dice(ctx, sides=10, num=n, show_sides=False)

    @commands.command()
    async def d12(self, ctx, n=1):
        """Roll a 10-sided dice"""
        await self.dice(ctx, sides=12, num=n, show_sides=False)

    @commands.command()
    async def d20(self, ctx, n=1):
        """Roll a 20-sided dice"""
        await self.dice(ctx, sides=20, num=n, show_sides=False)

    @commands.command()
    async def d100(self, ctx, n=1):
        """Roll a 100-sided dice"""
        await self.dice(ctx, sides=100, num=n, show_sides=False)

    @play.before_invoke
    @cichero.before_invoke
    @john.before_invoke
    async def ensure_voice(self, ctx):
        """Pre-hook used to ensure you the bot is connected to a voice channel before starting to
        play music."""
        if ctx.voice_client is None:
            if ctx.author.voice:
                await ctx.author.voice.channel.connect()
            else:
                await ctx.send("You are not connected to a voice channel.")
                raise commands.CommandError("Author not connected to a voice channel.")


def main():
    """Entrypoint for antipatibot program"""
    logging.basicConfig(level=logging.INFO)
    logging.getLogger("discord").setLevel(logging.WARNING)
    log = logging.getLogger("antipatibot")
    #    log.setLevel(logging.DEBUG)
    bot = commands.Bot(command_prefix=commands.when_mentioned_or("!"), description="AntipatiBot")

    log.sanitize = lambda message: str(message).replace(":", "_") \
        .replace("\r", "\\r") \
        .replace("\n", "\\n") \
        .replace("\t", "\\t")

    bot.add_cog(AntipatiBot(bot, log))
    try:
        discord_api_file = "/antipatibot/discord_token.txt"
        if os.path.exists(discord_api_file) and os.path.isfile(discord_api_file):
            with open(discord_api_file, encoding='utf8') as file:
                discord_token = file.read().strip("\n\r\t ")
        else:
            discord_token = os.getenv("ANTIPATIBOT_DISCORD_TOKEN", "")
        bot.run(discord_token)
    except discord.errors.LoginFailure:
        log.error("invalid_discord_token:Please set a valid discord bot API token.")


if __name__ == "__main__":
    main()
