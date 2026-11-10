#!/usr/bin/env python3
"""Curated English mappings for special .scs sub-message categories:
  1. Furigana / region place-name banners (BANNER_KANJI_MAP)
  2. Variable-tag sub-messages with {001A}/{001B}/{001E}/{0019} (VAR_SUB_MAP)
  3. Gameplay {0001} choice sub-messages and option labels (CHOICE_SUB_MAP, CHOICE_OPT_MAP)
  4. Sub-messages split across decode_spans records by 0x0011 0x0012 (MERGED_SPLIT_MAP)
  5. Clean overrides for non-{0012} cutscene subtitles & stray JP fixes (CLEAN_SUB_OVERRIDES)
"""

# 1. Place-name banners (keyed by kanji stripped of furigana/tags/spaces)
# Each value is rendered with {0016}{0004} and wrapped to <= 76 px (max 2 lines).
BANNER_KANJI_MAP = {
    "いろは宮": "Iroha\nShrine",
    "イヒカの村": "Ihika\nVillage",
    "ドンデン山": "Mt.\nDonden",
    "ヘビ仙人洞": "Snake\nHermit Cave",
    "三室峠": "Mimuro\nPass",
    "三徳峠": "Mitoku\nPass",
    "三日峠": "Mikka\nPass",
    "三日月峠": "Mikazuki\nPass",
    "三条村": "Sanjo\nVillage",
    "三郎の手塚": "Saburo's\nHand Mound",
    "三郎の胸塚": "Saburo's\nChest Mound",
    "三郎の腹塚": "Saburo's\nBelly Mound",
    "三郎の足塚": "Saburo's\nFoot Mound",
    "両面窟": "Ryomen\nCavern",
    "串の色／景品": "Skewer /\nPrize",
    "串本村": "Kushimoto\nVillage",
    "丹波": "Tanba",
    "丹波の国": "Tanba\nProvince",
    "亀山神社": "Kameyama\nShrine",
    "亀岡村": "Kameoka\nVillage",
    "京": "Kyoto",
    "京の国": "Kyoto\nProvince",
    "京／住宅区": "Kyoto:\nResidences",
    "京／商店区": "Kyoto:\nMarket",
    "京／寺社区": "Kyoto:\nTemples",
    "京／御所区": "Kyoto:\nPalace",
    "京／貧民区": "Kyoto:\nSlums",
    "人魚村": "Mermaid\nVillage",
    "人魚村洞窟": "Mermaid\nCave",
    "伊勢": "Ise",
    "伊勢の国": "Ise\nProvince",
    "伊勢神宮": "Ise\nShrine",
    "伊吹峠": "Ibuki\nPass",
    "伊賀村": "Iga\nVillage",
    "住吉大社": "Sumiyoshi\nShrine",
    "佐々山峠": "Sasayama\nPass",
    "保津峠": "Hozu\nPass",
    "信楽村": "Shigaraki\nVillage",
    "倉敷村": "Kurashiki\nVillage",
    "傘岩仙人洞": "Kasa-iwa\nHermit Cave",
    "六日市村": "Muikaichi\nVillage",
    "六甲峠": "Rokko\nPass",
    "冥府の穴": "Pit of\nHades",
    "出雲": "Izumo",
    "出雲の国": "Izumo\nProvince",
    "出雲大社": "Izumo\nShrine",
    "千年洞": "Millennium\nCave",
    "吉備": "Kibi",
    "吉備の国": "Kibi\nProvince",
    "和歌山城": "Wakayama\nCastle",
    "和歌山町": "Wakayama\nTown",
    "嘆きの谷": "Valley of\nGrief",
    "因幡": "Inaba",
    "因幡の国": "Inaba\nProvince",
    "地獄城": "Hell\nCastle",
    "地獄谷村": "Jigokudani\nVillage",
    "堺村": "Sakai\nVillage",
    "夜久野峠": "Yakuno\nPass",
    "大江山": "Mt. Oe",
    "大江山洞窟": "Mt. Oe\nCave",
    "大津村": "Otsu\nVillage",
    "大草洞": "Okusa\nCave",
    "大霊院": "Dairei-in\nTemple",
    "天の橋立": "Amano-\nhashidate",
    "天狗の庵": "Tengu's\nHermitage",
    "天狗の洞窟": "Tengu\nCave",
    "奈良村": "Nara\nVillage",
    "妙院": "Myoin\nTemple",
    "姫路城": "Himeji\nCastle",
    "姫路町": "Himeji\nTown",
    "宇奈月洞": "Unazuki\nCave",
    "安芸": "Aki",
    "安芸の国": "Aki\nProvince",
    "宝塚村": "Takarazuka\nVillage",
    "密林城": "Jungle\nCastle",
    "富山城": "Toyama\nCastle",
    "富山町": "Toyama\nTown",
    "小郡村": "Ogori\nVillage",
    "尾張": "Owari",
    "尾張の国": "Owari\nProvince",
    "尾道村": "Onomichi\nVillage",
    "尾鷲村": "Owase\nVillage",
    "山城村": "Yamashiro\nVillage",
    "岡山城": "Okayama\nCastle",
    "岡山町": "Okayama\nTown",
    "岩国村": "Iwakuni\nVillage",
    "岸和田村": "Kishiwada\nVillage",
    "左火女山": "Mt.\nSabime",
    "幻夢城": "Genmu\nCastle",
    "広島城": "Hiroshima\nCastle",
    "広島町": "Hiroshima\nTown",
    "弁天塔": "Benten\nTower",
    "弥陀ヶ原洞窟": "Midagahara\nCave",
    "忍の里": "Shinobi\nVillage",
    "志摩村": "Shima\nVillage",
    "戸倉峠": "Tokura\nPass",
    "押水村": "Oshimizu\nVillage",
    "新宮村": "Shingu\nVillage",
    "新潟村": "Niigata\nVillage",
    "暗闇城": "Darkness\nCastle",
    "有馬村": "Arima\nVillage",
    "木ノ葉峠": "Konoha\nPass",
    "朱雀洞": "Suzaku\nCave",
    "村上洞": "Murakami\nCave",
    "松江村": "Matsue\nVillage",
    "松阪城": "Matsusaka\nCastle",
    "松阪町": "Matsusaka\nTown",
    "根来の古墳": "Negoro\nTomb",
    "死野原洞窟": "Shinohara\nCave",
    "比えい山": "Mt. Hiei",
    "法水院": "Housuiin\nTemple",
    "津和野城": "Tsuwano\nCastle",
    "津和野町": "Tsuwano\nTown",
    "浜田村": "Hamada\nVillage",
    "浪華": "Naniwa",
    "浪華の国": "Naniwa\nProvince",
    "海の底": "Ocean\nFloor",
    "清姫村": "Kiyohime\nVillage",
    "火の都": "Capital\nof Fire",
    "火刃村": "Kajin\nVillage",
    "火多": "Hida",
    "火多の国": "Hida\nProvince",
    "火彦山": "Mt.\nHahiko",
    "炭焼小屋": "Charcoal\nHut",
    "熊野村": "Kumano\nVillage",
    "牛首村": "Ushikubi\nVillage",
    "犬山城": "Inuyama\nCastle",
    "犬山町": "Inuyama\nTown",
    "犬神寺": "Inugami\nTemple",
    "猪目村": "Inome\nVillage",
    "玄武洞": "Genbu\nCave",
    "玉造村": "Tamatsukuri\nVillage",
    "生駒峠": "Ikoma\nPass",
    "田代峠": "Tashiro\nPass",
    "白山": "Mt. Haku",
    "白川村": "Shirakawa\nVillage",
    "白橋洞": "Shirahashi\nCave",
    "白浜村": "Shirahama\nVillage",
    "白虎洞": "Byakko\nCave",
    "白銀城": "Hakugin\nCastle",
    "相川村": "Aikawa\nVillage",
    "矢喰城": "Yagui\nCastle",
    "石見の国": "Iwami\nProvince",
    "砂神城": "Sand God\nCastle",
    "神戸村": "Kobe\nVillage",
    "福井村": "Fukui\nVillage",
    "福山村": "Fukuyama\nVillage",
    "福島村": "Fukushima\nVillage",
    "秋芳洞": "Akiyoshi\nCave",
    "秋葉山の滝": "Mt. Akiba\nFalls",
    "秋葉山洞窟": "Mt. Akiba\nCave",
    "立山峠": "Tateyama\nPass",
    "竜神洞": "Dragon God\nCave",
    "箱庭城": "Hakoniwa\nCastle",
    "紀伊": "Kii",
    "紀伊の国": "Kii\nProvince",
    "綾部村": "Ayabe\nVillage",
    "綾鬼城": "Ayaki\nCastle",
    "縁切洞": "Enkiri\nCave",
    "縄文洞": "Jomon\nCave",
    "美女平村": "Bijodaira\nVillage",
    "羽須美村": "Hasumi\nVillage",
    "舌震村": "Shitaburu\nVillage",
    "舞鶴村": "Maizuru\nVillage",
    "船海宮": "Senkaigu",
    "花の御所": "Flower\nPalace",
    "荒神谷古墳": "Kojindani\nTomb",
    "萩村": "Hagi\nVillage",
    "藤原峠": "Fujiwara\nPass",
    "西京洞": "Saikyo\nCave",
    "豊岡村": "Toyooka\nVillage",
    "赤川神社": "Akagawa\nShrine",
    "赤目村": "Akame\nVillage",
    "越中": "Etchu",
    "越中の国": "Etchu\nProvince",
    "越前": "Echizen",
    "越前の国": "Echizen\nProvince",
    "越後の国": "Echigo\nProvince",
    "足下村": "Ashimoto\nVillage",
    "輪島村": "Wajima\nVillage",
    "輪笠村": "Wakasa\nVillage",
    "近江": "Omi",
    "近江の国": "Omi\nProvince",
    "造山洞窟": "Tsukuriyama\nCave",
    "逢坂峠": "Osaka\nPass",
    "逢瀬洞": "Ouse\nCave",
    "金沢城": "Kanazawa\nCastle",
    "金沢町": "Kanazawa\nTown",
    "金谷洞": "Kanaya\nCave",
    "鈴鹿峠": "Suzuka\nPass",
    "鋼鉄城": "Steel\nCastle",
    "錦峠": "Nishiki\nPass",
    "長篠城": "Nagashino\nCastle",
    "長篠町": "Nagashino\nTown",
    "長船村": "Osafune\nVillage",
    "長門": "Nagato",
    "長門の国": "Nagato\nProvince",
    "関所": "Checkpoint",
    "青口神社": "Aokuchi\nShrine",
    "青竜洞": "Seiryu\nCave",
    "鞍馬峠": "Kurama\nPass",
    "須佐の風穴": "Susa\nWind Cave",
    "馬瀬村": "Maze\nVillage",
    "馬鹿野城": "Umashikano\nCastle",
    "高山村": "Takayama\nVillage",
    "高野山": "Mt. Koya",
    "鬼骨城": "Onikotsu\nCastle",
    "魔海城": "Makai\nCastle",
    "鳥取村": "Tottori\nVillage",
    "鹿の子村": "Kanoko\nVillage",
    "鹿野村": "Shikano\nVillage",
    "黄昏洞": "Twilight\nCave",
    "黄泉平": "Yomotsu\nSlope",
    "黒縄洞窟": "Kokujo\nCave",
    "ＨａＨｉ村": "HaHi\nVillage",
}

# 2. Variable-tag sub-messages ({001A}, {001B}, {001E}, {0019})
VAR_SUB_MAP = {
    "\n{001A}へ{001B}歩\u3000{001A}へ{001B}歩と\n表示されている{0012}":
        "It reads: {001B} steps {001A},\n{001B} steps {001A}.{0012}",
    "{0006}ｒｅｉｙａｋｕ＿ｆｌｇ＝{001B}\n":
        "{0006}reiyaku_flg={001B}\n",
    "{000C}{0010}{0082}卍丸は\u3000{001E}両\u3000手に入れた！":
        "{000C}{0010}{0090}Manjimaru obtained {001E} Ryo!",
    "{000C}{0016}{0008}剣の攻撃力が\u3000{001B}になった｜\n{0008}卍丸の体力が\u3000{001B}｜":
        "{000C}{0016}Sword Attack became {001B}!\nManjimaru's HP became {001B}!",
    "{000C}{001A}に\u3000{001B}{0008}のダメージ｜{0012}":
        "{000C}{001A} took {001B} damage!{0012}",
    "{000C}{001A}の体と技の力が\u3000全快した｜{0012}":
        "{000C}{001A}'s HP and TP were fully restored!{0012}",
    "{000C}{001A}の体力が\u3000{001B}回復した｜{0012}":
        "{000C}{001A} recovered {001B} HP!{0012}",
    "{000C}{001A}の体力が\u3000全快した｜{0012}":
        "{000C}{001A}'s HP was fully restored!{0012}",
    "{000C}{001A}の技の力が\u3000全快した｜{0012}":
        "{000C}{001A}'s TP was fully restored!{0012}",
    "{000C}{001A}の攻撃｜{0012}":
        "{000C}{001A}'s attack!{0012}",
    "{000C}{001A}は\u3000シロの首輪を\n墓前に\u3000たむけた{0012}":
        "{000C}{001A} placed Shiro's collar\nbefore the grave.{0012}",
    "{000C}{001A}は\u3000戦えなくなった…{0012}":
        "{000C}{001A} can no longer fight...{0012}",
    "{000C}{001A}は\u3000毒をくらった｜{0012}":
        "{000C}{001A} was poisoned!{0012}",
    "{000C}{001A}は\u3000酸をくらった｜{0012}":
        "{000C}{001A} was hit with acid!{0012}",
    "{000C}{001A}を{001A}枚｜\u3000{001E}両｜\nいってみましょうか♀":
        "{000C}{001A} x{001A} for {001E} Ryo!\nShall we do it!?",
    "{000C}{001A}を\u3000手に入れた｜{0012}":
        "{000C}Obtained {001A}!{0012}",
    "{000C}{001A}をおそう\u3000激しいめまい｜{0012}":
        "{000C}Severe dizziness strikes {001A}!{0012}",
    "{000C}{001B}両分の幸が\u3000あなたに\n訪れますように｜{0012}":
        "{000C}May {001B} Ryo worth of fortune\ncome your way!{0012}",
    "{000C}{001B}本目まで\u3000切ったアルヨ\n残り\u3000あと\u3000{001B}本｜{0012}":
        "{000C}Cut up to root #{001B}!\nOnly {001B} more left!{0012}",
    "{000C}{001E}両で\u3000よろしいですね？":
        "{000C}That will be {001E} Ryo, okay?",
    "{000C}{001E}両分の幸が\u3000あなたに\n訪れますように｜{0012}":
        "{000C}May {001E} Ryo worth of fortune\ncome your way!{0012}",
    "{000C}あなたには\u3000見えなかったでしょうが\n今\u3000{001B}両分の幸が\u3000あなたから\n去りました\u3000ご愁傷さま…{0012}":
        "{000C}You couldn't see it, but {001B} Ryo\nof fortune just left you.\nMy condolences...{0012}",
    "{000C}おめでとうございまーす！\n景品は\u3000{001A}です{0012}":
        "{000C}Congratulations!\nYour prize is {001A}!{0012}",
    "{000C}くどいようですが\n{001A}の巻物でいいんでやんすね？":
        "{000C}Just to be sure, you want\nthe {001A} Scroll, right?",
    "{000C}さらに\u3000鉾先が\n{001A}を\u3000追いつめる｜{0012}":
        "{000C}The spearhead corners {001A}!{0012}",
    "{000C}そ\u3000そ\u3000そうでござるか！\nハハハ\u3000ならば\u3000よいでござるよ\n{001A}様に\u3000伝えておきまする{0012}":
        "{000C}I-Is that so! Hahaha, very well!\nI shall inform {001A}-sama.{0012}",
    "{000C}どこからともなく\u3000無数の\n馬と鹿が現れ\u3000よってたかって\n{001A}を\u3000殴りつけた｜{0012}":
        "{000C}Countless horses and deer appeared\nout of nowhere and beat up\n{001A}!{0012}",
    "{000C}ほぉー｜\u3000これからは\u3000{001A}かぁ｜\nで\u3000いかほど\u3000お買い上げで？\n\u3000{0001}一枚\u3000\u3000{0001}十枚\u3000\u3000{0001}百枚":
        "{000C}Aha, {001A} it is!\nHow many will you buy?\n   {0001}1   {0001}10   {0001}100",
    "{000C}また\u3000{001A}へ\u3000お寄りの際は\nお気軽にご利用くださいまし{0012}":
        "{000C}Please visit us again whenever\nyou come to {001A}!{0012}",
    "{000C}デューク・ペペの\u3000機械の手が\n{001A}の若い体に\u3000伸びた｜{0012}":
        "{000C}Duke Pepe's mechanical hand\nreached for {001A}!{0012}",
    "{000C}ヨミは\u3000{001A}の名を\u3000呼んだ……{0012}":
        "{000C}Yomi called {001A}'s name...{0012}",
    "{000C}ヨミは\u3000{001A}を\u3000手招きした……{0012}":
        "{000C}Yomi beckoned to {001A}...{0012}",
    "{000C}ヨミは\u3000{001A}を見ている……{0012}":
        "{000C}Yomi is staring at {001A}...{0012}",
    "{000C}今なら\u3000{001A}は\u3000たったの\n{001E}両…\u3000いいんですかね？":
        "{000C}Right now {001A} is only\n{001E} Ryo... Is that okay?",
    "{000C}卍丸は\u3000{001A}の額に\n記念スタンプを\u3000ペタンと押した{0012}":
        "{000C}Manjimaru stamped the commemorative\nstamp onto {001A}'s forehead.{0012}",
    "{000C}卍丸は\u3000{001E}両\u3000手に入れた{0012}":
        "{000C}Manjimaru obtained {001E} Ryo.{0012}",
    "{000C}叫喚の獅子は\u3000{001A}の\nふところに\u3000飛び込んだ｜{0012}":
        "{000C}The Lion of Kyokan lunged\nstraight at {001A}!{0012}",
    "{000C}本当に\u3000{001A}の巻物でいいんじゃな？":
        "{000C}Are you sure you want\nthe {001A} Scroll?",
    "{000C}残りは\u3000あと{001B}体{0012}":
        "{000C}{001B} remaining.{0012}",
    "{000C}毒針法師の\u3000髪の毛が\n{001A}をねらって\u3000飛んで来た｜{0012}":
        "{000C}Poison Needle Monk's hair flew\nstraight at {001A}!{0012}",
    "{000C}百鬼王の\u3000六本の腕が\n{001A}を追う｜{0012}":
        "{000C}Hyakki-Oh's six arms\nchase after {001A}!{0012}",
    "{000C}百鬼王は\u3000{001A}に\nつかみかかった｜{0012}":
        "{000C}Hyakki-Oh lunged to grab\n{001A}!{0012}",
    "{000C}肉助は\u3000隠し持っていた\n{001A}を\u3000すすった｜{0012}":
        "{000C}Nikusuke slurped the hidden\n{001A}!{0012}",
    "{000C}肉助は\u3000隠し持っていた\n{001A}を\u3000むしゃぶった｜{0012}":
        "{000C}Nikusuke devoured the hidden\n{001A}!{0012}",
    "{000C}阿鼻の獅子は\u3000{001A}の\nふところに\u3000飛び込んだ｜{0012}":
        "{000C}The Lion of Abi lunged\nstraight at {001A}!{0012}",
    "{000C}魔将パジャラは\n{001A}に向って\u3000優しく笑った…{0012}":
        "{000C}Demon General Pajara smiled\ngently at {001A}...{0012}",
    "{0010}{0000}\n\u3000塩\u3000\u3000{001B}\u3000両\u3000{001B}\u3000両\u3000{001B}\u3000両\n{0010}{0000}\n\u3000{0001}買う\u3000\u3000{0001}売る\u3000\u3000{0001}やめる\u3000\u3000{0001}説明":
        "{0010}{0000}\n Salt {001B}R {001B}R {001B}R\n{0010}{0000}\n   {0001}Buy   {0001}Sell   {0001}Exit   {0001}Info",
    "{0010}{0000}\n\u3000米\u3000\u3000{001B}\u3000両\u3000{001B}\u3000両\u3000{001B}\u3000両":
        "{0010}{0000}\n Rice {001B}R {001B}R {001B}R",
    "{0010}{0000}\n\u3000豆\u3000\u3000{001B}\u3000両\u3000{001B}\u3000両\u3000{001B}\u3000両":
        "{0010}{0000}\n Bean {001B}R {001B}R {001B}R",
    "{0010}{0000}\n\u3000麦\u3000\u3000{001B}\u3000両\u3000{001B}\u3000両\u3000{001B}\u3000両":
        "{0010}{0000}\n Wheat {001B}R {001B}R {001B}R",
    "{0010}{0082}{000C}{001A}の巻物に\u3000使う技が\n１\u3000減った｜":
        "{0010}{0090}{000C}The TP cost of the {001A}\nScroll decreased by 1!",
    "{0010}{0082}{000C}{001A}の巻物を\u3000手に入れた｜":
        "{0010}{0090}{000C}Obtained the {001A} Scroll!",
    "{0010}{0082}{001A}の巻物に\u3000使う技が\n１\u3000減った｜":
        "{0010}{0090}The TP cost of the {001A}\nScroll decreased by 1!",
    "{001A}\u3000エンカウント４倍または{0006}１／２":
        "{001A}: Encounter rate x4 or 1/2",
    "{001A}\u3000毒と酸\n":
        "{001A}: Poison and Acid\n",
    "{001A}\u3000術を封じる\n":
        "{001A}: Seals spells\n",
    "{001A}\u3000青松と同じ効果\n":
        "{001A}: Same effect as Green Pine\n",
    "{001A}\u3000ＨＰ・ＭＰが最大値\u3000または１\n":
        "{001A}: HP & TP to Max or 1\n",
    "{001A}\u3000ＭＡＸ・ＨＰ／２を加算\n":
        "{001A}: Adds Max HP / 2\n",
    "{001A}\u3000ＭＡＸ・ＭＰ／２を加算\n":
        "{001A}: Adds Max TP / 2\n",
    "{001A}\u3000ＭＰ・ＨＰの{0006}１／４{0004}を増または減\n":
        "{001A}: +/- 1/4 of HP & TP\n",
    "{001A}の巻物を\u3000なくしたようじゃな\nしかし\u3000巻物袋がいっぱいでは\nお渡しすることは\u3000できんわなぁ…{0012}":
        "You seem to have lost the {001A}\nScroll, but your scroll bag is\ntoo full for me to give it to you...{0012}",
    "{001A}の巻物を\u3000なくしたようじゃな\nしょうがない奴じゃのぉ…\nほれっ！\u3000{001A}の巻物じゃ！{0012}":
        "You lost the {001A} Scroll?\nWhat a hopeless case...\nHere! The {001A} Scroll!{0012}",
    "{001A}の巻物を\u3000選ぶとはな……\nあんた\u3000なかなか\u3000見どころ\u3000あるよ！\nさすがは\u3000火の勇者じゃ！{0012}":
        "Choosing the {001A} Scroll...\nYou've got quite an eye!\nWorthy of the Fire Hero!{0012}",
    "{001A}の術でいいかい？":
        "You want the {001A} spell?",
    "{001A}の術でいいかい？\n":
        "You want the {001A} spell?\n",
    "{001A}は\u3000{001A}で\n扉を開けた！{0012}":
        "{001A} unlocked the door\nwith {001A}!{0012}",
    "{001A}は\u3000{001A}を\n台座に\u3000はめ込もうとしたが\nうまく合わなかった{0012}":
        "{001A} tried to fit {001A}\ninto the pedestal, but it\ndidn't fit.{0012}",
    "{001A}は\u3000{001A}を\n台座に\u3000はめ込んだ！{0012}":
        "{001A} fitted {001A}\ninto the pedestal!{0012}",
    "{001A}は\u3000{001A}を\n墓石の上にていねいに置いた{0012}":
        "{001A} carefully placed\n{001A} on the gravestone.{0012}",
    "{001A}は\u3000{001A}を\n鍵穴に差し込んだ！":
        "{001A} inserted {001A}\ninto the keyhole!",
    "{001A}は\u3000ガレキの前に\n爆薬を仕掛けた{0012}":
        "{001A} set the explosives\nin front of the rubble.{0012}",
    "{001A}は\u3000反魂丹を\n電二郎の口に押し込んだ…{0012}":
        "{001A} placed the Hangontan\ninto Denjiro's mouth...{0012}",
    "{001A}は\u3000四水の鏡を\n石像に向けた！{0012}":
        "{001A} held the Four Waters\nMirror toward the stone statue!{0012}",
    "{001A}は\u3000太陽に向かって\n電子の手旗を振った{0012}":
        "{001A} waved the Electronic\nFlag toward the sun.{0012}",
    "{001A}は\u3000山門のカギで\n門を開けた！{0012}":
        "{001A} unlocked the gate\nwith the Temple Gate Key!{0012}",
    "{001A}は\u3000石像の指に\n嘆きの指輪をはめた！{0012}":
        "{001A} placed the Ring of Grief\non the stone statue's finger!{0012}",
    "{001A}は\u3000石川のカギで\n扉を開けた！{0012}":
        "{001A} unlocked the door\nwith Ishikawa's Key!{0012}",
    "{001A}は\u3000砂のカギで\n門を開けた！{0012}":
        "{001A} unlocked the gate\nwith the Sand Key!{0012}",
    "{001A}は\u3000空に向かって\n天章の笛を吹いた！{0012}":
        "{001A} blew the Tensho Flute\ntoward the sky!{0012}",
    "{001A}は\u3000竜の勾玉に手をかざした{0012}":
        "{001A} held a hand over\nthe Dragon Magatama.{0012}",
    "{001A}は\u3000電二磁石の文字盤を見た":
        "{001A} checked the dial\nof the Denji Compass.",
    "{001A}は「{001A}」を会得した{0012}":
        "{001A} learned \"{001A}\"!{0012}",
    "{001A}は青葉の笛をふいた{0012}":
        "{001A} played the Green Leaf Flute.{0012}",
    "{001A}へ\u3000よく\u3000お越しを！{0012}":
        "Welcome to {001A}!{0012}",
    "{001A}を\u3000渡すことは\u3000できない{0012}":
        "Cannot hand over {001A}.{0012}",
    "{001E}両\u3000見つけた｜{0012}":
        "Found {001E} Ryo!{0012}",
    "{001E}両を\u3000見つけた！{0012}":
        "Found {001E} Ryo!{0012}",
    "{001E}両を\u3000見つけた｜{0012}":
        "Found {001E} Ryo!{0012}",
    "{001E}両を見つけた！{0012}":
        "Found {001E} Ryo!{0012}",
    "「{001A}\u3000{001A}」\nこれっきゃ\u3000ねぇよ！\nわかったな{0012}":
        "\"{001A} {001A}\"!\nThat's the only one!\nGot it?{0012}",
    "あれま｜\u3000お客様の今年の運は\n{001E}両がないばかりに…{0012}":
        "Oh dear! Your luck this year is\ngone just for lack of {001E} Ryo...{0012}",
    "いい初夢が\u3000{001E}両で見られますよ":
        "You can see a good New Year's\ndream for {001E} Ryo!",
    "いらっしゃいませ！\n一泊\u3000{001E}両でございます{0012}":
        "Welcome!\nIt is {001E} Ryo per night.{0012}",
    "ここは{001A}です\u3000何かごようですか？\n":
        "This is {001A}. How can I help you?\n",
    "しかし{001A}はころげ落ちた\n{001A}はあわてて拾いあげた{0012}":
        "But {001A} rolled off!\n{001A} hurriedly picked it up.{0012}",
    "ヅガーーーンと\u3000{001A}でいいんだな？":
        "Kaboom! You want {001A}, right?",
    "一泊\u3000{001E}両じゃが\n泊まっていかれるかのぉ？\n":
        "It's {001E} Ryo for a night.\nWill you be staying?\n",
    "一泊\u3000{001E}両だ｜\n休んでくだろ？\n":
        "It's {001E} Ryo a night!\nYou're resting here, right?\n",
    "一泊\u3000{001E}両でございます\n旅の疲れを当宿屋で\u3000おとりください\n":
        "It is {001E} Ryo per night.\nPlease rest from your journey here.\n",
    "一泊\u3000{001E}両でございます\u3000今晩は\n温泉で旅のアカを\u3000落としませんか？\n":
        "It is {001E} Ryo per night.\nWash off your travel fatigue tonight?\n",
    "卍丸は\u3000{001E}両\u3000手に入れた{0012}":
        "Manjimaru obtained {001E} Ryo.{0012}",
    "卍丸は「{001A}」を手にいれた。":
        "Manjimaru obtained \"{001A}\".",
    "本当に\u3000{001A}の術で\u3000いいのかい？":
        "Are you sure you want the\n{001A} spell?",
    "決まりで\u3000旅のかたからは\u3000{001E}両\nいただいとります\u3000お泊りですか？\n":
        "By rule, we charge travelers\n{001E} Ryo. Will you stay?\n",
    "素泊りで\u3000{001E}両ですが\nご利用になられますか？\n":
        "It's {001E} Ryo for a room.\nWould you like to stay?\n",
}

# 3. Gameplay {0001} choice sub-messages (full sub-message -> clean EN <= 3 lines)
CHOICE_SUB_MAP = {
    "\n{0001}花を登録\u3000\u3000{0001}調合指定\u3000\u3000{0001}さよなら":
        "\n   {0001}Register   {0001}Blend   {0001}Bye",
    "\n\u3000{0001}ＹＥＳ\u3000\u3000{0001}ＮＯ":
        "\n   {0001}YES   {0001}NO",
    "{0001}初夢／記録\n{0001}初夢のみ\u3000\n{0001}記録のみ\u3000\n{0001}やめる\u3000\u3000":
        "   {0001}Dream & Save   {0001}Dream Only\n   {0001}Save Only      {0001}Cancel",
    "{0001}宿泊のみ\u3000\n{0001}やめる\u3000\u3000":
        "   {0001}Stay Only\n   {0001}Cancel",
    "{0001}宿泊／記録\n{0001}やめる\u3000\u3000":
        "   {0001}Stay & Save\n   {0001}Cancel",
    "{0001}宿泊／記録\n{0001}宿泊のみ\n{0001}記録のみ\n{0001}やめる":
        "   {0001}Stay & Save   {0001}Stay Only\n   {0001}Save Only     {0001}Cancel",
    "{0001}宿泊／記録\n{0001}宿泊のみ\u3000\n{0001}記録のみ\u3000\n{0001}やめる\u3000\u3000":
        "   {0001}Stay & Save   {0001}Stay Only\n   {0001}Save Only     {0001}Cancel",
    "{0001}火多\u3000{0001}尾張\u3000{0001}伊勢\u3000{0001}紀伊\u3000{0001}京\u3000\u3000{0001}近江\n{0001}越前\u3000{0001}越中\u3000{0001}越後\u3000{0001}因幡\u3000{0001}出雲\u3000{0001}石見\n{0001}丹波\u3000{0001}浪華\u3000{0001}吉備\u3000{0001}安芸\u3000{0001}長門\u3000{0001}戻る":
        "  {0001}Hida  {0001}Owari  {0001}Ise  {0001}Kii  {0001}Kyo  {0001}Omi\n  {0001}Echz  {0001}Etch  {0001}Echg  {0001}Inab  {0001}Izum  {0001}Iwam\n  {0001}Tanb  {0001}Nani  {0001}Kibi  {0001}Aki  {0001}Naga  {0001}Back",
    "{0001}０両\u3000{0001}一両\u3000{0001}十両\u3000{0001}百両\u3000{0001}千両":
        "   {0001}0   {0001}1   {0001}10   {0001}100   {0001}1000",
    "{000C}で\u3000どれを\u3000お買い上げで？\n\u3000{0001}米\u3000\u3000{0001}麦\u3000\u3000{0001}豆\u3000\u3000{0001}塩":
        "{000C}Which one will you buy?\n   {0001}Rice   {0001}Wheat   {0001}Beans   {0001}Salt",
    "{000C}どの精霊機の説明を\u3000聞きますか？\n\u3000{0001}波\u3000{0001}潮\u3000{0001}風":
        "{000C}Which Spirit Engine shall I explain?\n   {0001}Wave   {0001}Tide   {0001}Wind",
    "{000C}ほぉー｜\u3000これからは\u3000{001A}かぁ｜\nで\u3000いかほど\u3000お買い上げで？\n\u3000{0001}一枚\u3000\u3000{0001}十枚\u3000\u3000{0001}百枚":
        "{000C}Aha, {001A} it is!\nHow many will you buy?\n   {0001}1   {0001}10   {0001}100",
    "{000C}何本目まで切るか？\n{0001}１\u3000{0001}２\u3000{0001}３\u3000{0001}４\u3000{0001}５\u3000{0001}６\u3000{0001}７":
        "{000C}Cut up to which root?\n   {0001}1   {0001}2   {0001}3   {0001}4   {0001}5   {0001}6   {0001}7",
    "{000C}何番か\u3000選んでちょうだい\n\u3000{0001}壱\u3000{0001}弐\u3000{0001}参\u3000{0001}四\u3000{0001}五\u3000{0001}六\u3000{0001}七\u3000{0001}八":
        "{000C}Please pick a number!\n  {0001}1  {0001}2  {0001}3  {0001}4  {0001}5  {0001}6  {0001}7  {0001}8",
    "{000C}卍丸殿！\u3000三太夫様の中で\n恋人にするとしたら\u3000どの方ですか？\n\u3000{0001}花火\u3000\u3000{0001}まつり\u3000{0001}みこし":
        "{000C}Manjimaru! Which of the Sandayu\nwould you choose as a lover?\n   {0001}Hanabi   {0001}Matsuri   {0001}Mikoshi",
    "{000C}山に彫る\u3000俺様の顔なんだがよ｜\n{0011}{001E}正面と\u3000{0011}{000F}横向きと\u3000{0011}{0014}{0010}{0084}どっちがいいかな？\n{0001}正面\u3000{0001}横顔":
        "{000C}For my face carved on the mountain,\nis front or profile better?\n   {0001}Front   {0001}Profile",
    "{000C}誰を\u3000変更する？\n{0001}カブキ\u3000{0001}極\u3000楽\u3000{0001}\u3000絹\u3000\u3000{0001}シ\u3000ロ\u3000{0001}ホテイ":
        "{000C}Change whom?\n {0001}Kabuki {0001}Gokuraku {0001}Kinu {0001}Shiro {0001}Hotei",
    "{000C}Ｈｅｌｌｏ！\u3000預かり？\u3000引きだし？\nそれとも\u3000私に\u3000何か\u3000ご用かしら？\n\u3000{0001}いいえ\u3000{0001}はい\u3000":
        "{000C}Hello! Deposit or withdrawal?\nOr did you need something from me?\n   {0001}No   {0001}Yes",
    "あまり\u3000足しには\u3000なんねぇがよぉ…\n今やるかい？\u3000後にするかい？\n{0001}今すぐやる\u3000\u3000{0001}少し考えて":
        "It won't help much, though...\nDo it now, or save it for later?\n   {0001}Do it now   {0001}Think first",
    "さあ\u3000どっちじゃな？\n{0001}１\u3000\u3000{0001}２":
        "Now, which one will it be?\n   {0001}1   {0001}2",
    "その恋文\u3000今すぐ\u3000お捨てなさい！\nろくなこと\u3000起きないからね\n{0001}捨てる\u3000\u3000{0001}捨てない":
        "Throw that love letter away now!\nNothing good will come of it!\n   {0001}Throw away   {0001}Keep it",
    "たった\u3000１だけだと\u3000馬鹿にするなよ！\nすぐにやるかい？\u3000またにするかい？\n{0001}すぐにやる\u3000{0001}またにする":
        "Don't mock it for being just 1!\nDo it right now, or another time?\n   {0001}Right now   {0001}Another time",
    "どちらの\u3000カブキを\u3000斬りますか？\n{0001}左のカブキ\u3000{0001}右のカブキ":
        "Which Kabuki will you strike?\n   {0001}Left Kabuki   {0001}Right Kabuki",
    "どっちの\u3000コースを選ぶかね？\n{0001}極楽巡り\u3000\u3000{0001}地獄巡り\u3000\u3000{0001}乗らねぇ":
        "Which course would you like?\n   {0001}Paradise   {0001}Hell Tour   {0001}Don't ride",
    "どのかたが\u3000卍丸さんの本命\nなんですかねぇ……？\n\u3000{0001}花火\u3000\u3000{0001}まつり\u3000{0001}みこし\u3000{0001}別に…":
        "Which one is Manjimaru-san's\ntrue sweetheart...?\n   {0001}Hanabi   {0001}Matsuri   {0001}Mikoshi   {0001}None",
    "どーも\u3000どーも\u3000どーも\nイラハリ\u3000でーす！\u3000はい\u3000プリーズ？\n\u3000{0001}ＯＫ\u3000{0001}ＮＯ":
        "Hello, hello, hello!\nI'm Irahari! Yes, please?\n   {0001}OK   {0001}NO",
    "ぷりいーず\u3000ちっぷ！\n{0001}一両\u3000{0001}十両\u3000{0001}百両\u3000{0001}千両":
        "Please, a tip!\n   {0001}1 Ryo   {0001}10 Ryo   {0001}100 Ryo   {0001}1000 Ryo",
    "もし\u3000あたしが\u3000豚になったら\nどう\u3000責任とってくれるのよ♀\n\u3000{0001}結婚する\u3000{0001}食べる\u3000\u3000{0001}逃げる":
        "If I turn into a pig, how will you\ntake responsibility!?\n   {0001}Marry   {0001}Eat   {0001}Run away",
    "エビス丸\u3000ブラザーの人\u3000ホテイ丸\nドゥ\u3000ユー\u3000ノー\u3000ホテイ丸？\n\u3000{0001}Ｙｅｓ\u3000{0001}Ｎｏ":
        "Ebisumaru's brother is Hoteimaru!\nDo you know Hoteimaru?\n   {0001}Yes   {0001}No",
    "ヅガーーーンと\u3000１だけな！\n今やるかい？\u3000後にするかい？\n{0001}今\u3000{0001}後":
        "Kaboom, just by 1!\nDo it now, or later?\n   {0001}Now   {0001}Later",
    "今すぐ\u3000やるかね？\u3000後でやるかね？\n\u3000{0001}今すぐ\u3000\u3000{0001}後で":
        "Will you do it now, or later?\n   {0001}Right now   {0001}Later",
    "今すぐ\u3000やるか？\u3000それとも\n少し考えてからにするか？\u3000どうする？\n{0001}今すぐやる\u3000\u3000{0001}少し考えて":
        "Do it now, or think it over\na bit first? What'll you do?\n   {0001}Do it now   {0001}Think first",
    "今すぐに\u3000いたしやすかねぇ？\nそれとも\u3000後に\u3000いたしやすかねぇ？\n\u3000{0001}今すぐ\u3000\u3000{0001}後で":
        "Shall we do it right now,\nor save it for later?\n   {0001}Right now   {0001}Later",
    "俺様の道具屋に\u3000何か用かい？\n用がないなら\u3000とっとと失せな！\n{0001}耐える\u3000{0001}逃げる\u3000{0001}攻撃｜":
        "Got business at my item shop?\nIf not, get lost right now!\n   {0001}Endure   {0001}Run   {0001}Attack!",
    "俺様の道具屋に\u3000何か用かい？\n用がないなら\u3000とっとと失せな！\n\u3000{0001}耐える\u3000\u3000{0001}逃げる\u3000\u3000{0001}攻撃｜":
        "Got business at my item shop?\nIf not, get lost right now!\n   {0001}Endure   {0001}Run   {0001}Attack!",
    "唇と唇を引っつけて\u3000あんたに\n人工呼吸をしてたのは\u3000誰だと思う？\n\u3000{0001}花火\u3000\u3000{0001}まつり\u3000{0001}みこし\u3000{0001}あたし":
        "Who do you think gave you\nmouth-to-mouth resuscitation?\n   {0001}Hanabi   {0001}Matsuri   {0001}Mikoshi   {0001}Me",
    "心当たりは\u3000ねぇか？\u3000卍丸さん！\n{0001}ある\u3000{0001}ねぇ":
        "Anything ring a bell, Manjimaru?\n   {0001}Yes   {0001}Nope",
    "福引串団子を\u3000食べまくって\nお宝を\u3000当てまくろーーーぉ｜\n\u3000{0001}買う｜\u3000{0001}やめた\u3000{0001}説明":
        "Eat lots of Lucky Skewer Dango\nand win big prizes!\n   {0001}Buy!   {0001}Quit   {0001}Info",
    # Flower blending & dango prize items & tabloid headlines:
    "{0010}{0000}{0008}{0001}{0008}{0015}{0000}やめる": "{0010}{0000}{0008}{0001}{0008}{0015}{0000}Cancel",
    "{0010}{0000}{0008}{0001}{0008}{0015}{0000}血車草\n": "{0010}{0000}{0008}{0001}{0008}{0015}{0000}Bloodwheel Herb\n",
    "{0010}{0000}{0008}{0001}{0008}{0015}{0000}闇牡丹\n": "{0010}{0000}{0008}{0001}{0008}{0015}{0000}Dark Peony\n",
    "{0010}{0000}{0008}{0001}{0008}{0015}{0000}雪割桜\n": "{0010}{0000}{0008}{0001}{0008}{0015}{0000}Snowdrop Sakura\n",
    "{0010}{0000}{0008}{0001}{0008}{0015}{0001}血車草\n": "{0010}{0000}{0008}{0001}{0008}{0015}{0001}Bloodwheel Herb\n",
    "{0010}{0000}{0008}{0001}{0008}{0015}{0001}闇牡丹\n": "{0010}{0000}{0008}{0001}{0008}{0015}{0001}Dark Peony\n",
    "{0010}{0000}{0008}{0001}{0008}{0015}{0001}雪割桜\n": "{0010}{0000}{0008}{0001}{0008}{0015}{0001}Snowdrop Sakura\n",
    "{0010}{0000}{0008}{0001}{0015}{0000}人魚百合\n": "{0010}{0000}{0008}{0001}{0015}{0000}Mermaid Lily\n",
    "{0010}{0000}{0008}{0001}{0015}{0000}越の金梅\n": "{0010}{0000}{0008}{0001}{0015}{0000}Koshi Gold Plum\n",
    "{0010}{0000}{0008}{0001}{0015}{0001}人魚百合\n": "{0010}{0000}{0008}{0001}{0015}{0001}Mermaid Lily\n",
    "{0010}{0000}{0008}{0001}{0015}{0001}越の金梅\n": "{0010}{0000}{0008}{0001}{0015}{0001}Koshi Gold Plum\n",
    "{0015}{0000}{0006}\u3000{0004}{0001}白／福引串団子\n": "{0015}{0000}{0006} {0004}{0001}White / Lucky Dango\n",
    "{0015}{0000}{0006}\u3000{0004}{0001}竹／店員の笑顔": "{0015}{0000}{0006} {0004}{0001}Bamboo / Clerk's Smile",
    "{0015}{0000}{0006}\u3000{0004}{0001}紺／養老丸\n": "{0015}{0000}{0006} {0004}{0001}Navy / Yoro Pill\n",
    "{0015}{0000}{0006}\u3000{0004}{0001}緑／百命丸\n": "{0015}{0000}{0006} {0004}{0001}Green / Hyakumei Pill\n",
    "{0015}{0000}{0006}\u3000{0004}{0001}赤／岩戸の盾\n": "{0015}{0000}{0006} {0004}{0001}Red / Iwato Shield\n",
    "{0015}{0000}{0006}\u3000{0004}{0001}金／回天丹\n": "{0015}{0000}{0006} {0004}{0001}Gold / Kaitentan\n",
    "{0015}{0000}{0006}\u3000{0004}{0001}銀／七福の玉\n": "{0015}{0000}{0006} {0004}{0001}Silver / Shichifuku Orb\n",
    "{0015}{0000}{0006}\u3000{0004}{0001}黒／甘露丸\n": "{0015}{0000}{0006} {0004}{0001}Black / Kanro Pill\n",
    "{0015}{0001}{0006}\u3000{0004}{0001}白／福引串団子\n": "{0015}{0001}{0006} {0004}{0001}White / Lucky Dango\n",
    "{0015}{0001}{0006}\u3000{0004}{0001}竹／店員の笑顔": "{0015}{0001}{0006} {0004}{0001}Bamboo / Clerk's Smile",
    "{0015}{0001}{0006}\u3000{0004}{0001}紺／養老丸\n": "{0015}{0001}{0006} {0004}{0001}Navy / Yoro Pill\n",
    "{0015}{0001}{0006}\u3000{0004}{0001}緑／百命丸\n": "{0015}{0001}{0006} {0004}{0001}Green / Hyakumei Pill\n",
    "{0015}{0001}{0006}\u3000{0004}{0001}赤／岩戸の盾\n": "{0015}{0001}{0006} {0004}{0001}Red / Iwato Shield\n",
    "{0015}{0001}{0006}\u3000{0004}{0001}金／回天丹\n": "{0015}{0001}{0006} {0004}{0001}Gold / Kaitentan\n",
    "{0015}{0001}{0006}\u3000{0004}{0001}銀／七福の玉\n": "{0015}{0001}{0006} {0004}{0001}Silver / Shichifuku Orb\n",
    "{0015}{0001}{0006}\u3000{0004}{0001}黒／甘露丸\n": "{0015}{0001}{0006} {0004}{0001}Black / Kanro Pill\n",
    "\u3000{0001}丹波": "   {0001}Tanba",
    "\u3000{0001}京\u3000": "   {0001}Kyoto",
    "\u3000{0001}伊勢": "   {0001}Ise",
    "\u3000{0001}出雲": "   {0001}Izumo",
    "\u3000{0001}吉備": "   {0001}Kibi",
    "\u3000{0001}因幡": "   {0001}Inaba",
    "\u3000{0001}安芸": "   {0001}Aki",
    "\u3000{0001}尾張": "   {0001}Owari",
    "\u3000{0001}浪華": "   {0001}Naniwa",
    "\u3000{0001}石見": "   {0001}Iwami",
    "\u3000{0001}紀伊": "   {0001}Kii",
    "\u3000{0001}越中": "   {0001}Etchu",
    "\u3000{0001}越前": "   {0001}Echizen",
    "\u3000{0001}越後": "   {0001}Echigo",
    "\u3000{0001}近江": "   {0001}Omi",
    "\u3000{0001}長門": "   {0001}Nagato",
    # Tabloid news shop menus (we2/veec.scs, we3/veec.scs, we4/veec.scs):
    "{0001}ニーハオ｜\u3000\u3000\u3000{0006}９０\u3000{0004}":
        "  {0001}Ni Hao! {0006}90 {0004}",
    "{0001}人面花出現｜\u3000\u3000{0006}９０\u3000{0004}{0001}密会発覚｜\u3000\u3000\u3000{0006}９０{0004}\n{0001}速報｜\u3000鬼骨城\u3000{0006}９０\u3000{0004}{0001}日本初上陸｜\u3000\u3000{0006}９０{0004}\n":
        "  {0001}Face Flower! {0006}90 {0004}  {0001}Secret Tryst {0006}90{0004}\n  {0001}Onikotsu News {0006}90 {0004}  {0001}Japan Debut! {0006}90{0004}\n",
    "{0001}人面花出現｜\u3000\u3000{0006}９０\u3000{0004}{0001}密会発覚｜\u3000\u3000\u3000{0006}９０{0004}\n{0001}速報｜\u3000鬼骨城\u3000{0006}９０\u3000{0004}{0001}日本初上陸｜\u3000\u3000{0006}９０{0004}\n{0001}ニーハオ｜\u3000\u3000\u3000{0006}９０\u3000{0004}{0001}狂乱の脱獄\u3000\u3000\u3000{0006}９０{0004}\n{0001}愛の逃避行\u3000\u3000\u3000{0006}９０\u3000{0004}":
        "  {0001}Face Flower! {0006}90 {0004}  {0001}Secret Tryst {0006}90{0004}\n  {0001}Onikotsu News {0006}90 {0004}  {0001}Japan Debut! {0006}90{0004}\n  {0001}Ni Hao! {0006}90 {0004}  {0001}Mad Jailbreak {0006}90{0004}\n  {0001}Love Elopement {0006}90 {0004}",
    "{0001}人面花出現｜\u3000\u3000{0006}９０\u3000{0004}{0001}密会発覚｜\u3000\u3000\u3000{0006}９０{0004}\n{0001}速報｜\u3000鬼骨城\u3000{0006}９０\u3000{0004}{0001}日本初上陸｜\u3000\u3000{0006}９０{0004}\n{0001}ニーハオ｜\u3000\u3000\u3000{0006}９０\u3000{0004}{0001}狂乱の脱獄\u3000\u3000\u3000{0006}９０{0004}\n{0001}愛の逃避行\u3000\u3000\u3000{0006}９０\u3000{0004}{0001}血塗られた\u3000\u3000\u3000{0006}９０{0004}\n{0001}電撃離婚｜\u3000\u3000\u3000{0006}９０\u3000{0004}{0001}爆笑マントー\u3000\u3000{0006}９０{0004}\n{0001}犬肉食った｜\u3000\u3000{0006}９０\u3000{0004}{0001}奇跡の生還\u3000\u3000\u3000{0006}９０{0004}\n{0001}怪力世界一！\u3000\u3000{0006}９０\u3000{0004}":
        "  {0001}Face Flower! {0006}90 {0004}  {0001}Secret Tryst {0006}90{0004}\n  {0001}Onikotsu News {0006}90 {0004}  {0001}Japan Debut! {0006}90{0004}\n  {0001}Ni Hao! {0006}90 {0004}  {0001}Mad Jailbreak {0006}90{0004}\n  {0001}Love Elope {0006}90 {0004}  {0001}Bloodstained {0006}90{0004}\n  {0001}Shock Divorce {0006}90 {0004}  {0001}Funny Manto {0006}90{0004}\n  {0001}Dog Meat?! {0006}90 {0004}  {0001}Miracle Return {0006}90{0004}\n  {0001}Strongest! {0006}90 {0004}",
    "{0001}奇跡の生還\u3000\u3000\u3000{0006}９０{0004}\n": "  {0001}Miracle Return {0006}90{0004}\n",
    "{0001}愛の逃避行\u3000\u3000\u3000{0006}９０\u3000{0004}": "  {0001}Love Elopement {0006}90 {0004}",
    "{0001}泥沼愛憎劇\u3000\u3000\u3000{0006}９０{0004}": "  {0001}Love-Hate Drama {0006}90{0004}",
    "{0001}爆笑マントー\u3000\u3000{0006}９０{0004}\n": "  {0001}Funny Manto {0006}90{0004}\n",
    "{0001}犬肉食った｜\u3000\u3000{0006}９０\u3000{0004}": "  {0001}Dog Meat?! {0006}90 {0004}",
    "{0001}狂乱の脱獄\u3000\u3000\u3000{0006}９０{0004}\n": "  {0001}Mad Jailbreak {0006}90{0004}\n",
    "{0001}禁断の愛？\u3000\u3000\u3000{0006}９０{0004}\n": "  {0001}Forbidden Love? {0006}90{0004}\n",
    "{0001}血塗られた\u3000\u3000\u3000{0006}９０{0004}\n": "  {0001}Bloodstained {0006}90{0004}\n",
    "{0001}電撃離婚｜\u3000\u3000\u3000{0006}９０\u3000{0004}": "  {0001}Shock Divorce! {0006}90 {0004}",
    "{0001}ＵＦＯ飛来\u3000\u3000\u3000{0006}９０\u3000{0004}": "  {0001}UFO Sighting! {0006}90 {0004}",
}

# 4. The 15 sub-messages split across msg[i] and msg[i+1] by 0x0011 0x0012 (pause 18 frames)
# Keyed by (file, msg_i), value is the complete formatted sub-message for msg_i's tail
# (and msg_{i+1}'s first sub-message before its first {0000} becomes "").
MERGED_SPLIT_MAP = {
    ("b20/b20.scs", 2):
        "{000C}{0010}{0008}For that sake, I've endured hellish\ntraining every single day until today!{0012}",
    ("end0/end0.scs", 0):
        "{000C}{0010}{0090}I love Zipangu so much!\nAnd to all the people of this land:\nI love you!{0011}{0090}",
    ("end0/end0.scs", 1):
        "{000C}{0010}{0090}I want to become friends with\neveryone, every single one of you!{0011}{0090}",
    ("end0/end0.scs", 2):
        "{000C}{0010}{0090}I want to know more about Zipangu!\nSomeday, somewhere, see you again!{0011}{00B0}",
    ("end3/end3.scs", 0):
        "{000C}{0010}{0090}And you know, Mother is so good\nat sewing!{0011}{0090}",
    ("end3/end3.scs", 1):
        "{000C}{0010}{0090}I'm going to have Mother teach me\nhow to sew from now on!{0011}{0090}",
    ("end3/end3.scs", 2):
        "{000C}{0010}{0090}Hehehe! And by winter, I'll make a\nwarm kimono for you and visit with\nShiro!{0011}{00B0}",
    ("end3/end3.scs", 3):
        "{000C}{0010}{0090}To hell with fate, right?\nIsn't that right, Manjimaru?{0011}{00A0}",
    ("wb5/act012.scs", 2):
        "{000C}{0010}{0090}I grant you the Benimaru Slash!\nIt is a sword technique that strikes\nmultiple foes at once!{0012}",
    ("wc5/act013.scs", 0):
        "{000C}{0010}{0090}What?! Hearing you beat Onikotsu\nCastle, I expected someone grand,\nnot scruffy country bumpkins!{0011}{0090}",
    ("wc5/act013.scs", 1):
        "{000C}{0010}{0090}Strongest and handsomest of all!\nWarrior of love and beauty, Pink\nTornado Kikugoro is me!{0011}{00B0}",
    ("wf6/act046.scs", 0):
        "{000C}{0010}{0090}I will be waiting for you forever...\nForever and ever...{0011}{00B0}",
    ("xl1/vle2.scs", 1):
        "{000C}{0010}{0008}Oh, Boss Manji! To help the cause\nof justice even a little, I built an\ninn and waited for you!{0012}",
    ("xl1/vlf2.scs", 0):
        "{000C}{0010}{0008}Oh, Boss Manji! To help the cause\nof justice even a little, I built an\ninn and waited for you!{0012}",
    ("yn6/act_pe.scs", 4):
        "{000C}{0010}{0008}The cape northwest of Sakai! Be sure\nto come! Until then, I'll hold onto\nthis and wait for you forever!{0012}",
}

# 5. Clean overrides for non-{0012} cutscene subtitles (fitting <= 3 lines at 212 px)
# and multi-stanza cutscenes (v78/act078.scs, v85/act085.scs)
CLEAN_SUB_OVERRIDES = {
    "あたしも\u3000そろそろスープ作りに\n飽きてきたところだから\u3000退屈しのぎに\nお相手してあげようじゃないの！\nあんたたち火の一族を\u3000ひき肉にして\nあたしの\u3000メニューのはしっこに\n加えてあげるわよ｜\nさあ\u3000死の料理人\u3000地獄釜の肉助の\nキセキの包丁さばきを見るがいいわ｜":
        "I'm tired of making soup, so I'll\nplay with you to pass the time!{0011}{0050}{000C}I'll mince you Fire Clan brats and\nadd you to my menu!{0011}{0050}{000C}Behold the miraculous knife skills\nof Hell Cauldron Nikusuke!",
    "はっはっはっはっはっは\nうわっはっはっはっはっはっは｜\n\n\n海が呼ぶ｜\n\n\n風が呼ぶ｜\n\n\n女が呼ぶ｜\n\nジパング一の伊達男\n新カブキ団十郎たあ\u3000俺のことでぇい｜":
        "Hahahaha! Wahahahahaha!\nThe sea calls! The wind calls!\nThe ladies call!{0011}{0078}{000C}Zipangu's greatest dandy,\nShin Kabuki Danjuro, is me!",
    "はっはっはっはっはっは\nうわっはっはっはっはっはっは｜\n\n\n海が呼ぶ｜\n\n\n風が呼ぶ｜\n\n\n女が呼ぶ｜":
        "Hahahaha! Wahahahahaha!\nThe sea calls! The wind calls!\nThe ladies call!",
    "あなたとともに\u3000火の一族として\n戦いの中に\u3000身を置くことが\u3000私の宿命\nそれは\u3000もう\u3000変えられぬこと…":
        "Standing with you in battle as Fire\nClan is my destiny—that can no\nlonger be changed...",
    "おっと失礼！\u3000ご挨拶が遅れてしまった\nその\u3000マヌケそうな頭に\u3000僕の美しい\n名前を\u3000刻みこんでもらおうか":
        "Oops, pardon my late greeting! Let\nme carve my beautiful name into\nthat dopey head of yours!",
    "おまえさんなんかにゃ\u3000一生かかっても\n買えんと思うから\u3000見るだけ見るかい？":
        "Someone like you could never afford\nthese, so want to just look?",
    "この倉が有名な\u3000開かずの鶴姫倉さ\nこの倉の借り主の名を\u3000教えようか？":
        "This is the famous sealed Tsuruhime\nStorehouse. Want to know who rents it?",
    "しかし\u3000火の一族と呼ばれる民だけは\n根の一族に\u3000最後まで\u3000頑強に\n抵抗し\u3000戦い続けたのです":
        "Yet only the people of the Fire Clan\nresisted the Root Clan stubbornly\nand fought to the very end.",
    "その代わり\u3000俺様が勝ったら\n菊五郎は\u3000俺様の術を見て\u3000ビビッて\n小便ちびったって\u3000言いふらすからな":
        "If I win, I'll tell everyone Kikugoro\nwet his pants in fear at the sight\nof my spell!",
    "その力を\u3000借り\nほんの数日で\u3000このジパングを\u3000地獄に\nそして\u3000我が物に\u3000変えたといいます":
        "With that power, in just a few days\nthey turned Zipangu into hell and\nclaimed it as their own.",
    "その眼\u3000その髪…\u3000あなたが\u3000卍丸さん\nそして\u3000そのたくましい体\nあなたが\u3000極楽太郎さん\u3000ですね…":
        "Those eyes, that hair... Manjimaru.\nAnd that strong build... You must\nbe Gokuraku Taro...",
    "たまには\u3000こうして\u3000お迎えに\nあがらねば\u3000有名な\u3000火の勇者様に\n失礼にあたると\u3000いうものだよな♀":
        "It'd be rude to the famous Fire Hero\nif I didn't come out to welcome\nyou myself once in a while!",
    "ちょっと\u3000なによ！\u3000あんたたち！\nブタの姿じゃなきゃ\u3000あたしに\n勝てるとでも言うの？\u3000なまいきね｜":
        "Hey, what's with you guys?! Think\nyou can beat me just because you're\nnot pigs anymore? Cheeky brats!",
    "はまぐり姫様に\u3000逆らうなど\n愚かなことは\u3000即刻やめて\u3000田舎にでも\n帰ったほうが\u3000おのれのためだぞ｜":
        "Stop foolishly defying Princess\nHamaguri and go back to the\ncountryside for your own good!",
    "よく覚えとけ｜\u3000ジパングいち\n男前で\u3000強くて\u3000女にもてるのは\nこの\u3000カブキ様だ｜":
        "Remember well! The handsomest,\nstrongest ladies' man in Zipangu\nis the great Kabuki!",
    "わしは\u3000幻夢城城主\u3000はまぐり姫様が\n忠実なる家来\n巻貝法師と\u3000申す者じゃ":
        "I am Makigai Hoshi, loyal retainer\nto Princess Hamaguri, lord of\nGenmu Castle!",
    "わずかに\u3000残った\u3000火の一族も\n千年という年月の中で\u3000その血を\n民の中へ移し\u3000姿を消したはずでした":
        "Over a thousand years, the few\nsurviving Fire Clan passed their\nblood to the people and vanished.",
    "んっ…\u3000ならば\u3000こっちは\n大空を飛ぶ\u3000タカだ｜\n虎など\u3000空を\u3000飛べまい｜":
        "Hmph... Then I'll be a hawk soaring\nthrough the sky! A tiger can't\nfly in the sky!",
    "今より\u3000１とか２\u3000攻撃力が上だと\n剣は\u3000買い換えてしまう性分ですか？":
        "Are you the type to buy a new sword\neven if its Attack is only 1 or 2 higher?",
    "今日は\u3000僕と君の\u3000格の違いってのを\n見せてあげようと\u3000思ってねぇ\nわざわざ\u3000招待したのさ":
        "Today I went out of my way to invite\nyou so I could show you the\ndifference in class between us.",
    "兄のエビス丸も生きかえしてもろて\nアタシ\u3000ほんまにハッピーだすわ\n京都の人も\u3000ハッピーでーす！":
        "My brother Ebisumaru was revived\ntoo—I'm truly happy! Everyone in\nKyoto is happy too!",
    "卍丸\u3000私\u3000あなたに出会えたおかげで\n今まで\u3000こうして生きていられたの\nそしてこれからも\u3000生きてゆけるわ":
        "Manjimaru, thanks to meeting you,\nI've lived until now—and can keep\nliving from here on.",
    "卍丸さんのカツヤク\u3000後世に伝える為\n八本の聖剣ソードの\u3000頭文字を\n山に残して\u3000燃やすそうです":
        "To pass on your deeds, they'll burn\nthe first letters of the eight Holy\nSwords onto the mountains!",
    "卍丸は\u3000聖剣\u3000船海宮義経で\n３本目の暗黒ランを\u3000撃破した｜\n残り\u3000あと\u3000４本｜":
        "Manjimaru destroyed the 3rd Dark\nOrchid with Holy Sword Senkaigu\nYoshitsune! 4 more remain!",
    "卍丸君\u3000せいぜい\u3000この辺の\nザコと戦って\u3000暇をつぶしてくれ\nどうせ君も\u3000ヨミ様復活までの命…":
        "Kill time fighting the small fry\naround here, Manjimaru. You'll only\nlive until Yomi-sama revives anyway...",
    "君の旅も\u3000ここで終わりというわけじゃ\n幻夢城が\u3000ジパングを覆いつくす光景を\nそこで\u3000眺めておるがよいぞ｜":
        "Your journey ends here! Watch from\nthere as Genmu Castle engulfs\nall of Zipangu!",
    "密林城へ来い｜\n密林城で\u3000おもしろい趣向を\n用意して\u3000待ってるぞ｜":
        "Come to Jungle Castle! I'll be\nwaiting there with an amusing\nshow prepared for you!",
    "年の始めの\u3000試しとて…って歌もあるし\n一回\u3000十両で\u3000おみくじは\u3000いかが？":
        "Care to test your New Year's luck\nwith a fortune slip for 10 Ryo?",
    "旅のお供に\u3000お団子は\u3000どうです？\n他にもありますが\u3000いかがですか？":
        "How about some dango for your trip?\nWe have other items too!",
    "武具をお求めですか？\u3000卍丸さん！\n命の恩人から\u3000金とっちゃダメだよね？":
        "Looking for gear, Manjimaru-san?\nI can't charge my lifesaver!",
    "火の一族は\u3000その最後の力の\u3000すべてを\n火の勇者と呼ばれる\u3000七人の若者と\n七本の聖剣に\u3000結集しました":
        "The Fire Clan gathered all their\nremaining power into seven young\nFire Heroes and seven Holy Swords.",
    "無駄\u3000無駄ァ\u3000卍丸｜\nおぬしごときの力で\u3000この鬼面岩が\n動かせると\u3000思っているのか｜":
        "Useless, Manjimaru! Do you really\nthink strength like yours can move\nthis Demon-Face Rock?!",
    "私は\u3000父と母が死んだ日\n「この手で\u3000誰も\u3000傷つけない」と\n墓前に\u3000誓いを\u3000立てました…":
        "The day my parents died, I vowed\nat their grave: \"I will never hurt\nanyone with these hands...\"",
    "純潔の鎖が\u3000比えい山に\u3000あります\n私の右腕と\u3000左腕をしばり\n私の運命を\u3000つなぐ鎖です":
        "The Chains of Purity are on Mt. Hiei.\nThey bind my left and right arms\nand fetter my destiny.",
    "若者たちは\u3000その七つの命と\n引き換えに\u3000七本の暗黒ランを\u3000切り\n根の一族と悪神ヨミを\u3000封じたのです":
        "In exchange for their seven lives,\nthe youths cut down the seven Dark\nOrchids and sealed Yomi away.",
    "行商もこれで\u3000けっこう\u3000きついんや\n何か買ってくれると\u3000助かるわぁ？":
        "Peddling is tough work, you know.\nIt'd really help if you bought something!",
    "術を使って\u3000どちらがハデに\n変身できるか\u3000勝負だ\nもちろん\u3000ハデなほうの\u3000勝ちさ":
        "Let's see whose spell gives the\nflashier transformation! Naturally,\nthe flashier one wins!",
    "道中\u3000くれぐれも\u3000ご油断\u3000めされるな\nわれら\u3000三太夫は\u3000一足先に\n越中の国へ\u3000潜りまする！\u3000では…":
        "Stay on your guard on the road!\nWe Sandayu will slip into Etchu\nahead of you! Farewell...",
    "鉄さえ斬れる刀から\u3000とうふも斬れない\n刀まで何でもござれ！\u3000見てくかい？":
        "From blades that cut iron to ones that\ncan't cut tofu, we have it all! Look?",
    "鬼骨城を倒したというから\nどんな\u3000すごい奴かと思ったら\n小汚い\u3000田舎者じゃないか！":
        "Hearing you beat Onikotsu Castle,\nI expected someone grand, not a\nscruffy country bumpkin!",
    # Stray JP fixes:
    "あっ\u3000大霊院の卍丸さまですね\nお待ちしておりました":
        "Ah, Lord Manjimaru of Dairei-in!\nWe have been waiting for you.",
    "さすがは\u3000火の勇者卍丸どの…\n見事な戦いぶりでございました":
        "Worthy of Fire Hero Manjimaru...\nThat was a magnificent battle!",
    "来ないで\u3000卍丸！":
        "Don't come, Manjimaru!",
}
CHOICE_SUB_MAP["{0001}火多"] = "   {0001}Hida"

