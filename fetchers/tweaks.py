import subprocess
import tarfile
import tempfile
import urllib.request
import zipfile
import os
from configparser import ConfigParser
from pathlib import Path

from github import Github
from github.GitRelease import GitRelease

GITHUB_KEY = os.environ.get("GITHUB_KEY", None)
if not GITHUB_KEY:
    g = Github()
else:
    g = Github(GITHUB_KEY)

WTF_CONFIG = {
    "SET scriptMemory": "0",
    "SET cameraWaterCollision": "0",
    "SET NP_SpellQueueWindowMs": "150",
    "SET NP_ChannelQueueWindowMs": "750",
    "SET NP_CooldownQueueWindowMs": "150",
    "SET UncapSounds": "1",
    "SET checkAddonVersion": "0",
    "SET farclip": "777"
}


class Tweak(object):
    name: str = ""
    version: str = ""
    description: str = ""
    git_url: str = ""
    direct_url: str = ""
    dll_name: str = ""
    extractall: bool = False
    zip: bool = False
    zip_name: str = ""
    release: bool = False
    default_enabled: bool = True
    has_update: bool = False
    download_url: str = ""
    new_version: str = ""

    def __init__(self, release_data: dict):
        self.name = release_data["name"] if "name" in release_data else ""
        self.description = release_data["description"] if "description" in release_data else ""
        self.extractall = release_data["extractall"] if "extractall" in release_data else False
        self.git_url = release_data["git_url"] if "git_url" in release_data else ""
        self.direct_url = release_data["direct_url"] if "direct_url" in release_data else ""
        self.dll_name = release_data["dll_name"] if "dll_name" in release_data else ""
        self.zip = release_data["zip"] if "zip" in release_data else True
        self.zip_name = release_data["zip_name"] if "zip_name" in release_data else ""
        self.release = release_data["release"] if "release" in release_data else True
        self.default_enabled = release_data["default_enabled"] if "default_enabled" in release_data else True

    def check_update(self, config: ConfigParser) -> bool:
        path = config["turtle"]["turtle_path"]

        if config.has_option("tweaks", self.name):
            installed_version = config["tweaks"][self.name]
        else:
            installed_version = ""

        if self.direct_url:
            if self.direct_url.split("/")[-1] == installed_version and Path.exists(Path(path) / self.dll_name):
                self.has_update = False
            else:
                self.new_version = self.direct_url.split("/")[-1]
                self.has_update = True

        elif self.release:
            url = self.git_url.replace("https://github.com/", "")
            repo = g.get_repo(url)
            latest: GitRelease = repo.get_releases()[0]

            if latest.tag_name == installed_version and Path.exists(Path(path) / self.dll_name):
                self.has_update = False
            else:
                self.has_update = True
                self.new_version = latest.tag_name

            for asset in latest.assets:
                if self.zip:
                    if asset.name == self.zip_name:
                        self.download_url = asset.browser_download_url
                else:
                    if asset.name == self.dll_name:
                        self.download_url = asset.browser_download_url

        return self.has_update

    def install(self, config: ConfigParser) -> (bool, list[str]):
        messages = []
        path = config["turtle"]["turtle_path"]

        if self.direct_url:
            if not self.has_update:
                return True, [f"{self.name} is already the latest version."]
            try:
                with tempfile.NamedTemporaryFile(mode="wb", delete=False) as tmp:
                    urllib.request.urlretrieve(self.direct_url, tmp.name)
                    if self.zip:
                        with zipfile.ZipFile(tmp.name) as zip_file:
                            zip_file.extract(self.dll_name, path)
                            messages.append(f"Successfully downloaded and installed {self.name}")
                    config["tweaks"][self.name] = self.direct_url.split("/")[-1]
            except Exception as e:
                return False, [e]

        elif self.release:
            if self.has_update and self.download_url != "":
                if self.zip:
                    try:
                        with tempfile.NamedTemporaryFile(mode="wb", delete=False) as tmp:
                            urllib.request.urlretrieve(self.download_url, tmp.name)
                            with zipfile.ZipFile(tmp.name) as zip_file:
                                if self.extractall:
                                    zip_file.extractall(path)
                                else:
                                    zip_file.extract(self.dll_name, path)
                                messages.append(
                                    f"Successfully downloaded and installed {self.name} (version {self.new_version})"
                                )
                            config["tweaks"][self.name] = self.new_version
                    except Exception as e:
                        return False, f"Failed to download {self.name} (version {self.new_version}): {e}"
                else:
                    try:
                        urllib.request.urlretrieve(self.download_url, Path(path) / self.dll_name)
                        config["tweaks"][self.name] = self.new_version
                    except Exception as e:
                        return False, f"Failed to download {self.name} (version {self.new_version}): {e}"
                    messages.append(
                        f"Successfully downloaded and installed {self.name} (version {self.new_version})"
                    )

        return True, messages


def apply_vanilla_tweaks(path: str, url: str, settings: dict = {"windows": True, "replace": False, "farclip": 777}) -> (bool, list[str]):
    is_zip = url.endswith(".zip")
    with tempfile.NamedTemporaryFile(mode="wb", suffix=".zip", delete=False) as tmp:
        urllib.request.urlretrieve(url, tmp.name)
        if is_zip:
            with zipfile.ZipFile(tmp.name) as zip:
                if settings["windows"]:
                    zip.extract("vanilla-tweaks.exe", path)
                else:
                    zip.extract("vanilla-tweaks", path)
        else:
            with tarfile.open(tmp.name) as tar:
                if settings["windows"]:
                    tar.extract("vanilla-tweaks.exe", path)
                else:
                    tar.extract("vanilla-tweaks", path)

    args = []
    if settings["windows"]:
        args.append(".\\vanilla-tweaks.exe")
        path = path.replace("/", "\\")
    else:
        args.append("./vanilla-tweaks")

    args.append("--farclip")
    args.append(str(settings["farclip"]))

    if settings["replace"]:
        args.append("-o")
        args.append("WoW.exe")

    args.append("WoW.exe")
    print(args)
    print(path)
    try:
        result = subprocess.Popen(args, cwd=path, shell=settings["windows"], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    except Exception as e:
        return False, [f"Failed to run vanilla tweaks: {e}"]

    output = result.communicate()
    return True, [m.strip() for m in output[0].decode("ascii").split("\n")]


def update_dll_txt(path: str, tweaks: list[Tweak]):
    dll_path = Path(path) / "dlls.txt"
    try:
        with open(dll_path, "w") as dlltxt:
            dlltxt.write("twdiscord.dll\n")
            for tweak in tweaks:
                dlltxt.write(tweak.dll_name + "\n")
    except PermissionError:
        return False, "Permission error when trying to write dlls.txt"
    return True, "Success"


def load_tweaks_from_json(json_data: dict) -> list[Tweak]:
    tweaks = []
    if "tweaks" in json_data:
        for tweak in json_data["tweaks"]:
            tweaks.append(Tweak(tweak))

    return tweaks


def set_wtf_config(path: str) -> (bool, list[str]):
    existing = []
    p = Path(path) / "WTF" / "Config.wtf"
    try:
        with open(p, "r") as cfg:
            existing = [l.rstrip() for l in cfg.readlines()]
    except FileNotFoundError:
        return False, ["Could not find Config.wtf in TurtleWoW directory, aborting."]
    except PermissionError:
        return False, ["Permission error when reading from Config.wtf"]

    for k, v in WTF_CONFIG.items():
        for i, l in enumerate(existing):
            if l.startswith(k):
                existing[i] = f"{k} \"{v}\""
                break
        else:
            existing.append(f"{k} \"{v}\"")

    try:
        with open(p, "w") as cfg:
            for l in existing:
                cfg.write(l + "\n")
    except PermissionError:
        return False, "Permission error when trying to write to Config.wtf"

    return True, "Wrote some settings to Config.wtf"
