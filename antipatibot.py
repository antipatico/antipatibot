"""antipatibot, the smart discord server."""
import logging
import os
import discord
from discord.ext import commands


class AntipatiBot(commands.Cog):
    """AntipatiBot's collection of command."""
    def __init__(self, bot):
        self.bot = bot

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
        return await ctx.message.reply(
    "ECCOLO: https://www.youtube.com/watch?v=DAuPe14li4g&list=PLeVDvlKJhCxFR8RzHmcCntoEptM1Tqwkx")

    @commands.command()
    async def play(self, ctx, *, song: str):
        """Plays a youtube stream given a song link."""
        return await ctx.message.reply(f"{song}")

    @commands.command()
    async def stop(self, ctx):
        """Stop playing music and disconnect from the voice channel."""
        if ctx.voice_client is not None:
            await ctx.voice_client.disconnect()

    @play.before_invoke
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
    logging.basicConfig(level=logging.CRITICAL)
    bot = commands.Bot(command_prefix=commands.when_mentioned_or("!"), description="AntipatiBot")

    @bot.event
    async def on_ready():
        print(f"Logged on as {bot.user}!")

    bot.add_cog(AntipatiBot(bot))
    bot.run(os.getenv("ANTIPATIBOT_DISCORD_TOKEN", ""))


if __name__ == "__main__":
    main()
