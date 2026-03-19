import os
import sys
from urllib.request import urlopen
from urllib.parse import urlparse, unquote

# get file name
def get_filename_from_url(url: str) -> str:
    path = urlparse(url).path
    filename = os.path.basename(path)
    filename = unquote(filename)

    return filename


def main() -> None:
    
    url = sys.argv[1]
    filename = get_filename_from_url(url)

    # download
    try:
        with urlopen(url) as response, open(filename, "wb") as f:
            f.write(response.read())

        print(f"Downloaded: {filename}")

    except Exception as e:
        print(f"Download failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()