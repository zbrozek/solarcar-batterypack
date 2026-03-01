import urllib.request
import urllib.error
import sys
import os

base_url = "https://yaqwsx.github.io/jlcparts/data/"

def download(url, filename):
    print(f"Downloading {url} to {filename}...", flush=True)
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req) as response, open(filename, 'wb') as out_file:
            data = response.read()
            out_file.write(data)
        return True
    except urllib.error.HTTPError as e:
        if e.code == 404:
            print(f"404 Not Found for {url}", flush=True)
            return False
        raise

def main():
    if not download(base_url + "cache.zip", "cache.zip"):
        print("Failed to download cache.zip")
        sys.exit(1)

    for i in range(1, 100):
        vol = f"cache.z{i:02d}"
        if not download(base_url + vol, vol):
            break

    print("All parts downloaded.")
    print("Please extract data using 7z, e.g.:")
    print("7z x cache.zip")

if __name__ == "__main__":
    main()
