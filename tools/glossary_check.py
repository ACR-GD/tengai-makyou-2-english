#!/usr/bin/env python3
"""Report script records that break the glossary, without changing game data.

A record is flagged when its Japanese contains a canonical term but its English
lacks the canonical form, or when its English keeps a Japanese honorific.
Flags are review candidates: a pronoun or a rephrase can be correct English.
"""
import argparse
from collections import Counter
import json
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
TAG = re.compile(r"\{[0-9A-Fa-f]{4}\}|<[0-9A-Fa-f]{2}>")
HONORIFIC = re.compile(r"\b[A-Z][A-Za-z']+-(?:san|sama|dono|kun|chan|hime|tan)\b")
HONORIFIC_HIME = re.compile(r"\b([A-Z][A-Za-z]+)-hime\b")
HONORIFIC_STRIP = re.compile(r"\b([A-Z][A-Za-z']+)-(?:san|sama|dono|kun|chan|tan)\b")


def plain_en(record):
    return " ".join(TAG.sub(" ", record["en_tagged"]).split())


def checked_terms(glossary):
    skip = set(glossary.get("context_only", []))
    return {jp: en for jp, en in glossary["canonical"].items() if jp not in skip and "(" not in jp}


def term_pattern(jp):
    """Katakana names match as whole words, so ニック does not hit メカニック."""
    if re.fullmatch(r"[ァ-ヴー・]+", jp):
        return re.compile(r"(?<![ァ-ヴー])" + re.escape(jp) + r"(?![ァ-ヴー])")
    return re.compile(re.escape(jp))


def find_issues(records, glossary, prefix=""):
    terms = {term_pattern(jp): (jp, want) for jp, want in checked_terms(glossary).items()}
    aliases = glossary.get("aliases", {})
    issues = []
    for r in records:
        if not r["id"].startswith(prefix):
            continue
        en = plain_en(r)
        low = en.lower()
        hits = [(jp, want) for pat, (jp, want) in terms.items() if pat.search(r["jp_clean"])]
        for jp, want in hits:
            # A longer matching term (大霊院女彦) takes precedence over one it contains (大霊院).
            if any(jp != other and jp in other for other, _ in hits):
                continue
            if not any(form.lower() in low for form in [want, *aliases.get(want, [])]):
                issues.append({"id": r["id"], "kind": "term", "jp": jp, "want": want, "en": en})
        for m in HONORIFIC.finditer(en):
            issues.append({"id": r["id"], "kind": "honorific", "found": m.group(0), "en": en})
    return issues


def fixable(record):
    """Timed subtitles, choice menus and banners have length-bound layouts; leave them to hand review."""
    t = record["en_tagged"]
    return not any(op in t for op in ("{0010}", "{0011}", "{0001}", "{0016}"))


def fix_text(text, variants):
    text = HONORIFIC_HIME.sub(lambda m: "Princess " + m.group(1), text)
    text = HONORIFIC_STRIP.sub(r"\1", text)
    pairs = sorted(((v, want) for want, vs in variants.items() for v in vs), key=lambda p: -len(p[0]))
    for v, want in pairs:
        text = re.sub(r"(?<![\w-])" + re.escape(v) + r"(?![\w-])", want, text)
    return text


def apply_fixes(records, glossary, prefix=""):
    """Rewrite honorifics and listed variants in en_tagged and en; return the changed ids."""
    variants = glossary.get("variants", {})
    changed = []
    for r in records:
        if not r["id"].startswith(prefix) or not fixable(r):
            continue
        new = {k: fix_text(r[k], variants) for k in ("en_tagged", "en")}
        if new["en_tagged"] != r["en_tagged"] or new["en"] != r["en"]:
            r.update(new)
            changed.append(r["id"])
    return changed


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--json", type=Path, default=ROOT / "translation/tengai2_script.translated.json")
    ap.add_argument("--glossary", type=Path, default=ROOT / "translation/glossary.json")
    ap.add_argument("--prefix", default="", help="only check ids starting with this, e.g. wa1/")
    ap.add_argument("--list", action="store_true", help="print every flagged record")
    ap.add_argument("--fix", action="store_true", help="rewrite honorifics and listed variants in the JSON")
    a = ap.parse_args()
    records = json.loads(a.json.read_text(encoding="utf-8"))
    glossary = json.loads(a.glossary.read_text(encoding="utf-8"))
    if a.fix:
        changed = apply_fixes(records, glossary, a.prefix)
        a.json.write_text(json.dumps(records, ensure_ascii=False, indent=1), encoding="utf-8")
        print(f"fixed {len(changed)} records")
    issues = find_issues(records, glossary, a.prefix)
    if a.list:
        for i in issues:
            what = i.get("found") or f"{i['jp']} -> {i['want']}"
            print(f"{i['id']}\t{i['kind']}\t{what}\t{i['en']}")
    terms = Counter(i["want"] for i in issues if i["kind"] == "term")
    hons = Counter(i["found"] for i in issues if i["kind"] == "honorific")
    print(f"{len(issues)} flags: {sum(terms.values())} term, {sum(hons.values())} honorific")
    for want, n in terms.most_common(25):
        print(f"  term  {n:5}  {want}")
    for found, n in hons.most_common(10):
        print(f"  hon   {n:5}  {found}")


if __name__ == "__main__":
    main()
