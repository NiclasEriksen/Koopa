import os
import sys
import json
from fetchers import tweaks


if __name__ == "__main__":
    p = os.path.join(os.path.dirname(os.path.realpath(sys.argv[0])), "tweaks.json")

    with open(p) as json_file:
        json_data = json.load(json_file)

    t = tweaks.load_tweaks_from_json(json_data)
    for tw in t:
        print(tw.name)