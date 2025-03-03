from pytubefix import YouTube
from pytubefix.cli import on_progress

if __name__ == '__main__':
    url = "https://youtu.be/mJbhnng5fDY?si=muRoHDelfGAxFTdF"

    yt = YouTube(url, on_progress_callback=on_progress)
    print(yt.title)

    ys = yt.streams.get_highest_resolution()
    ys.download()
