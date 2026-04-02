import os
import argparse
from urllib.request import urlopen, Request
from urllib.parse import urlparse, unquote
from urllib.error import HTTPError, URLError
import time
import socket
import base64
import threading


DEFAULT_BUFFER_SIZE = 128 * 1024


def get_filename_from_url(url: str) -> str:
    path = urlparse(url).path
    filename = os.path.basename(path)
    filename = unquote(filename)

    if not filename:
        return "downloaded_file"

    return filename


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


def build_progress_line(downloaded: int, total: int, start_time: float) -> str:
    elapsed = time.time() - start_time
    if elapsed <= 0:
        elapsed = 0.001

    speed = downloaded / elapsed

    if total > 0:
        percent = downloaded / total * 100
        bar_length = 30
        filled = int(bar_length * downloaded / total)
        bar = "#" * filled + "-" * (bar_length - filled)

        remaining = total - downloaded
        eta = remaining / speed if speed > 0 else 0

        return (
            f"[{bar}] {percent:5.1f}% "
            f"({format_size(downloaded)}/{format_size(total)}) "
            f"{format_size(speed)}/s ETA {format_time(eta)}"
        )
    else:
        return (
            f"Downloaded {format_size(downloaded)} "
            f"at {format_size(speed)}/s"
        )


class ProgressState:
    def __init__(self, total: int, start_time: float):
        self.downloaded = 0
        self.total = total
        self.start_time = start_time
        self.lock = threading.Lock()


def progress_worker(state: ProgressState, stop_event: threading.Event, interval: float = 0.1) -> None:
    last_len = 0

    while not stop_event.wait(interval):
        with state.lock:
            downloaded = state.downloaded
            total = state.total
            start_time = state.start_time

        line = build_progress_line(downloaded, total, start_time)
        pad = max(0, last_len - len(line))
        print("\r" + line + (" " * pad), end="", flush=True)
        last_len = len(line)

    with state.lock:
        downloaded = state.downloaded
        total = state.total
        start_time = state.start_time

    line = build_progress_line(downloaded, total, start_time)
    pad = max(0, last_len - len(line))
    print("\r" + line + (" " * pad), end="", flush=True)


def stop_progress_thread(progress_thread, stop_event) -> None:
    if stop_event is not None:
        stop_event.set()
    if progress_thread is not None:
        progress_thread.join()
        print()


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
    parser.add_argument(
        "--bufsize",
        type=int,
        default=DEFAULT_BUFFER_SIZE,
        help="Read buffer size in bytes (default: 131072)"
    )

    args = parser.parse_args()

    url = args.url
    retry_count = args.retry
    timeout = args.timeout
    user = args.user
    password = args.password
    custom_headers = args.header
    bufsize = args.bufsize

    if bufsize <= 0:
        print("Error: --bufsize must be greater than 0.")
        return

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
        progress_thread = None
        stop_event = None

        try:
            request = Request(url, headers=headers)

            print(f"Using background progress thread, buffer size = {bufsize} bytes")

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

                start_time = time.time()
                state = ProgressState(total_size, start_time)
                stop_event = threading.Event()
                progress_thread = threading.Thread(
                    target=progress_worker,
                    args=(state, stop_event),
                    daemon=True
                )
                progress_thread.start()

                with open(filename, "wb") as f:
                    while True:
                        chunk = response.read(bufsize)
                        if not chunk:
                            break

                        f.write(chunk)

                        with state.lock:
                            state.downloaded += len(chunk)

            stop_progress_thread(progress_thread, stop_event)

            elapsed = time.time() - start_time
            avg_speed = state.downloaded / elapsed if elapsed > 0 else 0

            print(f"Downloaded: {filename}")
            print(f"Time used: {elapsed:.2f}s")
            print(f"Average speed: {format_size(avg_speed)}/s")
            return

        except HTTPError as e:
            stop_progress_thread(progress_thread, stop_event)

            print(f"HTTP error {e.code}: {e.reason}")

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
            stop_progress_thread(progress_thread, stop_event)

            print(f"Network/timeout error: {e}")

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
            stop_progress_thread(progress_thread, stop_event)

            print(f"Download failed: {e}")

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