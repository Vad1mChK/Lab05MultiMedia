from mutagen.mp4 import MP4, MP4Tags
from datetime import datetime
from mutagen.easyid3 import EasyID3
from mutagen.id3 import ID3, TIT2, TPE1, ID3NoHeaderError


def tag_mp4_file(file: str, *, title: str = None, author: str = None, date: datetime = None):
    video = MP4(file)
    if title:
        video.tags['\xa9nam'] = title
    if author:
        video.tags['\xa9ART'] = author
    if date:
        video.tags['\xa9day'] = [date.strftime("%Y-%m-%d")]
    video.save()

def tag_mp3_file(path: str, *, title: str | None = None, author: str | None = None, do_comment: bool = True) -> None:
    audio = EasyID3(path)

    print(f"Before:\n{audio.pprint()}")

    if "comment" not in EasyID3.valid_keys:
        EasyID3.RegisterTextKey("comment", "COMM")

    if title is not None:
        audio["title"] = [title]        # or [title]
    if author is not None:
        audio["artist"] = [author]
    if do_comment:
        audio["comment"] = ["Downloaded with DMA Video Downloader"]

    print(f"After:\n{audio.pprint()}")

    audio.save(v2_version=3)                        # writes tags back to file

if __name__ == '__main__':
    file = "D:/Videos/Title - Sonic Pocket Adventure [OST].mp4"
    # tag_mp3_file(file, title="Forever Halloween", author="The Megas")
    tag_mp4_file(file, title="skebob", author="redacted")
