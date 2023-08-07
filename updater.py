import http.client
import json
from urllib.parse import urlparse
import subprocess as sp
from bs4 import BeautifulSoup
from argparse import ArgumentParser
import os
import os.path as osp
import shutil
import zipfile


URL = "https://googlechromelabs.github.io/chrome-for-testing/known-good-versions-with-downloads.json"
BUILD = "mac-arm64"


def get_download_information():
    url = urlparse(URL)
    conn = http.client.HTTPSConnection(url.netloc)
    conn.request("GET", url.path)
    response = conn.getresponse()
    data = response.read()
    parsed = json.loads(data)
    return parsed


def get_stable_version():
    url = "https://googlechromelabs.github.io/chrome-for-testing/"
    parsed = urlparse(url)
    conn = http.client.HTTPSConnection(parsed.netloc)
    conn.request("GET", parsed.path)
    response = conn.getresponse()
    data = response.read().decode("utf-8")

    soup = BeautifulSoup(data, "html.parser")
    selector = "#stable > p > code"
    tag = soup.select_one(selector)
    return tag.text


def download_file(url):
    parsed = urlparse(url)
    conn = http.client.HTTPSConnection(parsed.netloc)
    conn.request("GET", parsed.path)
    response = conn.getresponse()
    data = response.read()
    return data


def recursive_dir_rename(dirpath, rule):
    files = [osp.join(dirpath, f) for f in os.listdir(dirpath)]
    for file in files:
        if not osp.isdir(file):
            continue
        dirname = osp.basename(file)
        if dirname in rule:
            new_dirname = rule[dirname]
            new_path = osp.join(dirpath, new_dirname)
            os.rename(file, new_path)
            print(f"Renamed {file} to {new_path}")
            file = new_path
        recursive_dir_rename(file)


if __name__ == "__main__":
    allowed_builds = ["linux64", "mac-arm64", "mac-x64", "win32", "win64"]
    parser = ArgumentParser()
    parser.add_argument("--build", default="mac-arm64", choices=allowed_builds)
    args = parser.parse_args()
    build = args.build

    # remove old files
    print("Removing old files...")
    if not osp.exists("chrome"):
        os.mkdir("chrome")
    if osp.exists("chrome/chrome.zip"):
        os.remove("chrome/chrome.zip")
    if osp.exists("chrome/chromedriver.zip"):
        os.remove("chrome/chromedriver.zip")
    if osp.exists(f"chrome/chrome-{build}"):
        shutil.rmtree(f"chrome/chrome-{build}")
    if osp.exists(f"chrome/chromedriver-{build}"):
        shutil.rmtree(f"chrome/chromedriver-{build}")
    # remove symlinks
    if osp.exists("google-chrome", follow_symlinks=False):
        os.remove("google-chrome")
    if osp.exists("chromedriver", follow_symlinks=False):
        os.remove("chromedriver")

    print("Downloading files...")
    stable = get_stable_version()
    print(f"Stable version: {stable}")
    payload = get_download_information()
    version_options = payload["versions"]

    for version_entry in version_options:
        version = version_entry["version"]
        if version == stable:
            downloads = version_entry["downloads"]
            chrome_url = downloads["chrome"]
            driver_url = downloads["chromedriver"]

            for option in chrome_url:
                platform = option["platform"]
                if platform == build:
                    url = option["url"]
                    print("Downloading chrome...")
                    data = download_file(url)
                    with open("chrome/chrome.zip", "wb") as f:
                        f.write(data)

            for option in driver_url:
                platform = option["platform"]
                if platform == build:
                    url = option["url"]
                    print("Downloading chromedriver...")
                    data = download_file(url)
                    with open("chrome/chromedriver.zip", "wb") as f:
                        f.write(data)

    # unzip files
    print("Unzipping files...")
    zip_src = "chrome/chrome.zip"
    zip_dest = f"chrome/chrome-{build}"
    zipfile.ZipFile(zip_src).extractall(zip_dest)
    zip_src = "chrome/chromedriver.zip"
    zip_dest = f"chrome/chromedriver-{build}"
    zipfile.ZipFile(zip_src).extractall(zip_dest)

    # remove zip files
    print("Removing zip files...")
    os.remove("chrome/chrome.zip")
    os.remove("chrome/chromedriver.zip")

    # make symlink
    print("Making symlinks...")
    if "mac" in build:
        src = f"chrome/chrome-{build}/Google Chrome for Testing.app/Contents/MacOS/Google Chrome for Testing"
    elif "linux" in build:
        src = f"chrome/chrome-{build}/chrome-{build}/chrome"
    else:
        NotImplementedError(f"build {build} not supported")
    abssrc = osp.abspath(src)
    dest = "google-chrome"
    os.symlink(abssrc, dest)
    src = f"chrome/chromedriver-{build}/chromedriver"
    absdest = osp.abspath(src)
    dest = "chromedriver"
    os.symlink(abssrc, dest)

    print("Done!")
