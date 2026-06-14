import json
import os
import re
from html import unescape

import requests

WEBHOOK_URL = "https://discord.com/api/webhooks/1515751123846168666/cLA-jiWaQyZyPWD2w-qshsg7KyBfy4I910Ok_c52ru5FVfX1Zvh1DOgwge4ZebqobD9O"
ROLE_PING = "<@&1515752173533790218>"

AUTHOR_ICON_URL = "https://files.catbox.moe/rusxk8.png"
FOOTER_ICON_URL = "https://files.catbox.moe/qttqpy.png"

API_URL = "https://medal.tv/api/v2/quests?limit=50&state=active"
POSTED_FILE = "posted_quests.json"

HEADERS = {
    "Accept": "application/json",
    "User-Agent": "Mozilla/5.0"
}


def load_posted():
    if not os.path.exists(POSTED_FILE):
        return {"active": {}}

    try:
        with open(POSTED_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)

        if isinstance(data, list):
            return {"active": {qid: {} for qid in data}}

        if isinstance(data, dict):
            data.setdefault("active", {})
            return data

    except Exception:
        pass

    return {"active": {}}


def save_posted(data):
    with open(POSTED_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)


def cut(text, limit=1000):
    text = str(text or "Not provided")
    return text[:limit - 3] + "..." if len(text) > limit else text


def clean_html(text):
    if not text:
        return "Not provided"

    text = unescape(text)
    text = re.sub(r"<br\s*/?>", "\n", text, flags=re.I)
    text = re.sub(r"<.*?>", "", text)
    return text.strip()


def to_timestamp(ms):
    if not ms:
        return "Unknown"

    try:
        ts = int(ms) // 1000
        return f"<t:{ts}:f>"
    except Exception:
        return "Unknown"


def fetch_quests():
    r = requests.get(API_URL, headers=HEADERS, timeout=30)
    r.raise_for_status()
    data = r.json()
    return data.get("items", [])


def get_quest_info(quest):
    qid = quest.get("id")
    config = quest.get("config", {})

    messages = config.get("messages", {})
    reward = config.get("reward", {})
    reward_msg = reward.get("messages", {})

    title = messages.get("name", "Unknown Medal Quest")
    quest_text = clean_html(messages.get("detailedDescription"))
    quest_text = re.sub(r"^Quest:\s*", "", quest_text, flags=re.I).strip()

    reward_name = reward_msg.get("name", "Unknown Reward")
    reward_desc = reward_msg.get("description", "No reward description")

    starts_at = config.get("startsAt")
    ends_at = config.get("endsAt")

    return {
        "id": qid,
        "title": title,
        "quest_text": quest_text,
        "reward_name": reward_name,
        "reward_desc": reward_desc,
        "startsAt": starts_at,
        "endsAt": ends_at
    }


def send_discord(quest):
    qid = quest.get("id")
    config = quest.get("config", {})

    messages = config.get("messages", {})
    assets = config.get("assets", {})
    reward = config.get("reward", {})
    reward_msg = reward.get("messages", {})

    title = messages.get("name", "Unknown Medal Quest")
    quest_text = clean_html(messages.get("detailedDescription"))
    quest_text = re.sub(r"^Quest:\s*", "", quest_text, flags=re.I).strip()

    reward_name = reward_msg.get("name", "Unknown Reward")
    reward_desc = reward_msg.get("description", "No reward description")

    banner = assets.get("banner")
    icon = reward.get("assets", {}).get("icon")

    start_time = to_timestamp(config.get("startsAt"))
    end_time = to_timestamp(config.get("endsAt"))

    quest_link = f"https://medal.tv/quests?questId={qid}"

    embed = {
        "author": {
            "name": "Medal TV - Quests",
            "icon_url": AUTHOR_ICON_URL
        },
        "title": title,
        "url": quest_link,
        "color": 0xA3FF12,
        "fields": [
            {
                "name": "Start at",
                "value": start_time,
                "inline": True
            },
            {
                "name": "End at",
                "value": end_time,
                "inline": True
            },
            {
                "name": "Quest",
                "value": cut(quest_text, 900),
                "inline": False
            },
            {
                "name": "Reward",
                "value": cut(f"{reward_name}\n{reward_desc}", 900),
                "inline": False
            }
        ],
        "footer": {
            "text": "Subho's Medal TV Quest Informer",
            "icon_url": FOOTER_ICON_URL
        }
    }

    if banner:
        embed["image"] = {"url": banner}

    if icon:
        embed["thumbnail"] = {"url": icon}

    payload = {
        "content": ROLE_PING,
        "embeds": [embed]
    }

    res = requests.post(WEBHOOK_URL, json=payload, timeout=30)

    if res.status_code >= 400:
        print("Discord error:", res.status_code, res.text[:500])
        return False

    return True


def send_ended_discord(old_quest):
    qid = old_quest.get("id")
    title = old_quest.get("title", "Unknown Medal Quest")
    quest_link = f"https://medal.tv/quests?questId={qid}"

    embed = {
        "author": {
            "name": "Medal TV - Quests",
            "icon_url": AUTHOR_ICON_URL
        },
        "title": f"Quest Ended: {title}",
        "url": quest_link,
        "color": 0xFF3333,
        "fields": [
            {
                "name": "Status",
                "value": "This quest is no longer active.",
                "inline": False
            }
        ],
        "footer": {
            "text": "Subho's Medal TV Quest Informer",
            "icon_url": FOOTER_ICON_URL
        }
    }

    payload = {
        "content": ROLE_PING,
        "embeds": [embed]
    }

    res = requests.post(WEBHOOK_URL, json=payload, timeout=30)

    if res.status_code >= 400:
        print("Discord ended error:", res.status_code, res.text[:500])
        return False

    return True


def main():
    posted_data = load_posted()
    posted_active = posted_data.get("active", {})

    quests = fetch_quests()

    quests.sort(
        key=lambda q: q.get("config", {}).get("startsAt", 0)
    )

    current_ids = {q.get("id") for q in quests if q.get("id")}

    print(f"Found {len(quests)} active quests")
    print(f"Already posted: {len(posted_active)}")

    print("\n=== Active Quests ===")
    for q in quests:
        quest_name = (
            q.get("config", {})
             .get("messages", {})
             .get("name", "Unknown Quest")
        )
        print(f"• {quest_name}")
    print("====================\n")

    new_count = 0
    ended_count = 0

    for old_qid, old_quest in list(posted_active.items()):
        if old_qid not in current_ids:
            print(f"Quest ended: {old_quest.get('title', old_qid)}")

            if send_ended_discord(old_quest):
                posted_active.pop(old_qid, None)
                save_posted(posted_data)
                ended_count += 1

    for quest in quests:
        info = get_quest_info(quest)
        qid = info.get("id")
        name = info.get("title", qid)

        if not qid or qid in posted_active:
            continue

        print(f"Posting new quest: {name}")

        if send_discord(quest):
            posted_active[qid] = info
            save_posted(posted_data)
            new_count += 1

    print(f"Posted {new_count} new quests")
    print(f"Posted {ended_count} ended quests")


if __name__ == "__main__":
    main()