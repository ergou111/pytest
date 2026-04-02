import os
import argparse
from urllib.request import urlopen, Request
from urllib.parse import urlparse, unquote
from urllib.error import HTTPError, URLError
import time
import socket
import base64

def get_filename_from_url(url: str) -> str:
    path = urlparse(url).path
    filename = os.path.basename(path)
    filename = unquote(filename)

    if not filename:
        return "downloaded_file"

    return filename

def show_progress(downloaded: int, total: int, start_time: float) -> None:
    elapsed = time.time() - start_time
    if elapsed <= 0:
        elapsed = 0.001

    speed = downloaded / elapsed

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
    parser.add_argument("--retry", type=int, default=0, help="Retry count after failure")
    parser.add_argument("--timeout", type=float, default=10, help="Timeout in seconds")
    parser.add_argument("--user", help="Username for basic authentication")
    parser.add_argument("--password", help="Password for basic authentication")
    parser.add_argument(
        "--header",
        action="append",
        default=[],
        help='Custom header, example: --header "Key: Value"'
    )

    args = parser.parse_args()

    url = args.url
    retry_count = args.retry
    timeout = args.timeout
    user = args.user
    password = args.password
    custom_headers = args.header

    if args.output:
        filename = args.output
    else:
        filename = get_filename_from_url(url)

    if (user and not password) or (password and not user):
        print("Error: --user and --password must be used together.")
        return

    headers = {}

    for item in custom_headers:
        if ":" not in item:
            print(f'Invalid header format: {item}')
            print('Use: --header "Key: Value"')
            return

        key, value = item.split(":", 1)
        headers[key.strip()] = value.strip()

    if user and password:
        auth_text = f"{user}:{password}"
        auth_bytes = auth_text.encode("utf-8")
        auth_base64 = base64.b64encode(auth_bytes).decode("utf-8")
        headers["Authorization"] = f"Basic {auth_base64}"

    max_attempts = retry_count + 1

    for attempt in range(1, max_attempts + 1):
        try:
            request = Request(url, headers=headers)

            with urlopen(request, timeout=timeout) as response:
                final_url = response.geturl()
                if final_url != url:
                    print("Redirect detected:")
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
            return

        except HTTPError as e:
            print(f"\nHTTP error {e.code}: {e.reason}")

            if e.code == 401:
                print("Authentication failed.")
            elif e.code == 404:
                print("File not found on the server.")
            elif e.code == 403:
                print("Access denied.")
            elif e.code == 500:
                print("Internal server error.")
            else:
                print("Server returned an HTTP error.")

            if 500 <= e.code < 600 and attempt < max_attempts:
                print(f"Retrying... ({attempt}/{retry_count})")
                time.sleep(1)
                continue
            else:
                break

        except (URLError, socket.timeout, TimeoutError) as e:
            print(f"\nNetwork/timeout error: {e}")

            if os.path.exists(filename):
                try:
                    os.remove(filename)
                except OSError:
                    pass

            if attempt < max_attempts:
                print(f"Retrying... ({attempt}/{retry_count})")
                time.sleep(1)
                continue
            else:
                print("No more retries left.")
                break

        except Exception as e:
            print(f"\nDownload failed: {e}")

            if os.path.exists(filename):
                try:
                    os.remove(filename)
                except OSError:
                    pass

            if attempt < max_attempts:
                print(f"Retrying... ({attempt}/{retry_count})")
                time.sleep(1)
                continue
            else:
                print("No more retries left.")
                break


if __name__ == "__main__":
    main()