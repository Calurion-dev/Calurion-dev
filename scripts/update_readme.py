#!/usr/bin/env python3
"""Regénère le README de profil depuis les README des dépôts GitHub."""
import json
import os
import re
import urllib.error
import urllib.request

OWNER = "Calurion-dev"
API = "https://api.github.com"
TOKEN = os.environ.get("GITHUB_TOKEN", "")
README = "README.md"

CATEGORIES = [
    ("sport", "🏋️ Sport & calisthénie"),
    ("music", "🥁 Musique"),
    ("tools", "🛠️ Outils"),
    ("web", "🌐 Web & side projects"),
    ("other", "📦 Autres projets"),
]

# Ordre d'affichage ; les nouveaux dépôts arrivent à la fin de leur catégorie.
ORDER = [
    "FitQuest", "Calicoach", "Calisthenix-Lab", "Workout-Calculator2000", "Random-Trail",
    "site-learnbatterie", "Drum-part",
    "QuickCut", "Open-montage",
    "Site-vitrine-menuiserie", "Simubac-2027", "Wiki-Hay-Day", "Footlive",
]

CATEGORY = {
    "FitQuest": "sport",
    "Calicoach": "sport",
    "Calisthenix-Lab": "sport",
    "Workout-Calculator2000": "sport",
    "Random-Trail": "sport",
    "site-learnbatterie": "music",
    "Drum-part": "music",
    "QuickCut": "tools",
    "Open-montage": "tools",
    "Site-vitrine-menuiserie": "web",
    "Simubac-2027": "web",
    "Wiki-Hay-Day": "web",
    "Footlive": "web",
}

KEYWORDS = {
    "sport": ["sport", "workout", "fitness", "calisthen", "gym", "muscu", "trail", "velo", "course", "running", "foot", "basket"],
    "music": ["music", "musique", "drum", "batterie", "piano", "guitare", "guitar", "audio"],
    "tools": ["tool", "outil", "cli", "script", "bot", "automation", "montage", "video", "cut"],
    "web": ["site", "web", "wiki", "guide", "portfolio", "html", "css"],
}

NAMES = {
    "Calicoach": "CaliCoach",
    "site-learnbatterie": "LearnBatterie",
    "Simubac-2027": "Simubac 2027",
    "Wiki-Hay-Day": "Wiki Hay Day",
    "Open-montage": "OpenMontage",
    "Site-vitrine-menuiserie": "Confort Bois Habitat",
}

# Dépôts privés : invisibles via l'API, donc décrits ici.
PRIVATE = [
    {
        "repo": "Open-montage",
        "name": "OpenMontage",
        "category": "tools",
        "description": "Plateforme de production vidéo pilotée par un agent IA : pipelines, outils Python, checkpoints.",
    },
    {
        "repo": "Site-vitrine-menuiserie",
        "name": "Confort Bois Habitat",
        "category": "web",
        "description": "Site vitrine pour un menuisier du Rhône.",
    },
]

# Dépôts sans README exploitable.
OVERRIDES = {
    "FitQuest": "RPG de street workout : XP, quêtes, badges, classement et carte des spots.",
    "Workout-Calculator2000": "Générateur de séances aléatoires de calisthénie et street workout.",
    "Drum-part": "Logiciel simple pour créer des partitions de batterie.",
    "QuickCut": "Coupe la musique automatiquement à l'ouverture de DaVinci Resolve.",
    "Simubac-2027": "Simulateur de notes pour le bac.",
    "Wiki-Hay-Day": "Guide complet du jeu Hay Day.",
    "Footlive": "Prototype d'app Expo de scores de foot en direct (inachevé).",
}

HEADER = """# Salut, moi c'est Calurion 👋

Je code des sites web et des petits outils, surtout autour du sport, de la musique et du web.
Tous mes projets sont ici, avec une démo quand elle est en ligne.

`TypeScript` · `JavaScript` · `Python` · `HTML/CSS`
"""


def api(path, accept="application/vnd.github+json"):
    req = urllib.request.Request(API + path)
    req.add_header("Accept", accept)
    req.add_header("X-GitHub-Api-Version", "2022-11-28")
    if TOKEN:
        req.add_header("Authorization", f"Bearer {TOKEN}")
    with urllib.request.urlopen(req, timeout=30) as res:
        return res.read()


def repos():
    page = 1
    while True:
        data = json.loads(api(
            f"/users/{OWNER}/repos?per_page=100&type=owner&page={page}"
        ))
        yield from data
        if len(data) < 100:
            break
        page += 1


def readme(repo):
    try:
        return api(f"/repos/{OWNER}/{repo}/readme", "application/vnd.github.raw").decode("utf-8", "replace")
    except urllib.error.HTTPError as err:
        if err.code == 404:
            return ""
        raise


def plain(md):
    md = re.sub(r"<!--.*?-->", " ", md, flags=re.S)
    md = re.sub(r"\[!\[[^\]]*\]\([^)]*\)\]\([^)]*\)", " ", md)
    md = re.sub(r"!\[[^\]]*\]\([^)]*\)", " ", md)
    md = re.sub(r"<[^>]+>", " ", md)
    md = re.sub(r"\[([^\]]+)\]\([^)]*\)", r"\1", md)
    md = re.sub(r"[*_`~]", "", md)
    return re.sub(r"\s+", " ", md).strip()


def intro(md):
    """Premier paragraphe de texte du README, hors titre, badges et images."""
    para = []
    for line in md.splitlines():
        text = line.strip()
        if text.startswith("```"):
            break
        if not text:
            if para:
                break
            continue
        if text.startswith(("#", "![", "[![", "<", ">", "---", "|")):
            if para:
                break
            continue
        para.append(text)
    return plain(" ".join(para))


def shorten(text, limit=160):
    text = text.strip()
    if len(text) <= limit:
        return text
    cut = text[:limit]
    if " — " in cut[60:]:
        return cut[:cut.rindex(" — ")].rstrip(" ,;:.")
    return cut.rsplit(" ", 1)[0].rstrip(" ,;:.-—") + "…"


def description(repo_name, data, md):
    if repo_name in OVERRIDES:
        return OVERRIDES[repo_name]
    text = intro(md) or (data.get("description") or "")
    sentences = re.split(r"(?<=[.!?])\s+", text.strip())
    picked = ""
    for sentence in sentences:
        candidate = (picked + " " + sentence).strip()
        if len(candidate) > 160:
            break
        picked = candidate
    text = shorten(picked or text).strip()
    if text and text[-1] not in ".!?…":
        text += "."
    return text


def category(repo_name, text):
    if repo_name in CATEGORY:
        return CATEGORY[repo_name]
    haystack = plain(f"{repo_name} {text}").lower()
    for key, words in KEYWORDS.items():
        if any(word in haystack for word in words):
            return key
    return "other"


def demo(data):
    home = (data.get("homepage") or "").strip()
    if home:
        return home
    if data.get("has_pages"):
        return f"https://{OWNER.lower()}.github.io/{data['name']}/"
    return ""


def item(repo_name, name, cat, desc, link, is_private):
    return {
        "repo": repo_name,
        "name": name,
        "category": cat,
        "desc": desc,
        "link": link,
        "private": is_private,
        "order": ORDER.index(repo_name) if repo_name in ORDER else len(ORDER),
    }


def line(entry):
    if entry["private"]:
        title = f"**{entry['name']}** *(code privé)*"
    else:
        title = f"**[{entry['name']}](https://github.com/{OWNER}/{entry['repo']})**"
    text = f"- {title} — {entry['desc']}"
    if entry["link"]:
        text += f" → [Démo]({entry['link']})"
    return text


def main():
    groups = {}
    for data in repos():
        name = data["name"]
        if name == OWNER or data["private"] or data["fork"] or data["archived"]:
            continue
        md = readme(name)
        desc = description(name, data, md)
        if not desc:
            continue
        cat = category(name, desc)
        groups.setdefault(cat, []).append(item(
            name, NAMES.get(name, name), cat, desc, demo(data), False
        ))

    known = {entry["repo"] for entries in groups.values() for entry in entries}
    for extra in PRIVATE:
        if extra["repo"] in known:
            continue
        groups.setdefault(extra["category"], []).append(item(
            extra["repo"], extra["name"], extra["category"],
            extra["description"], "", True
        ))

    parts = [HEADER.rstrip("\n")]
    for key, title in CATEGORIES:
        entries = sorted(
            groups.get(key, []), key=lambda e: (e["order"], e["name"].lower())
        )
        if entries:
            parts.append(f"## {title}\n\n" + "\n".join(line(e) for e in entries))

    output = "\n\n".join(parts).rstrip() + "\n"
    current = ""
    if os.path.exists(README):
        with open(README, encoding="utf-8") as file:
            current = file.read()
    if output != current:
        with open(README, "w", encoding="utf-8", newline="\n") as file:
            file.write(output)
        print("README updated")
    else:
        print("No change")


if __name__ == "__main__":
    main()
