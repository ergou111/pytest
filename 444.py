import os
import argparse
from urllib.request import urlopen
from urllib.parse import urlparse, unquote
import time

# get file name
def get_filename_from_url(url: str) -> str:
    path = urlparse(url).path
    filename = os.path.basename(path)
    filename = unquote(filename)

    return filename

# progress bar
def show_progress(downloaded: int, total: int, start_time: float) -> None:
    # calculate time
    elapsed = time.time() - start_time
    if elapsed <= 0:
        elapsed = 0.001

    # calculate download time
    speed = downloaded / elapsed

    # format kb more readable
    def format_size(size: float) -> str:
        if size >= 1024 * 1024:
            return f"{size / (1024 * 1024):.1f} MB"
        elif size >= 1024:
            return f"{size / 1024:.1f} KB"
        else:
            return f"{size:.0f} B"

    # format time as MM:SS
    def format_time(seconds: float) -> str:
        if seconds < 0:
            seconds = 0
        minutes = int(seconds // 60)
        secs = int(seconds % 60)
        return f"{minutes:02d}:{secs:02d}"

    if total > 0:
        percent = downloaded / total * 100
        bar_length = 30
        filled = int(bar_length * downloaded / total)
        bar = "#" * filled + "-" * (bar_length - filled)

        remaining = total - downloaded
        eta = remaining / speed if speed > 0 else 0

        print(
            f"\r[{bar}] {percent:5.1f}% "
            f"({format_size(downloaded)}/{format_size(total)}) "
            f"{format_size(speed)}/s ETA {format_time(eta)}",
            end=""
        )
    else:
        print(
            f"\rDownloaded {format_size(downloaded)} "
            f"at {format_size(speed)}/s",
            end=""
        )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("url", help="URL to download")
    parser.add_argument("-o", "--output", help="Output filename")

    args = parser.parse_args()

    url = args.url

    if args.output:
        filename = args.output
    else:
        filename = get_filename_from_url(url)

    # download
    try:
        with urlopen(url) as response, open(filename, "wb") as f:
            f.write(response.read())

        print(f"Downloaded: {filename}")

    except Exception as e:
        print(f"Download failed: {e}")

    # download
    try:
        with urlopen(url) as response, open(filename, "wb") as f:
            total_size = response.headers.get("Content-Length")
            total_size = int(total_size)

            downloaded = 0
            start_time = time.time()

            while True:
                chunk = response.read(8192)
                if not chunk:
                    break

                f.write(chunk)
                downloaded += len(chunk)
                show_progress(downloaded, total_size, start_time)

        print()
        print(f"Downloaded: {filename}")

    except Exception as e:
        print(f"Download failed: {e}")


if __name__ == "__main__":
    main()