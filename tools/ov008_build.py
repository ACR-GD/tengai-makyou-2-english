#!/usr/bin/env python3
"""Encode Overlay 3 (ov_008) cutscene subtitles and re-point subtitle table across 3 arenas."""
from __future__ import annotations

import json
import struct
from pathlib import Path
from typing import Dict, List, Tuple

from scs_codec import enc_char
from vwf_font import measure_line_px

SUBTITLE_JSON = Path(__file__).resolve().parents[1] / "translation/ov008_subtitles.json"
SUBTITLE_ARM9_ARENA = (0xF4620, 0xF4D94)
SUBTITLE_TAIL_ARENA = (0x11E390, 0x11E7A4)
COMBAT_RELOAD_ARENA = (0x11E7A4, 0x11E7E4)
BATTLE_NUMERIC_RENDERER = (0x18960, 0x190D4)

# 189 Japanese subtitle lines in table index order
SUBTITLE_LINES_JP: List[str] = [
    # 0-15: Opening Inn
    "んんぐっ　んっ　ふう……", "かあちゃん　おかわり", "卍丸はいるかー？", "卍丸……",
    "またどこかでケンカしたんでしょう", "まったく　しょうがない子ねえ…", "それにしても　子供のケンカに",
    "いちいち親が出てくるなんて", "おとなのすることじゃないわ", "卍丸", "お前はほとぼりが冷めるまで",
    "どこかその辺でひまをつぶしておいで", "二階のいつもの所からお逃げ！",
    "後は　母さんがてきとうにあしらって", "おくから", "まかせなさい",
    # 16-40: Kabuki Danjuro Intro
    "どけどけどけどけどけどけどけーい！", "ジパング一の伊達男",
    "カブキ団十郎さまのお通りでぇーい｜", "小汚ねえいなか者は　はずかしそうに",
    "道のはじっこを　歩きやがれ｜", "あ？　そのちいせえ体に", "ちぃーとも",
    "にあわねえ陣羽織　おめえが卍丸か？", "耳かっぽじって　よーく聞けよ！",
    "おめえといっしょに　戦うつもりは", "ぜーんぜんないっ｜", "俺は　たしかに火の一族だ！",
    "しかし　生まれてこのかた　それで", "得したことなんざ　一度もねえ！",
    "俺は　この火の血の力で", "目立って", "目立って　目立ちまくって", "名を売って",
    "チョー", "派手に　生きるのさ｜", "まっ　そういうわけだ！",
    "テメエもな　ジパングのためとか", "宿命とか捨てて　楽しくやれや！なっ！",
    "はっはっはっはっ！", "ハーハーハーハーハハハハ！",
    # 41-48: Shinigami Brothers
    "我々は　根の一族の刺客", "死神兄弟だ", "卍丸よ", "そこにいるのはわかっているぞ",
    "宿屋ごとつぶしてもかまわんが", "子分の命がおしかったら", "外に", "出てこーーーい｜",
    # 49-59: Prologue Mari & Yomi
    "マリよ", "ヨミよ", "私のかわいい子たち", "お前たち二人の力を合わせ",
    "この世界の中で", "もっとも美しき地に", "何者にも屈せぬ", "強き命を産み落とし",
    "そして　育みなさい", "さあ", "旅立つのです",
    # 60-72: Madam Basshou Betrayal
    "かあさま　なにをするの♀", "何をするのだってぇ？　フフフフフ",
    "火の一族は　なんてバカなんだい！", "母親が　生きていると思ったのかい？",
    "生きているわけが　無いんだよ！", "だって　あたしが殺したんだからね｜",
    "今　この三人を料理してやるから", "そこで見ておいで！", "その後おまえも",
    "母親と同じところへ送ってやるよ！", "おー　ほっほっほっほっほっ…", "かあさま…", "だましたのね｜",
    # 73-90: Kinu Demon Awakening
    "なぜ　私がキヌと言う名前かわかる？", "鬼が怒る", "と書いて", "鬼怒（キヌ）",
    "それが　私の本当の名前…", "私の体にねむる", "鬼の力", "今まで",
    "誰にも見せたことがなかったけど", "もう　ゆるせないっ｜", "私を怒らせた",
    "自分のおろかさを呪いながら", "死んで　行きなさいっ｜", "はぁ…　はぁはぁ　はぁ……",
    "わぁああああああああああ♀", "はぅ　わあああああああ｜", "うぁ……",
    "うぁああああああああああああああ……",
    # 91-113: Yomi Final Monologue
    "お　お前たちは", "い　いったい", "何者なのだ？", "マリのつくった　火の一族には",
    "こんな力はないはず…", "そのゆるぎなき闘争心", "決してあきらめぬ　ふくつの心",
    "それは　我が子根の民に", "このヨミが与えしもの…", "なぜお前たちが　その力を？",
    "お前たちの中には　火の力と根の力が", "共に宿っているというのか？",
    "千年の時の中で　火と根は", "交ざり合ったというのか…",
    "まさか　それが　人間と言うものか…", "正も邪も",
    "お前たちは　自分で決めてしまうのか…", "神は　いらぬと言うか…",
    "マリよ　目覚めよ　我が体内より出よ", "正と邪が交じり合う　不純な命を",
    "その目で確かめ…", "そして……！", "絶望するがいいわー｜",
    # 114-179: Mari Ending Speech
    "火の子供たちよ", "私の声が聞こえますか？", "マリです",
    "ヨミのジュバクをといてくれたことに", "感謝します", "お前たちが戦っている時",
    "何もしてやれず", "苦しい思いをさせた事を　許しておくれ", "でも",
    "お前たちは立派に戦った", "その力を", "信じていいのですよ",
    "これから　私はお前たちに", "大切な話をしなければなりません", "よく聞くのですよ",
    "この地に", "何者にも屈せぬ", "強く新しい命を生み出すために",
    "私とヨミはやってきたのです", "ヨミは", "強さとは",
    "争いに勝ち抜くことだと　考えました", "私は", "強さとは", "他人をかばいやる",
    "愛だと思ったのです", "そして", "根の民と火の民が　生まれたのです",
    "根と火は", "当然のごとく　争いあいましたが", "火の民は", "その大いなる愛のあまり",
    "根の民とも　交わってしまったのです", "そして", "凶暴さと　愛情という",
    "二つの相反する性格を持つ", "人間と言う存在が　生まれました", "私は",
    "予期せぬじたいにとまどいましたが", "それが", "彼らの力の源だと気付いた時",
    "私は", "人間を信じてみることにしたのです", "もう", "私とヨミのみちしるべは",
    "必要ありません", "何者にもたよらず", "人間は", "自分の力で", "歩いて行けるでしょう",
    "私たちの　使命は終わりました", "私は　ヨミを連れて", "生まれた地へ　戻ります",
    "なにもしてやれなかった", "私だけど", "最後に一つくらい",
    "母親らしいことをさせておくれ", "ヨミにうばわれた", "お前たちの", "大事な人を",
    "できるだけたくさん", "心の中に思いえがくのです", "卍丸よ", "そして",
    "火の子供たちよ", "さようなら……",
    # 180-188: Kikugoro Dying Pleading
    "助けて！　助けて！　卍丸さん…", "あの娘を　止めてぇ｜", "あ　あたしが悪かった…",
    "もう二度と　こんなことはしない…", "あんたたちの目の前にもあらわれない",
    "だからおねがい", "はやく…　あの娘を止めて…", "もう　ゆるして……", "だめっ｜",
]


def load_subtitles(path=SUBTITLE_JSON):
    records = json.loads(Path(path).read_text(encoding="utf-8"))
    if len(records) != len(SUBTITLE_LINES_JP):
        raise ValueError("Subtitle data must contain exactly 189 ordered occurrences")
    for idx, (r, jp) in enumerate(zip(records, SUBTITLE_LINES_JP)):
        if r["index"] != idx or r["jp"] != jp or r["id"] != f"ov008/{idx:03d}":
            raise ValueError(f"Subtitle source/index mismatch at {idx}")
        en = r.get("en")
        if not isinstance(en, str) or not en.strip() or "\n" in en or "{" in en or "<" in en:
            raise ValueError(f"Invalid subtitle English at {idx}")
        if measure_line_px(en) > 212:
            raise ValueError(f"Subtitle {idx} exceeds 212 pixels")
        if any("\u3040" <= c <= "\u30ff" or "\u4e00" <= c <= "\u9fff" for c in en):
            raise ValueError(f"Japanese remains in subtitle {idx}")
    return records


def enc_fullwidth_sjis(text: str) -> bytes:
    """Encode an English string to full-width Shift-JIS terminated by 0x0000."""
    out = bytearray()
    for ch in text:
        out += enc_char(ch, translit=True)
    out += b"\x00\x00"
    return bytes(out)


def allocate_subtitles(records=None) -> Tuple[List[int], bytearray, bytearray, bytearray]:
    """Allocate all 189 subtitles across the 3 arenas and return (ptrs, buf1, buf2, buf3)."""
    arenas = [
        {"name": "ov008",       "ram_base": 0x022B4C20, "cap": 4236, "buf": bytearray()},
        {"name": "arm9_f4620",  "ram_base": 0x020F4620, "cap": 1908, "buf": bytearray()},
        {"name": "arm9_11e390", "ram_base": 0x0211E390, "cap": 1044, "buf": bytearray()},
    ]

    if records is None:
        records = load_subtitles()
    str_ptrs: Dict[bytes, int] = {}
    line_ptrs: List[int] = []

    for idx, record in enumerate(records):
        raw = enc_fullwidth_sjis(record["en"])
        if raw in str_ptrs:
            line_ptrs.append(str_ptrs[raw])
            continue

        allocated = False
        for a in arenas:
            if len(a["buf"]) + len(raw) <= a["cap"]:
                addr = a["ram_base"] + len(a["buf"])
                a["buf"] += raw
                str_ptrs[raw] = addr
                line_ptrs.append(addr)
                allocated = True
                break
        if not allocated:
            raise RuntimeError(f"Could not fit {len(raw)}B for line {idx} in any arena!")

    # Pad remaining capacity with 0
    for a in arenas:
        while len(a["buf"]) < a["cap"]:
            a["buf"].append(0)

    return line_ptrs, arenas[0]["buf"], arenas[1]["buf"], arenas[2]["buf"]


def patch_ov008(rom: bytearray, o8s: int, o8e: int,
                arm9_rom_off: int = 0x4000, arm9_size: int = 0x1204F8) -> int:
    """Patch all 189 subtitle strings into ov_008 & ARM9, and re-point the pointer table.

    Returns the number of patched subtitle pointers (189).
    """
    line_ptrs, buf_ov, buf_arm1, buf_arm2 = allocate_subtitles()
    if not (0 <= o8s < o8e <= len(rom)) or o8s + 0x5EB0 + len(line_ptrs) * 4 > o8e:
        raise ValueError("Overlay 8 is too small for the subtitle arenas/table")
    if arm9_size < 0x11E390 + len(buf_arm2) or arm9_rom_off + arm9_size > len(rom):
        raise ValueError("ARM9 is too small for the subtitle arenas")

    # 1. Write Arena 1 into ov_008 @ file offset 0x4DE0 (length 4,236 B)
    ov_str_start = o8s + 0x4DE0
    rom[ov_str_start : ov_str_start + len(buf_ov)] = buf_ov

    # 2. Write Arena 2 into arm9 @ file offset 0x0F4620 (length 1,908 B)
    arm1_start = arm9_rom_off + 0x0F4620
    rom[arm1_start : arm1_start + len(buf_arm1)] = buf_arm1

    # 3. Write Arena 3 into arm9 @ file offset 0x11E390 (length 1,108 B)
    arm2_start = arm9_rom_off + 0x11E390
    rom[arm2_start : arm2_start + len(buf_arm2)] = buf_arm2

    # 4. Update the 189 pointers in ov_008's pointer table @ file offset 0x5EB0
    table_start = o8s + 0x5EB0
    for i, ptr in enumerate(line_ptrs):
        struct.pack_into("<I", rom, table_start + i * 4, ptr)

    return len(line_ptrs)
