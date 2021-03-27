import os
import sys
import textwrap
from io import BytesIO

import requests
from PIL import Image, ImageDraw, ImageFont
from dotenv import load_dotenv
from oppai import *

from utils.crop import cropped_thumbnail
from utils.replay_parser import ReplayParser

load_dotenv()
apiKey = os.getenv("apiKey")


def getBeatmapFile(beatmap_id: str):
    response = requests.get("https://osu.ppy.sh/osu/" + beatmap_id)
    return response.content


def getBeatmapFromMd5(Md5: str) -> dict:
    response = requests.get("https://osu.ppy.sh/api/get_beatmaps", {
        "k": apiKey,
        "h": Md5,
    })

    return response.json()[0]


def getUserFromUsername(username: str) -> dict:
    response = requests.get("https://osu.ppy.sh/api/get_user", {
        "k": apiKey,
        "u": username,
        "type": "string",
    })

    return response.json()[0]


def getScore(user: str, mods: str, beatmapId) -> dict:
    response = requests.get("https://osu.ppy.sh/api/get_scores", {
        "k": apiKey,
        "u": user,
        "mods": mods,
        "b": beatmapId
    })

    return response.json()[0]


def getCover(beatmapsetId: int) -> Image:
    response = requests.get(f"https://assets.ppy.sh/beatmaps/{beatmapsetId}/covers/cover@2x.jpg?")

    return Image.open(BytesIO(response.content))


def getAvatar(userId: int) -> Image:
    response = requests.get(f"https://a.ppy.sh/{userId}")
    avatarImage = Image.open(BytesIO(response.content)).convert("RGBA")

    return cropped_thumbnail(avatarImage, (222, 222))


def writeText(image: Image, fontSize: int, text: str, xy: tuple = (0, 0), anchor: str = "lm", fill: tuple = (0, 0, 0),
              center: bool = False, align: str = "center"):
    draw = ImageDraw.Draw(image)
    font = ImageFont.truetype("Stuff/Gothic.ttf", fontSize)

    if center:
        width, height = image.size

        xy = (width / 2, height / 2)
        anchor = "mm"

    draw.multiline_text(xy, text, font=font, anchor=anchor, fill=fill, align="center")

    return image


def main():
    replayInfo = ReplayParser(sys.argv[1])

    # Initialize pp calculator
    ez = ezpp_new()
    ezpp_set_autocalc(ez, 1)

    beatmapInfo = getBeatmapFromMd5(replayInfo.beatmap_md5)
    beatmapBytes = getBeatmapFile(beatmapInfo['beatmap_id'])
    userInfo = getUserFromUsername(replayInfo.player_name)
    cover = cropped_thumbnail(getCover(beatmapInfo["beatmapset_id"]), (3200, 1800))

    ezpp_data_dup(ez, beatmapBytes.decode('utf-8'), len(beatmapBytes))  # Load beatmap into pp calc

    template = Image.new("RGBA", (3200, 1800), color=("#ffffff"))
    templateMask = Image.open("Stuff/Masks/TemplateMask.png").convert("RGBA")
    avatarMask = Image.open("Stuff/Masks/AvatarMask.png").convert("L")

    template.paste(cover)
    template.paste(templateMask, (0, 0), templateMask)

    # Avatar
    avatar = getAvatar(userInfo["user_id"])
    template.paste(avatar, (220, 1455), avatarMask)

    # Username
    template = writeText(template, 140, userInfo["username"], (476, 1560))

    # Beatmap Title
    beatmapInfo["titleWrapped"] = "\n".join(textwrap.wrap(beatmapInfo["title"], 25))
    template = writeText(template, 200, beatmapInfo["titleWrapped"], center=True, fill=(255, 255, 255))

    # Play Stats
    # 228, 330

    acc = f'{replayInfo.acc:.2f}'
    template = writeText(template, 180, acc, (220, 390))
    template = writeText(template, 180, str(replayInfo.max_combo), (900, 390))

    scoreInfo = getScore(userInfo["username"], replayInfo.mods, beatmapInfo["beatmap_id"])

    ezpp_set_mods(ez, replayInfo.mods)  # Set mods in pp calc
    ezpp_set_accuracy(ez, replayInfo.count100, replayInfo.count50)
    ezpp_set_nmiss(ez, replayInfo.count_miss)
    ezpp_set_combo(ez, replayInfo.max_combo)

    if scoreInfo["pp"]:
        pp = f'{int(float(scoreInfo["pp"]))}'
    else:
        pp = f"{int(ezpp_pp(ez))}"

    template = writeText(template, 180, pp, (1590, 390))

    # Mods 
    # 404, 238
    xOffset = 2687
    for mod in replayInfo.parsed_mods:
        modImage = cropped_thumbnail(Image.open(f"Modicons/{mod}.png").convert("RGBA"), (404, 238))
        template.paste(modImage, (xOffset, 1450), modImage)

        xOffset -= 450

    template.save("thumbnail.png")

    mods = f" {''.join(replayInfo.parsed_mods)}" if replayInfo.parsed_mods else ""

    with open("text.txt", "w", encoding="utf-8") as file:
        file.write(f"""
# Title
{userInfo["username"]} - {beatmapInfo["title"]} [{beatmapInfo["version"]}] {acc}%{mods} {replayInfo.max_combo}x {pp}{"pp" if scoreInfo["pp"] else ""}

# Description
Oyuncu: https://osu.ppy.sh/users/{userInfo["user_id"]}
Harita: https://osu.ppy.sh/beatmapsets/{beatmapInfo["beatmapset_id"]}#osu/{beatmapInfo["beatmap_id"]}
Skin: 
        """)


if "__main__" == __name__:
    main()
