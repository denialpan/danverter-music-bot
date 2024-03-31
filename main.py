from dotenv import load_dotenv
import discord
from discord.ext import commands
import os
import youtube_dl
import json
import asyncio
import queue

intents = discord.Intents.default()
intents.message_content = True
intents.voice_states = True

bot = commands.Bot(command_prefix="!", intents=intents)

load_dotenv()
TOKEN = os.getenv("DISCORD_TOKEN")

music_queue = queue.Queue()


@bot.event
async def on_ready():
    print(f'Logged in as {bot.user}')


async def play_next(ctx):
    if not music_queue.empty():
        await play_music(ctx, music_queue.get_nowait())
    else:
        asyncio.run_coroutine_threadsafe(
            ctx.voice_client.disconnect(), bot.loop)


async def play_music(ctx, url):

    voice_channel = ctx.author.voice.channel
    voice_client = discord.utils.get(bot.voice_clients, guild=ctx.guild)

    if voice_client is None:
        voice_client = await voice_channel.connect()

    with open('config.json', 'r') as file:
        config_data = json.load(file)

    music_volume = config_data['volume']
    music_playback_speed = config_data['playback_speed']

    FFMPEG_OPTIONS = {
        'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5',
        'options': f'-vn -filter:a "volume={music_volume}, atempo={music_playback_speed}"'
    }

    # if no music in queue
    if not ctx.voice_client.is_playing():
        try:

            ydl_opts = {'quiet': True, 'format': 'bestaudio'}
            with youtube_dl.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=False)
                audio_url = info['formats'][0]['url']
                ctx.voice_client.play(discord.FFmpegOpusAudio(
                    audio_url, **FFMPEG_OPTIONS), after=lambda e: asyncio.run_coroutine_threadsafe(play_next(ctx), bot.loop))
                await ctx.send(f'Playing: {info["title"]} <{url}>')
        except Exception as e:
            embed = discord.Embed(
                title="Issue that occured and i didn't parse any of this",
                color=discord.Color.red()
            )
            embed.add_field(name="error", value=f"{e}", inline=True)

            await ctx.send(embed=embed)
            with music_queue.mutex:
                music_queue.queue.clear()
            asyncio.run_coroutine_threadsafe(
                ctx.voice_client.disconnect(), bot.loop)

    else:
        music_queue.put(url)
        await ctx.send(f'Added to queue. Queue size of {music_queue.qsize()}')


@bot.command()
async def play(ctx, *, query: str):
    if ctx.author.voice is None or ctx.author.voice.channel is None:
        await ctx.send("You need to be in a voice channel")
        return

    voice_channel = ctx.author.voice.channel
    if ctx.voice_client is None:
        await voice_channel.connect()

    try:

        if "youtube.com" in query:
            print(query)
            await play_music(ctx, query)
        else:
            search_query = f"ytsearch:{query}"
            print(search_query)
            with youtube_dl.YoutubeDL({'format': 'bestaudio'}) as ydl:
                info = ydl.extract_info(search_query, download=False)
                constructed_url = info['entries'][0]['webpage_url']
                await play_music(ctx, constructed_url)
    except Exception as e:
        embed = discord.Embed(
            title="Issue that occured and i didn't parse any of this",
            color=discord.Color.red()
        )
        embed.add_field(name="error", value=f"{e}", inline=True)

        await ctx.send(embed=embed)
        with music_queue.mutex:
            music_queue.queue.clear()
        asyncio.run_coroutine_threadsafe(
            ctx.voice_client.disconnect(), bot.loop)


@bot.command()
async def skip(ctx):

    if ctx.author.voice is None or ctx.author.voice.channel is None:
        await ctx.send("You need to be in a voice channel")
        return

    if ctx.voice_client is not None and ctx.voice_client.is_playing():
        ctx.voice_client.stop()
        await ctx.send("Skipping...")
    else:
        await ctx.send("Nothing is playing to skip")


@bot.command()
async def stop(ctx):

    if ctx.author.voice is None or ctx.author.voice.channel is None:
        await ctx.send("You need to be in a voice channel")
        return

    with music_queue.mutex:
        music_queue.queue.clear()
    asyncio.run_coroutine_threadsafe(
        ctx.voice_client.disconnect(), bot.loop)


@bot.command()
async def speed(ctx, speed: float):

    if ctx.author.voice is None or ctx.author.voice.channel is None:
        await ctx.send("You need to be in a voice channel")
        return

    truncated_speed = round(speed, 2)

    if not 0.5 <= truncated_speed <= 5:
        embed = discord.Embed(
            description=f"Playback speed must be between 0.5 and 5",
            color=discord.Color.red()
        )
        await ctx.channel.send(embed=embed)
        return

    # load config speed
    with open('config.json', 'r') as file:
        config_data = json.load(file)

    config_data['playback_speed'] = truncated_speed

    with open('config.json', 'w') as file:
        json.dump(config_data, file, indent=4)  # indent for better readability

    embed = discord.Embed(
        description=f"Set playback speed as **{truncated_speed}**",
        color=discord.Color.green()

    )

    await ctx.channel.send(embed=embed)


@bot.command()
async def volume(ctx, volume: float):

    if ctx.author.voice is None or ctx.author.voice.channel is None:
        await ctx.send("You need to be in a voice channel")
        return

    truncated_volume = round(volume, 2)

    if not 0.1 <= truncated_volume <= 2:
        embed = discord.Embed(
            description=f"**Volume must be between 0.1 and 2**",
            color=discord.Color.red()
        )
        await ctx.channel.send(embed=embed)
        return

    # load config volume
    with open('config.json', 'r') as file:
        config_data = json.load(file)

    config_data['volume'] = truncated_volume

    with open('config.json', 'w') as file:
        json.dump(config_data, file, indent=4)  # indent for better readability

    embed = discord.Embed(
        description=f"Set volume as **{truncated_volume}**",
        color=discord.Color.green()
    )

    await ctx.channel.send(embed=embed)


@bot.command()
async def default(ctx):

    if ctx.author.voice is None or ctx.author.voice.channel is None:
        await ctx.send("You need to be in a voice channel")
        return

    # load config volume
    with open('config.json', 'r') as file:
        config_data = json.load(file)

    config_data['volume'] = 1
    config_data['playback_speed'] = 1

    with open('config.json', 'w') as file:
        json.dump(config_data, file, indent=4)  # indent for better readability

    embed = discord.Embed(
        description=f"Set volume as **1** and playback speed as **1**",
        color=discord.Color.green()
    )

    await ctx.channel.send(embed=embed)


def main() -> None:
    bot.run(token=TOKEN)


if __name__ == '__main__':
    main()
