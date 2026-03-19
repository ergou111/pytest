import os
import argparse
from urllib.request import urlopen
from urllib.parse import urlparse, unquote

# get file name
def get_filename_from_url(url: str) -> str:
    path = urlparse(url).path
    filename = os.path.basename(path)
    filename = unquote(filename)

    return filename

# progress bar
def show_progress(downloaded: int, total: int) -> None:
    if total > 0:
        percent = downloaded / total * 100
        bar_length = 30
        filled = int(bar_length * downloaded / total)
        bar = "#" * filled + "-" * (bar_length - filled)

        print(f"\r[{bar}] {percent:.1f}% ({downloaded}/{total} bytes)", end="")
    else:
        print(f"\rDownloaded {downloaded} bytes", end="")


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

            while True:
                chunk = response.read(8192)
                if not chunk:
                    break

                f.write(chunk)
                downloaded += len(chunk)
                show_progress(downloaded, total_size)

        print()
        print(f"Downloaded: {filename}")

    except Exception as e:
        print(f"Download failed: {e}")


if __name__ == "__main__":
    main()