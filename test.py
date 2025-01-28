import yt_dlp

COOKIES_FILE_PATH = 'www.youtube.com_cookies.txt'


def list_formats(video_url):
    ydl_opts = {
        'format': 'bestaudio',
        'quiet': False,  # Disable quiet mode to see output
        'noplaylist': True,
        'cookiefile': COOKIES_FILE_PATH,
        'extractor_args': {'youtube': {'player_client': ['android']}},
        'listformats': True  # This enables --list-formats
    }

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        try:
            ydl.extract_info(video_url, download=False)  # Extract format list
        except yt_dlp.utils.DownloadError as e:
            print(f"Error: {e}")


# Replace with the actual video URL
video_url = "https://www.youtube.com/watch?v=xSTcuLXmkbU"
list_formats(video_url)
