import re

def distill_filename(name: str) -> str:
    """
    Removes forbidden characters from a name to make it a suitable Windows file/directory name.
    Typically these include the following:
    / \\ : ? * " < > |
    :param path: name to remove forbidden characters from
    :return: name with all forbidden characters removed
    """
    forbidden_characters = re.compile(r'[/\\:?*\"<>|]')
    return forbidden_characters.sub('_', name)


def shorten_path(path: str, is_windows: bool = False) -> str:
    """
    Shorten a file path so that all intermediate folders are reduced to their first letter.
    Examples:
      "C:\\Users\\Video\\Movies\\venom.mp4" -> "C:\\U\\V\\M\\venom.mp4"
      "/home/video/Movies/venom.mp4" -> "/h/v/M/venom.mp4"
    """
    # Determine the path separator: use '\' if present, else '/'
    sep = re.compile(r'[/\\]')
    parts = sep.split(path)
    if len(parts) < 3:
        return path  # Nothing to shorten if there are less than 3 parts
    # Keep the first (drive letter or root) and the last part (file name) as-is.
    shortened = [parts[0] if is_windows else ''] + \
                [part[:1] for part in parts[1:-1]] + \
                [parts[-1]]
    return '/'.join(shortened)


def format_time(ms: int) -> str:
    """
    Format milliseconds into [HH:]MM:SS.
    If the duration is less than one hour, HH: is omitted.
    """
    total_seconds = ms // 1000
    hours = total_seconds // 3600
    minutes = (total_seconds % 3600) // 60
    seconds = total_seconds % 60
    if hours > 0:
        return f"{hours:2}:{minutes:02}:{seconds:02}"
    return f"{minutes:2}:{seconds:02}"


def truncate_start(string: str, limit: int=32, prefix: str='...') -> str:
    if len(prefix) > limit:
        raise ValueError(f"Prefix too long for the length of {limit}: {prefix}")

    if len(string) > limit:
        return prefix + string[-(limit - len(prefix)):]

    return string


if __name__ == '__main__':
    print(shorten_path('C:\\Users\\Video\\Movies\\venom.mp4', is_windows=True))
    print(shorten_path('/home/video/Movies/venom.mp4', is_windows=False))
    for i in range(32):
        print(format_time(1000 << i))
    print(limit_start('come here and taste my venom venom venom', limit=15, prefix='...'))