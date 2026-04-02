import os
import argparse
from urllib.request import urlopen
from urllib.parse import urlparse, unquote
from urllib.error import HTTPError, URLError
import time

def get_filename_from_url(url: str) -> str:
    path = urlparse(url).path
    filename = os.path.basename(path)
    filename = unquote(filename)

    if not filename:
        return "downloaded_file"

    return filename

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

    try:
        with urlopen(url) as response:
            # check redirect
            final_url = response.geturl()
            if final_url != url:
                print(f"Redirect detected:")
                print(f"Original URL: {url}")
                print(f"Final URL: {final_url}")

            total_size = response.headers.get("Content-Length")
            if total_size is not None and total_size.isdigit():
                total_size = int(total_size)
            else:
                total_size = 0

            downloaded = 0
            start_time = time.time()

            with open(filename, "wb") as f:
                while True:
                    chunk = response.read(8192)
                    if not chunk:
                        break

                    f.write(chunk)
                    downloaded += len(chunk)
                    show_progress(downloaded, total_size, start_time)

        print()
        print(f"Downloaded: {filename}")

    except HTTPError as e:
        print(f"HTTP error {e.code}: {e.reason}")

        if e.code == 404:
            print("File not found on the server.")
        elif e.code == 403:
            print("Access denied.")
        elif e.code == 500:
            print("Internal server error.")
        else:
            print("Server returned an HTTP error.")

    except URLError as e:
        print(f"URL error: {e.reason}")
        print("Please check the URL or your internet connection.")

    except Exception as e:
        print(f"Download failed: {e}")


if __name__ == "__main__":
    main()