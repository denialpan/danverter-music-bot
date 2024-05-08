from dotenv import load_dotenv
import discord
from discord.ext import commands
import os
import youtube_dl
import json
import asyncio
import queue
import datetime

intents = discord.Intents.default()
intents.message_content = True
intents.voice_states = True

bot = commands.Bot(command_prefix="!", intents=intents, case_insensitive=True)

load_dotenv()
TOKEN = os.getenv("DISCORD_TOKEN")

music_queue = queue.Queue()

pending = False


@bot.event
async def on_ready():
    print(f'Logged in as {bot.user}')
    # riff raff main
    channel = bot.get_channel(1198864658308812842)
    await channel.send("Bot has restarted")


@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.CommandNotFound):
        embed = discord.Embed(
            title="you're jacob's elo graph",
            description=f"!play \n !skip \n !stop \n !q \n !speed \n !volume \n !default",
            color=discord.Color(0x000000)
        )

        await ctx.send(embed=embed)


async def play_next(ctx):
    if not music_queue.empty():
        song = music_queue.get_nowait()
        await play_music(ctx, list(song.keys())[0])
    elif not pending:
        asyncio.run_coroutine_threadsafe(
            ctx.voice_client.disconnect(), bot.loop)
        # reset to default settings upon leave
        with open('config.json', 'r') as file:
            config_data = json.load(file)

        config_data['volume'] = 1
        config_data['playback_speed'] = 1

        with open('config.json', 'w') as file:
            json.dump(config_data, file, indent=4)


async def play_music(ctx, url):

    global pending
    pending = True

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

    try:

        ydl_opts = {'quiet': True, 'format': 'bestaudio'}
        with youtube_dl.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            audio_url = info['formats'][0]['url']

            if not ctx.voice_client.is_playing():

                ctx.voice_client.play(discord.FFmpegOpusAudio(
                    audio_url, **FFMPEG_OPTIONS), after=lambda e: asyncio.run_coroutine_threadsafe(play_next(ctx), bot.loop))
                await ctx.send(f'Playing: {info["title"]} [{str(datetime.timedelta(seconds=info["duration"]))}] <{url}>')
            else:
                key = f"{url}"
                value = f"{info["title"]}"
                pair = {key: value}
                print(pair)
                music_queue.put(pair)
                await ctx.send(f'Added {info["title"]} <{url}> to queue. Queue size of {music_queue.qsize()}')

    except Exception as e:
        embed = discord.Embed(
            title="Issue that occurred and i didn't parse any of this",
            color=discord.Color.red()
        )
        embed.add_field(name="", value=f"{e}", inline=True)

        await ctx.send(embed=embed)
        with music_queue.mutex:
            music_queue.queue.clear()
        asyncio.run_coroutine_threadsafe(
            ctx.voice_client.disconnect(), bot.loop)

    pending = False


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
            title="Issue that occurred and i didn't parse any of this",
            color=discord.Color.red()
        )
        embed.add_field(name="", value=f"{e}", inline=True)

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
    # reset to default settings upon leave
    with open('config.json', 'r') as file:
        config_data = json.load(file)

    config_data['volume'] = 1
    config_data['playback_speed'] = 1

    with open('config.json', 'w') as file:
        json.dump(config_data, file, indent=4)


@bot.command()
async def q(ctx):

    if ctx.author.voice is None or ctx.author.voice.channel is None:
        await ctx.send("You need to be in a voice channel")
        return

    constructed_queue_list = ""

    if music_queue.empty():
        constructed_queue_list = "Queue is empty"
    else:
        count = 0

        for song in music_queue.queue:
            constructed_queue_list += f"{count}. {
                song[list(song.keys())[0]]} \n"
            count += 1

        embed = discord.Embed(
            title="Queue",
            description=constructed_queue_list,
            color=discord.Color(0x000000)
        )

    embed = discord.Embed(
        title="Queue",
        description=constructed_queue_list,
        color=discord.Color(0x000000)
    )

    await ctx.send(embed=embed)


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
