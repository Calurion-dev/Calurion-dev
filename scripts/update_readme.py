#!/usr/bin/env python3
"""Regénère le README de profil depuis les README des dépôts GitHub."""
import hashlib
import json
import os
import re
import urllib.error
import urllib.request

OWNER = "Calurion-dev"
API = "https://api.github.com"
TOKEN = os.environ.get("GITHUB_TOKEN", "")
README = "README.md"

# shortcut: incrémenter VERSION à la main si le rendu change ; sinon le bot
# considère qu'il n'y a rien à faire tant qu'aucun dépôt ne bouge.
VERSION = 1

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
    "QuickCut", "Scenopia",
    "Simubac-2027", "Wiki-Hay-Day", "Footlive",
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
    "Scenopia": "tools",
    "Simubac-2027": "web",
    "Wiki-Hay-Day": "web",
    "Footlive": "web",
}

KEYWORDS = {
    "sport": ["sport", "workout", "fitness", "calisthen", "gym", "muscu", "trail", "velo", "course", "running", "foot", "basket"],
    "music": ["music", "musique", "drum", "batterie", "piano", "guitare", "guitar", "audio"],
    "tools": ["tool", "outil", "cli", "script", "bot", "automation", "montage", "video", "cut", "tournage", "film"],
    "web": ["site", "web", "wiki", "guide", "portfolio", "html", "css"],
}

NAMES = {
    "Calicoach": "CaliCoach",
    "site-learnbatterie": "LearnBatterie",
    "Simubac-2027": "Simubac 2027",
    "Wiki-Hay-Day": "Wiki Hay Day",
}

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


def item(repo_name, name, cat, desc, link):
    return {
        "repo": repo_name,
        "name": name,
        "category": cat,
        "desc": desc,
        "link": link,
        "order": ORDER.index(repo_name) if repo_name in ORDER else len(ORDER),
    }


def line(entry):
    title = f"**[{entry['name']}](https://github.com/{OWNER}/{entry['repo']})**"
    text = f"- {title} — {entry['desc']}"
    if entry["link"]:
        text += f" → [Démo]({entry['link']})"
    return text


def fingerprint(data):
    state = [
        [r["name"], r["pushed_at"], r.get("description"), r.get("homepage"), r.get("has_pages")]
        for r in data
        if r["name"] != OWNER and not r["private"] and not r["fork"] and not r["archived"]
    ]
    state.sort()
    payload = json.dumps([VERSION, state], sort_keys=True).encode()
    return hashlib.sha256(payload).hexdigest()[:12]


def main():
    data = list(repos())
    fp = fingerprint(data)

    current = ""
    if os.path.exists(README):
        with open(README, encoding="utf-8") as file:
            current = file.read()
    if f"<!-- fingerprint: {fp} -->" in current:
        print("No repo change")
        return

    groups = {}
    for repo in data:
        name = repo["name"]
        if name == OWNER or repo["private"] or repo["fork"] or repo["archived"]:
            continue
        md = readme(name)
        desc = description(name, repo, md)
        if not desc:
            continue
        cat = category(name, desc)
        groups.setdefault(cat, []).append(item(
            name, NAMES.get(name, name), cat, desc, demo(repo)
        ))

    parts = [HEADER.rstrip("\n")]
    for key, title in CATEGORIES:
        entries = sorted(
            groups.get(key, []), key=lambda e: (e["order"], e["name"].lower())
        )
        if entries:
            parts.append(f"## {title}\n\n" + "\n".join(line(e) for e in entries))

    output = "\n\n".join(parts).rstrip() + f"\n\n<!-- fingerprint: {fp} -->\n"
    if output != current:
        with open(README, "w", encoding="utf-8", newline="\n") as file:
            file.write(output)
        print("README updated")
    else:
        print("No change")


if __name__ == "__main__":
    main()
