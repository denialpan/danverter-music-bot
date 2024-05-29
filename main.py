from dotenv import load_dotenv
import discord
from discord.ext import commands
import os
import youtube_dl
import json
import asyncio
import queue
import datetime


class Video:
    def __init__(self, title: str, duration: str, yt_share_link: str):
        self.title = title
        self.duration = duration
        self.yt_share_link = yt_share_link

    def __str__(self):
        return f"DEBUG INFORMATION {self.title} {str(datetime.timedelta(seconds=self.duration))} <{self.yt_share_link}>"


intents = discord.Intents.default()
intents.message_content = True
intents.voice_states = True

bot = commands.Bot(command_prefix="!", intents=intents, case_insensitive=True)

load_dotenv()
TOKEN = os.getenv("DISCORD_TOKEN")

music_queue = queue.Queue()
processing_video = False


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
            description=f"!play\n!skip\n!stop\n!q\n!speed\n!volume\n!default",
            color=discord.Color(0x000000)
        )

        await ctx.send(embed=embed)

# get song from queue


async def play_next(ctx):

    global processing_video

    if not music_queue.empty():
        video = music_queue.get_nowait()
        await play_music(ctx, video.yt_share_link)
    else:
        asyncio.run_coroutine_threadsafe(
            ctx.voice_client.disconnect(), bot.loop)
        # reset to default settings upon leave
        with open('config.json', 'r') as file:
            config_data = json.load(file)

        config_data['volume'] = 1
        config_data['playback_speed'] = 1

        with open('config.json', 'w') as file:
            json.dump(config_data, file, indent=4)

    processing_video = False


async def play_music(ctx, url: str):

    global processing_video

    with open('config.json', 'r') as file:
        config_data = json.load(file)

    music_volume = config_data['volume']
    music_playback_speed = config_data['playback_speed']

    FFMPEG_OPTIONS = {
        'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5',
        'options': f'-vn -filter:a "volume={music_volume}, atempo={music_playback_speed}"'
    }

    try:

        ydl_opts = {
            'format': 'bestaudio',  # Choose your desired format
            'noplaylist': True,
            'quiet': True  # Suppress output
        }

        info = None

        with youtube_dl.YoutubeDL(ydl_opts) as ydl:
            try:
                info = ydl.extract_info(url, download=False)
            except youtube_dl.utils.ExtractorError:
                await ctx.send("Invalid YouTube link.")
                return

        if not ctx.voice_client.is_playing():
            await ctx.send(f'Playing: {info["title"]} [{str(datetime.timedelta(seconds=info["duration"]))}] <{url}>')
            ctx.voice_client.play(discord.FFmpegPCMAudio(
                info['url'], **FFMPEG_OPTIONS), after=lambda e: asyncio.run_coroutine_threadsafe(play_next(ctx), bot.loop))
            processing_video = False

    except Exception as e:
        await throw_error(ctx, e)


@bot.command()
async def play(ctx, *, query: str):

    global processing_video

    if ctx.author.voice is None or ctx.author.voice.channel is None:
        await ctx.send("You need to be in a voice channel")
        return

    voice_channel = ctx.author.voice.channel
    if ctx.voice_client is None:
        await voice_channel.connect()

    try:

        ydl_link_settings = {
            'format': 'bestaudio',  # Choose your desired format
            'noplaylist': True,
            'quiet': True,  # Suppress output
        }

        ydl_search_settings = {
            'default_search': 'ytsearch',
            'max_downloads': 1,
            'quiet': True,
            'noplaylist': True,
            'extract-flat': True
        }

        shareable_url = ""
        retrieved_video_info = None

        if "&list" in query:  # is playlist link
            shareable_url = f"{query[:query.find("&list")]}"

        elif "youtu.be" in query:  # weird shortened youtube link
            shareable_url = f"https://www.youtube.com/watch?v={
                query.split('/')[-1]}"

        elif "youtube.com" in query:  # exact normal youtube link
            shareable_url = query

        else:  # search query

            with youtube_dl.YoutubeDL(ydl_search_settings) as ydl:
                try:
                    retrieved_video_info = ydl.extract_info(
                        query, download=False)
                except:
                    await ctx.send("Invalid YouTube link.")
                    return

                shareable_url = retrieved_video_info['entries'][0]['webpage_url']

        # not playing and nothing is in queue
        if not ctx.voice_client.is_playing() and music_queue.empty() and not processing_video:
            processing_video = True
            await play_music(ctx, shareable_url)

        # add to queue no matter what
        else:
            with youtube_dl.YoutubeDL(ydl_link_settings) as ydl:
                info_dict = ydl.extract_info(shareable_url, download=False)
                title = info_dict.get('title', None)
                duration = info_dict.get(
                    'duration', None)  # Duration in seconds
                shareable_url = info_dict.get('webpage_url', None)

            video_info = Video(title, duration, shareable_url)
            music_queue.put(video_info)
            await ctx.send(f"Added: {video_info.title} <{video_info.yt_share_link}> to queue. Queue size of {music_queue.qsize()}")

    except Exception as e:
        await throw_error(ctx, e)


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

    global processing_video

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

    processing_video = False


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

        for video in music_queue.queue:
            constructed_queue_list += f"{count}. {video.title} \n"
            count += 1

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


async def throw_error(ctx, e: Exception):
    embed = discord.Embed(
        title="Issue that occurred and this time i did parse it",
        color=discord.Color.red()
    )
    embed.add_field(name="", value=f"{e}", inline=True)

    await ctx.send(embed=embed)
    with music_queue.mutex:
        music_queue.queue.clear()
    asyncio.run_coroutine_threadsafe(
        ctx.voice_client.disconnect(), bot.loop)


def main() -> None:
    bot.run(token=TOKEN)


if __name__ == '__main__':
    main()
