from utils.crop import cropped_thumbnail
from utils.replay_parser import ReplayParser
from io import BytesIO
from PIL import Image, ImageDraw, ImageFont
from dotenv import load_dotenv
import sys
import requests
import textwrap
import os

load_dotenv()
apiKey = os.getenv("apiKey")


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


def writeText(image: Image, fontSize: int ,text: str , xy: tuple = (0, 0), anchor: str = "lm", fill: tuple = (0, 0, 0), center: bool = False, align: str = "center"):
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

    beatmapInfo = getBeatmapFromMd5(replayInfo.beatmap_md5)
    userInfo = getUserFromUsername(replayInfo.player_name)
    cover = cropped_thumbnail(getCover(beatmapInfo["beatmapset_id"]), (3200, 1800))

    template = Image.new("RGBA", (3200, 1800), color=("#ffffff"))
    templateMask = Image.open("Stuff/Masks/TemplateMask.png").convert("RGBA")
    avatarMask = Image.open("Stuff/Masks/AvatarMask.png").convert("L")

    template.paste(cover)
    template.paste(templateMask, (0, 0), templateMask)

    # Avatar
    avatar = getAvatar(userInfo["user_id"])
    template.paste(avatar, (228, 1455), avatarMask)

    # Username
    template = writeText(template, 140, userInfo["username"], (480, 1560))

    # Beatmap Title
    beatmapInfo["titleWrapped"] = "\n".join(textwrap.wrap(beatmapInfo["title"], 20))
    template = writeText(template, 180, beatmapInfo["titleWrapped"], center=True, fill=(255, 255, 255))

    # Play Stats
    # 228, 330

    acc = f'{replayInfo.acc:.2f}'
    template = writeText(template, 150, acc, (220, 390))
    template = writeText(template, 150, str(replayInfo.max_combo), (900, 390))
    
    scoreInfo = getScore(userInfo["username"], replayInfo.mods, beatmapInfo["beatmap_id"])
    
    if scoreInfo["pp"]:
        pp = f'{int(float(scoreInfo["pp"]))}'
    else:
        pp = "Loved"

    template = writeText(template, 150, pp, (1590, 390))

    # Mods 
    # 404, 238
    xOffset = 2687
    for mod in replayInfo.parsed_mods:
        modImage = cropped_thumbnail(Image.open(f"Modicons/{mod}.png").convert("RGBA"), (404, 238))
        template.paste(modImage, (xOffset, 1450), modImage)
        
        xOffset -= 450


    template.save("thumbnail.png")

    with open("text.txt", "w", encoding="utf-8") as file:
        file.write(f"""
# Title
{userInfo["username"]} - {beatmapInfo["title"]} [{beatmapInfo["version"]}] {acc}% {replayInfo.max_combo}x {pp}

# Description
Oyuncu: https://osu.ppy.sh/users/{userInfo["user_id"]}
Harita: https://osu.ppy.sh/beatmapsets/{beatmapInfo["beatmapset_id"]}#osu/{beatmapInfo["beatmap_id"]}
Skin: 
        """)


if "__main__" == __name__:
    main()