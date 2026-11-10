#!/usr/bin/env python3
"""Batch-translate extracted Japanese script text via Google Cloud Translate v2.

Features:
  * Reads API key from translation/.env (GOOGLE_API_KEY).
  * De-duplicates identical segments to minimise quota usage.
  * Batches requests (segment + character limits) with retry/backoff.
  * Resumable: persists a translate_cache.json after every batch.
  * Writes machine drafts separately; never overwrites the edited translation.
"""
import html
import json
import os
import sys
import time
import urllib.error
import urllib.request

ROOT = os.path.join(os.path.dirname(__file__), "..", "translation")
ROOT = os.path.abspath(ROOT)
ENDPOINT = "https://translation.googleapis.com/language/translate/v2"

MAX_SEGMENTS = 100          # API hard limit is 128
MAX_CHARS_PER_BATCH = 8000  # stay well under request size limits


def load_key():
    for line in open(os.path.join(ROOT, ".env"), encoding="utf-8"):
        line = line.strip()
        if line.startswith("GOOGLE_API_KEY="):
            return line.split("=", 1)[1].strip().strip('"').strip("'")
    raise SystemExit("GOOGLE_API_KEY not found in translation/.env")


def translate_batch(key, segs, retries=5):
    body = json.dumps({"q": segs, "source": "ja", "target": "en",
                       "format": "text"}).encode("utf-8")
    url = f"{ENDPOINT}?key={key}"
    delay = 2.0
    for attempt in range(retries):
        req = urllib.request.Request(url, data=body,
                                     headers={"Content-Type": "application/json"})
        try:
            with urllib.request.urlopen(req, timeout=60) as r:
                d = json.load(r)
            return [html.unescape(t["translatedText"])
                    for t in d["data"]["translations"]]
        except urllib.error.HTTPError as e:
            msg = e.read().decode("utf-8", "replace")
            if e.code in (429, 500, 503) and attempt < retries - 1:
                time.sleep(delay)
                delay *= 2
                continue
            raise SystemExit(f"HTTP {e.code}: {msg[:400]}")
        except (urllib.error.URLError, TimeoutError):
            if attempt < retries - 1:
                time.sleep(delay)
                delay *= 2
                continue
            raise


def build_batches(items):
    batch, n_chars = [], 0
    for s in items:
        if batch and (len(batch) >= MAX_SEGMENTS or n_chars + len(s) > MAX_CHARS_PER_BATCH):
            yield batch
            batch, n_chars = [], 0
        batch.append(s)
        n_chars += len(s)
    if batch:
        yield batch


def main():
    key = load_key()
    recs = json.load(open(os.path.join(ROOT, "tengai2_script.json"), encoding="utf-8"))

    cache_path = os.path.join(ROOT, "translate_cache.json")
    cache = {}
    if os.path.exists(cache_path):
        cache = json.load(open(cache_path, encoding="utf-8"))

    # unique segments still needing translation
    uniques = []
    seen = set()
    for r in recs:
        s = r["jp_clean"]
        if s and s not in cache and s not in seen:
            seen.add(s)
            uniques.append(s)

    total_unique = len(seen) + len(cache)
    print(f"Records: {len(recs)} | unique segments total: ~{total_unique} | "
          f"already cached: {len(cache)} | to translate: {len(uniques)}", flush=True)

    done = 0
    for batch in build_batches(uniques):
        outs = translate_batch(key, batch)
        for src, dst in zip(batch, outs):
            cache[src] = dst
        done += len(batch)
        json.dump(cache, open(cache_path, "w", encoding="utf-8"), ensure_ascii=False)
        print(f"  translated {done}/{len(uniques)} segments", flush=True)

    # fill records
    for r in recs:
        r["en"] = cache.get(r["jp_clean"], "")

    json.dump(recs, open(os.path.join(ROOT, "tengai2_script.machine.json"),
                         "w", encoding="utf-8"), ensure_ascii=False, indent=1)

    import csv
    with open(os.path.join(ROOT, "tengai2_script.machine.csv"),
              "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(["id", "file", "msg", "jp_clean", "en"])
        for r in recs:
            w.writerow([r["id"], r["file"], r["msg"], r["jp_clean"], r["en"]])

    # English readable dumps mirroring the JP ones
    en_dir = os.path.join(ROOT, "text_dump_machine")
    by_file = {}
    for r in recs:
        by_file.setdefault(r["file"], []).append(r)
    for rel, rs in by_file.items():
        out_txt = os.path.join(en_dir, rel + ".txt")
        os.makedirs(os.path.dirname(out_txt), exist_ok=True)
        with open(out_txt, "w", encoding="utf-8") as f:
            f.write(f"# {rel}\n")
            for r in rs:
                f.write(f"\n--- msg {r['msg']} ---\n")
                f.write("JP: " + r["jp_clean"].replace("\n", "\nJP: ") + "\n")
                f.write("EN: " + r["en"].replace("\n", "\nEN: ") + "\n")

    print(f"\nDone. {len(cache)} unique segments cached.")
    print("Outputs: tengai2_script.machine.json/.csv, text_dump_machine/**.txt")
    print("Edited tengai2_script.translated.json and en_tagged were not changed.")


if __name__ == "__main__":
    main()
