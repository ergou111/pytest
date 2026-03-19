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


if __name__ == "__main__":
    main()