import tempfile
import urllib.request
import zipfile
from configparser import ConfigParser
from pathlib import Path


class Mod(object):
    name: str = ""
    version: str = ""
    description: str = ""
    git_url: str = ""
    direct_url: str = ""
    mpq_name: str = ""
    zip: bool = False
    zip_name: str = ""
    release: bool = False
    default_enabled: bool = True
    has_update: bool = False

    def __init__(self, release_data: dict):
        self.name = release_data["name"] if "name" in release_data else ""
        self.description = release_data["description"] if "description" in release_data else ""
        self.dest_path = release_data["dest_path"] if "dest_path" in release_data else ""
        self.git_url = release_data["git_url"] if "git_url" in release_data else ""
        self.direct_url = release_data["direct_url"] if "direct_url" in release_data else ""
        self.mpq_name = release_data["mpq_name"] if "mpq_name" in release_data else ""
        self.zip = release_data["zip"] if "zip" in release_data else True
        self.default_enabled = release_data["default_enabled"] if "default_enabled" in release_data else True

    def check_update(self, config: ConfigParser) -> bool:
        path = config["turtle"]["turtle_path"]
        if Path.exists(Path(path) / self.dest_path / self.mpq_name):
            self.has_update = False
        else:
            self.has_update = True
        return self.has_update

    def install(self, config: ConfigParser) -> (bool, list[str]):
        path = config["turtle"]["turtle_path"]

        if self.direct_url:
            try:
                with tempfile.NamedTemporaryFile(mode="wb", delete=False) as tmp:
                    if self.zip:
                        urllib.request.urlretrieve(self.direct_url, tmp.name)
                        with zipfile.ZipFile(tmp.name) as zip:
                            zip.extract(self.mpq_name, Path(path) / self.dest_path)
                    else:
                        urllib.request.urlretrieve(self.direct_url, Path(path) / self.dest_path / self.mpq_name)
                    self.has_update = False
                    return True, [f"Successfully downloaded and installed {self.name}"]

            except Exception as e:
                return False, [e]
        else:
            return False, [f"{self.name} was not installed. (Only direct links are supported for mods)"]




def load_mods_from_json(json_data: dict) -> list[Mod]:
    mods = []
    if "mods" in json_data:
        for mod in json_data["mods"]:
            mods.append(Mod(mod))

    return mods