from __future__ import annotations

import csv
import html
import io
import json
import random
import re
from datetime import datetime
from pathlib import Path
from urllib.parse import quote_plus
from urllib.request import Request, urlopen
import xml.etree.ElementTree as ET

from PIL import Image, ImageDraw, ImageFont
import streamlit as st
import streamlit.components.v1 as components


GENRES = [
    "ゴールド",
    "BTC",
    "仮想通貨",
    "為替",
    "投資知識",
    "EA・自動売買",
    "LINE誘導",
]

THEME_SUGGESTIONS = {
    "ゴールド": [
        "ゴールド価格と米金利の関係",
        "金価格とドル指数の見方",
        "地政学リスクと安全資産需要",
        "インフレ懸念とゴールド投資",
        "中央銀行の金購入と相場への影響",
    ],
    "BTC": [
        "BTC価格と米金利の関係",
        "ビットコインETFの資金流入",
        "半減期後のBTC需給",
        "BTCのボラティリティとの向き合い方",
        "長期保有と短期売買の考え方",
    ],
    "仮想通貨": [
        "アルトコインニュースの見方",
        "仮想通貨規制と市場への影響",
        "ステーブルコインのリスク確認",
        "出来高と時価総額の確認ポイント",
        "プロジェクトの実需を確認する方法",
    ],
    "為替": [
        "ドル円と日米金利差",
        "中央銀行発言と為替相場",
        "雇用統計と為替の値動き",
        "円安・円高ニュースの見方",
        "為替介入への警戒ポイント",
    ],
    "投資知識": [
        "資金管理の基本",
        "損切りルールの作り方",
        "NISA活用時の注意点",
        "分散投資の考え方",
        "投資メモを残すメリット",
    ],
    "EA・自動売買": [
        "EAのバックテスト確認ポイント",
        "自動売買の最大ドローダウン",
        "フォワード実績の見方",
        "EAを止める基準の作り方",
        "相場環境とEAの相性",
    ],
    "LINE誘導": [
        "投資情報を受け取る前の確認ポイント",
        "相場メモをLINEで受け取る活用法",
        "無料情報を見るときの注意点",
        "投資学習コミュニティの使い方",
        "売買判断を急がない情報収集",
    ],
}

NEWS_QUERIES = {
    "ゴールド": "ゴールド 金価格 米金利 ドル指数 投資",
    "BTC": "BTC ビットコイン 価格 ETF 暗号資産",
    "仮想通貨": "仮想通貨 暗号資産 アルトコイン 規制 市場",
    "為替": "為替 ドル円 円相場 米金利 中央銀行",
    "投資知識": "投資 NISA 資産形成 リスク管理 金融教育",
    "EA・自動売買": "EA 自動売買 FX バックテスト ドローダウン",
    "LINE誘導": "投資 情報収集 LINE 資産形成 学習",
}

PROHIBITED_PHRASES = [
    "絶対稼げる",
    "必ず上がる",
    "今すぐ買え",
    "確実に儲かる",
    " guaranteed ",
]

STRONG_ASSERTIONS = [
    "必ず",
    "絶対",
    "確実",
    "断言",
    "間違いない",
    "100%",
]

ENDING_NOTES = [
    "ここで差がつくのは、ニュースの見出しよりも、その裏にある資金の流れを読めるかだと思います。",
    "短期の値動きに振り回されるより、今どの材料が市場に意識されているかを押さえたい局面です。",
    "強気・弱気のどちらかに寄せすぎず、シナリオを複数持つ人ほど相場に残りやすいと感じます。",
    "売買を急ぐ前に、根拠、時間軸、撤退ラインをセットで見るだけで判断の質はかなり変わります。",
    "このテーマは、価格予想よりも市場参加者が何を警戒しているかを見る方が学びが多いです。",
]

GENRE_CONTEXTS = {
    "ゴールド": [
        "金利、ドル指数、地政学リスクの変化で見え方が変わりやすい資産",
        "インフレ懸念や安全資産需要が意識されやすいテーマ",
        "短期の値動きだけでなく、実質金利や為替の影響も受けやすい市場",
    ],
    "BTC": [
        "半減期、ETF資金流入、米金利の見通しなどで注目度が変わりやすい資産",
        "ボラティリティが大きく、期待と警戒が同時に出やすい市場",
        "長期ストーリーと短期需給のギャップを確認したいテーマ",
    ],
    "仮想通貨": [
        "プロジェクトの実需、流動性、規制動向で評価が変わりやすい分野",
        "ニュースの勢いだけで価格が動く場面もあり、冷静な確認が必要な市場",
        "銘柄ごとの差が大きく、時価総額や出来高も見ておきたいテーマ",
    ],
    "為替": [
        "金利差、中央銀行発言、雇用や物価指標で流れが変わりやすい市場",
        "短期ではニュース、長期では金融政策の方向感が意識されやすいテーマ",
        "一方向に見えても反発が起きやすく、ポジション管理が重要な市場",
    ],
    "投資知識": [
        "利益より先にリスク管理を考える習慣が大切なテーマ",
        "相場観よりも、資金管理と再現性を整えることが重要な分野",
        "知識を増やすほど、焦って売買しない判断も選びやすくなるテーマ",
    ],
    "EA・自動売買": [
        "バックテスト、フォワード実績、最大ドローダウンの確認が欠かせない分野",
        "設定任せにしすぎず、相場環境との相性を見たいテーマ",
        "便利さの裏側にある停止基準や資金管理を先に決めたい分野",
    ],
    "LINE誘導": [
        "投資情報を受け取る前に、自分の目的やリスク許容度を整理したいテーマ",
        "情報収集の入口として使えても、売買判断は自分で確認したい分野",
        "相場メモや学習用の情報として、落ち着いて活用したいテーマ",
    ],
}

TEMPLATES = [
    "{genre}で今見るべきは「{theme}」そのものより、相場がどの材料に反応しているかです。{context}だからこそ、値動きだけを追うと判断が浅くなりがち。{note}",
    "「{theme}」は、{genre}を見るうえでかなり重要なヒントになります。ポイントは上がる下がるの予想ではなく、どの時間軸の参加者が動いているか。{context}なので、背景を分けて見る価値があります。{note}",
    "{genre}の「{theme}」は、単なるニュースではなく相場心理を読む材料になります。強い材料に見えても、すでに価格へ織り込まれている可能性もあります。{note}",
    "「{theme}」で注目したいのは、価格の方向感よりも市場の警戒ポイントです。{genre}は{context}なので、期待シナリオと崩れる条件をセットで持つと見方がかなり変わります。{note}",
    "投資で差が出るのは、ニュースを早く知ることより解釈の精度です。{genre}の「{theme}」も、見出しだけではなく金利、需給、リスク許容度の変化まで見たいところ。{note}",
]

FONT_CANDIDATES = [
    "/System/Library/Fonts/Supplemental/AppleGothic.ttf",
    "/System/Library/Fonts/AppleSDGothicNeo.ttc",
    "/System/Library/Fonts/Hiragino Sans GB.ttc",
    "/System/Library/Fonts/Supplemental/NotoSansGothic-Regular.ttf",
]


@st.cache_data(ttl=900)
def fetch_latest_news(genre: str, max_items: int = 8) -> list[dict[str, str]]:
    query = quote_plus(NEWS_QUERIES[genre])
    url = f"https://news.google.com/rss/search?q={query}&hl=ja&gl=JP&ceid=JP:ja"
    request = Request(url, headers={"User-Agent": "Mozilla/5.0"})

    with urlopen(request, timeout=10) as response:
        xml_text = response.read().decode("utf-8", errors="ignore")

    root = ET.fromstring(xml_text)
    items = []
    for item in root.findall("./channel/item")[:max_items]:
        title = html.unescape(item.findtext("title", default="")).strip()
        link = item.findtext("link", default="").strip()
        published = item.findtext("pubDate", default="").strip()
        if title:
            items.append({"title": title, "link": link, "published": published})
    return items


def sanitize_text(text: str) -> str:
    for phrase in PROHIBITED_PHRASES + STRONG_ASSERTIONS:
        text = text.replace(phrase, "")
    return " ".join(text.split())


def clean_theme_title(theme: str) -> str:
    theme = html.unescape(theme)
    theme = re.sub(r"\s+", " ", theme).strip()
    theme = re.sub(r"\s*[|-]\s*\d{4}年\d{1,2}月\d{1,2}日.*$", "", theme)
    theme = re.sub(r"\s*\d{4}年\d{1,2}月\d{1,2}日.*$", "", theme)
    theme = re.sub(r"\s*-\s*[^-]{2,40}$", "", theme)
    for separator in ["｜", "|"]:
        if separator in theme:
            theme = theme.split(separator)[0]
    theme = re.sub(r"\s+", " ", theme).strip(" -｜|。")
    return sanitize_text(theme)


def fit_to_x_length(text: str, theme: str, genre: str) -> str:
    text = sanitize_text(text)
    if len(text) > 280:
        text = text[:276].rstrip("、。 ") + "。"

    while len(text) < 140:
        addition = (
            f"{genre}の{theme}は、見出しで終わらせず市場の反応、出来高、金利や需給まで見ると解像度が上がります。"
            "ここを分けて考えられるかで、ニュースの使い方に差が出ます。"
        )
        text = sanitize_text(text + " " + addition)
        if len(text) > 280:
            text = text[:276].rstrip("、。 ") + "。"
            break

    return text


def format_post_with_line_breaks(text: str) -> str:
    text = sanitize_text(text)
    text = re.sub(r"([。！？])\s+", r"\1", text)
    sentences = []
    current = ""
    for char in text:
        current += char
        if char in "。！？":
            sentences.append(current.strip())
            current = ""
    if current:
        sentences.append(current.strip())

    paragraphs = []
    paragraph = ""
    for sentence in sentences:
        if paragraph and len(paragraph) + len(sentence) > 52:
            paragraphs.append(paragraph)
            paragraph = sentence
        else:
            paragraph += sentence
    if paragraph:
        paragraphs.append(paragraph)

    formatted = "\n\n".join(paragraphs)
    if len(formatted) <= 280:
        return formatted

    formatted = "\n".join(paragraphs)
    if len(formatted) <= 280:
        return formatted

    return text[:276].rstrip("、。 \n") + "。"


def generate_posts(theme: str, genre: str) -> list[str]:
    theme = clean_theme_title(theme)
    contexts = GENRE_CONTEXTS[genre][:]
    notes = ENDING_NOTES[:]
    templates = TEMPLATES[:]
    random.shuffle(contexts)
    random.shuffle(notes)
    random.shuffle(templates)

    posts = []
    for index in range(5):
        post = templates[index].format(
            genre=genre,
            theme=theme,
            context=contexts[index % len(contexts)],
            note=notes[index % len(notes)],
        )
        fitted_post = fit_to_x_length(post, theme, genre)
        posts.append(format_post_with_line_breaks(fitted_post))
    return posts


def validate_posts(posts: list[str]) -> list[str]:
    warnings = []
    for number, post in enumerate(posts, start=1):
        if not 140 <= len(post) <= 280:
            warnings.append(f"{number}件目: 文字数が140〜280字の範囲外です。")
        for phrase in PROHIBITED_PHRASES + STRONG_ASSERTIONS:
            if phrase.strip() and phrase in post:
                warnings.append(f"{number}件目: 禁止表現「{phrase.strip()}」が含まれています。")
    return warnings


def save_to_csv(theme: str, genre: str, posts: list[str]) -> Path:
    theme = clean_theme_title(theme)
    output_dir = Path("outputs")
    output_dir.mkdir(exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    csv_path = output_dir / f"x_posts_{timestamp}.csv"

    with csv_path.open("w", encoding="utf-8-sig", newline="") as csv_file:
        writer = csv.writer(csv_file)
        writer.writerow(["created_at", "genre", "theme", "post", "characters"])
        created_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        for post in posts:
            writer.writerow([created_at, genre, theme, post, len(post)])

    return csv_path


def build_csv_text(theme: str, genre: str, posts: list[str]) -> str:
    theme = clean_theme_title(theme)
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["created_at", "genre", "theme", "post", "characters"])
    created_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    for post in posts:
        writer.writerow([created_at, genre, theme, post, len(post)])
    return output.getvalue()


def copy_button(label: str, text: str, key: str) -> None:
    payload = json.dumps(text)
    button_id = f"copy_{key}"
    components.html(
        f"""
        <button id="{button_id}" style="
            width: 100%;
            min-height: 42px;
            border: 1px solid #d0d7de;
            border-radius: 8px;
            background: #ffffff;
            color: #111827;
            font-size: 15px;
            font-weight: 700;
            cursor: pointer;
        ">{html.escape(label)}</button>
        <script>
        const button = document.getElementById("{button_id}");
        const text = {payload};
        button.addEventListener("click", async () => {{
            try {{
                await navigator.clipboard.writeText(text);
                const original = button.textContent;
                button.textContent = "コピーしました";
                setTimeout(() => button.textContent = original, 1600);
            }} catch (error) {{
                const area = document.createElement("textarea");
                area.value = text;
                document.body.appendChild(area);
                area.select();
                document.execCommand("copy");
                document.body.removeChild(area);
                const original = button.textContent;
                button.textContent = "コピーしました";
                setTimeout(() => button.textContent = original, 1600);
            }}
        }});
        </script>
        """,
        height=52,
    )


def find_font_path() -> str | None:
    for font_dir in [Path("/System/Library/Fonts"), Path("/Library/Fonts")]:
        for font_path in font_dir.rglob("*.ttc"):
            if "ヒラ" in font_path.name and "角" in font_path.name:
                return str(font_path)
    for font_path in FONT_CANDIDATES:
        if Path(font_path).exists():
            return font_path
    return None


def load_font(size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    font_path = find_font_path()
    if font_path:
        return ImageFont.truetype(font_path, size=size)
    return ImageFont.load_default()


def shorten_text(text: str, max_chars: int) -> str:
    text = sanitize_text(text)
    if len(text) <= max_chars:
        return text
    return text[: max_chars - 1].rstrip("、。 ") + "…"


def clean_theme_for_comic(theme: str) -> str:
    theme = clean_theme_title(theme)
    for separator in [" - ", "｜", "|"]:
        if separator in theme:
            theme = theme.split(separator)[0]
    return shorten_text(theme, 24)


def wrap_text(text: str, font: ImageFont.ImageFont, max_width: int) -> list[str]:
    lines = []
    current = ""
    for char in text:
        test_line = current + char
        width = font.getbbox(test_line)[2]
        if width <= max_width or not current:
            current = test_line
        else:
            lines.append(current)
            current = char
    if current:
        lines.append(current)
    return lines


def draw_wrapped_text(
    draw: ImageDraw.ImageDraw,
    position: tuple[int, int],
    text: str,
    font: ImageFont.ImageFont,
    fill: str,
    max_width: int,
    line_spacing: int = 8,
) -> int:
    x, y = position
    for line in wrap_text(text, font, max_width):
        draw.text((x, y), line, font=font, fill=fill)
        y += font.getbbox(line)[3] - font.getbbox(line)[1] + line_spacing
    return y


def draw_badge(draw: ImageDraw.ImageDraw, xy: tuple[int, int], number: int) -> None:
    x, y = xy
    draw.rounded_rectangle((x, y, x + 74, y + 74), radius=12, fill="#05070d", outline="#ffffff", width=3)
    draw.text((x + 22, y + 8), str(number), font=load_font(48), fill="#ffffff")


def draw_mascot(draw: ImageDraw.ImageDraw, center: tuple[int, int], scale: float = 1.0, mood: str = "neutral") -> None:
    cx, cy = center
    head_w = int(110 * scale)
    head_h = int(130 * scale)
    green = "#a7d521"
    outline = "#263800"
    draw.ellipse((cx - head_w // 2, cy - head_h // 2, cx + head_w // 2, cy + head_h // 2), fill=green, outline=outline, width=3)
    draw.line((cx - 30 * scale, cy - 58 * scale, cx - 55 * scale, cy - 95 * scale), fill=outline, width=4)
    draw.line((cx + 30 * scale, cy - 58 * scale, cx + 55 * scale, cy - 95 * scale), fill=outline, width=4)
    draw.ellipse((cx - 68 * scale, cy - 112 * scale, cx - 42 * scale, cy - 86 * scale), fill=green, outline=outline, width=3)
    draw.ellipse((cx + 42 * scale, cy - 112 * scale, cx + 68 * scale, cy - 86 * scale), fill=green, outline=outline, width=3)
    draw.polygon(
        [
            (cx - 55 * scale, cy - 8 * scale),
            (cx - 98 * scale, cy - 35 * scale),
            (cx - 62 * scale, cy + 28 * scale),
        ],
        fill=green,
        outline=outline,
    )
    draw.polygon(
        [
            (cx + 55 * scale, cy - 8 * scale),
            (cx + 98 * scale, cy - 35 * scale),
            (cx + 62 * scale, cy + 28 * scale),
        ],
        fill=green,
        outline=outline,
    )
    draw.ellipse((cx - 34 * scale, cy - 24 * scale, cx - 4 * scale, cy + 14 * scale), fill="#ffffff", outline=outline, width=2)
    draw.ellipse((cx + 4 * scale, cy - 24 * scale, cx + 34 * scale, cy + 14 * scale), fill="#ffffff", outline=outline, width=2)
    draw.ellipse((cx - 22 * scale, cy - 8 * scale, cx - 10 * scale, cy + 8 * scale), fill="#111111")
    draw.ellipse((cx + 10 * scale, cy - 8 * scale, cx + 22 * scale, cy + 8 * scale), fill="#111111")
    if mood == "surprise":
        draw.ellipse((cx - 16 * scale, cy + 35 * scale, cx + 16 * scale, cy + 68 * scale), fill="#2a1208", outline=outline, width=2)
    elif mood == "happy":
        draw.arc((cx - 28 * scale, cy + 26 * scale, cx + 28 * scale, cy + 66 * scale), 0, 180, fill=outline, width=4)
    else:
        draw.arc((cx - 22 * scale, cy + 34 * scale, cx + 22 * scale, cy + 56 * scale), 0, 180, fill=outline, width=3)
    draw.rounded_rectangle((cx - 52 * scale, cy + 75 * scale, cx + 52 * scale, cy + 170 * scale), radius=18, fill="#06243b", outline="#0b1420", width=3)


def draw_chart(draw: ImageDraw.ImageDraw, box: tuple[int, int, int, int], color: str) -> None:
    x1, y1, x2, y2 = box
    draw.rounded_rectangle(box, radius=12, fill="#081525", outline="#88a7c7", width=2)
    points = [
        (x1 + 24, y2 - 48),
        (x1 + 90, y2 - 120),
        (x1 + 160, y2 - 90),
        (x1 + 235, y2 - 170),
        (x2 - 32, y2 - 130),
    ]
    draw.line(points, fill=color, width=7, joint="curve")
    for x, y in points:
        draw.ellipse((x - 8, y - 8, x + 8, y + 8), fill="#ffffff", outline=color, width=3)


def draw_panel(
    draw: ImageDraw.ImageDraw,
    box: tuple[int, int, int, int],
    number: int,
    heading: str,
    body: str,
    genre: str,
    mood: str,
) -> None:
    x1, y1, x2, y2 = box
    draw.rounded_rectangle(box, radius=8, fill="#061222", outline="#ffffff", width=5)
    draw_badge(draw, (x1 + 18, y1 + 18), number)
    heading_font = load_font(34)
    body_font = load_font(25)
    small_font = load_font(22)
    draw_wrapped_text(draw, (x1 + 104, y1 + 24), heading, heading_font, "#ffe600", x2 - x1 - 130, 4)
    draw_mascot(draw, (x1 + 122, y1 + 250), 0.82, mood)
    if genre in ["BTC", "仮想通貨"]:
        icon = "B"
        icon_color = "#f59e0b"
    elif genre == "ゴールド":
        icon = "GOLD"
        icon_color = "#facc15"
    elif genre == "為替":
        icon = "FX"
        icon_color = "#22c55e"
    else:
        icon = "TIP"
        icon_color = "#38bdf8"
    draw.ellipse((x2 - 130, y2 - 130, x2 - 28, y2 - 28), fill=icon_color, outline="#ffffff", width=4)
    draw.text((x2 - 106, y2 - 102), icon, font=load_font(25), fill="#111827")
    bubble = (x1 + 220, y1 + 122, x2 - 28, y2 - 58)
    draw.rounded_rectangle(bubble, radius=18, fill="#fff7e6", outline="#111827", width=3)
    draw_wrapped_text(draw, (bubble[0] + 22, bubble[1] + 18), body, body_font, "#111827", bubble[2] - bubble[0] - 44, 8)
    draw_chart(draw, (x1 + 28, y2 - 178, x1 + 260, y2 - 34), "#ef4444" if number == 3 else "#22c55e")
    draw.text((x1 + 36, y2 - 204), "CHECK", font=small_font, fill="#ffffff")


def create_comic_script(theme: str, genre: str) -> list[tuple[str, str, str]]:
    short_theme = clean_theme_for_comic(theme)
    context = GENRE_CONTEXTS[genre][0]
    return [
        (
            f"{genre}ニュースを整理",
            f"今日のテーマは「{short_theme}」。まずは見出しだけで判断せず、何が材料視されているか確認します。",
            "surprise",
        ),
        (
            "市場が反応する理由",
            f"{context}です。短期の値動きと長期の前提を分けて見ると、焦りにくくなります。",
            "happy",
        ),
        (
            "注意したいポイント",
            "SNSの熱量だけで飛び乗らず、出来高、時間軸、損切りラインを先に確認したいところです。",
            "surprise",
        ),
        (
            "デンデの見解",
            "一つの見方として、材料を整理してから判断。投資助言ではなく、無理のない範囲で情報確認を続けたいですね。",
            "happy",
        ),
    ]


def generate_four_panel_comic(theme: str, genre: str) -> Path:
    output_dir = Path("outputs")
    output_dir.mkdir(exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    image_path = output_dir / f"x_comic_{timestamp}.png"
    image = Image.new("RGB", (1200, 1200), "#020617")
    draw = ImageDraw.Draw(image)

    panels = [
        (8, 8, 596, 596),
        (604, 8, 1192, 596),
        (8, 604, 596, 1192),
        (604, 604, 1192, 1192),
    ]
    for index, (heading, body, mood) in enumerate(create_comic_script(theme, genre), start=1):
        draw_panel(draw, panels[index - 1], index, heading, body, genre, mood)

    image.save(image_path)
    return image_path


def build_comic_prompt(theme: str, genre: str, posts: list[str]) -> str:
    theme = clean_theme_title(theme)
    short_theme = clean_theme_for_comic(theme)
    script = create_comic_script(theme, genre)
    reference_post = posts[0] if posts else ""
    panel_lines = []
    for index, (heading, body, _mood) in enumerate(script, start=1):
        panel_lines.append(f"{index}コマ目: 見出し「{heading}」 / 内容「{body}」")

    return f"""
以下の条件で、X投稿用の4コマ漫画画像を作成してください。

【目的】
投資系X投稿に添える、情報整理型の4コマ漫画画像を作る。
ジャンルは「{genre}」、テーマは「{short_theme}」です。

【参考にする投稿文】
{reference_post}

【4コマの内容】
{chr(10).join(panel_lines)}

【画像の構成】
- 正方形の1枚画像
- 2x2配置の4コマ漫画
- 各コマに太めの白い枠線
- 左上に1、2、3、4の番号
- 濃いネイビー系の背景
- かわいい緑色の宇宙人風マスコットキャラクターを登場させる
- 投資ニュース解説らしく、チャート、ローソク足、価格ボード、金貨、BTC、為替ボードなどを自然に入れる
- 文字が読みやすい大きな吹き出しを入れる
- Xで目を引く、明るく高品質なデジタルイラストにする

【画風】
- 添付した参考4コマのような、ポップで見やすい投資解説漫画
- 太い線、はっきりした色、余白のある構図
- 少しコミカルだが、投資アカウントに合う落ち着きも残す
- 暗い背景に黄色や白の見出しが映える雰囲気

【重要な注意】
- 「絶対稼げる」「必ず上がる」「今すぐ買え」などの断定・買い煽り表現は入れない
- 利益保証や投資助言に見える表現は避ける
- 投資判断は自己責任、情報整理、リスク確認というニュアンスにする
- 読者を煽りすぎず、冷静に学べる雰囲気にする

【入れてほしい日本語テキスト】
1コマ目見出し: {script[0][0]}
1コマ目本文: {script[0][1]}

2コマ目見出し: {script[1][0]}
2コマ目本文: {script[1][1]}

3コマ目見出し: {script[2][0]}
3コマ目本文: {script[2][1]}

4コマ目見出し: {script[3][0]}
4コマ目本文: {script[3][1]}
""".strip()


def save_comic_prompt(theme: str, genre: str, prompt: str) -> Path:
    theme = clean_theme_title(theme)
    output_dir = Path("outputs")
    output_dir.mkdir(exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    safe_genre = genre.replace("・", "_")
    prompt_path = output_dir / f"x_comic_prompt_{safe_genre}_{timestamp}.txt"
    prompt_path.write_text(prompt, encoding="utf-8")
    return prompt_path


def clear_generated_results() -> None:
    st.session_state.posts = []
    st.session_state.csv_path = None
    st.session_state.comic_path = None
    st.session_state.comic_prompt = ""
    st.session_state.prompt_path = None


st.set_page_config(page_title="投資系X投稿文生成ツール", page_icon="✍️", layout="centered")

st.title("投資系X投稿文生成ツール")
st.caption("X APIや自動投稿は使わず、投稿文を作成してCSV保存するだけのツールです。")

if "posts" not in st.session_state:
    st.session_state.posts = []
if "csv_path" not in st.session_state:
    st.session_state.csv_path = None
if "comic_path" not in st.session_state:
    st.session_state.comic_path = None
if "comic_prompt" not in st.session_state:
    st.session_state.comic_prompt = ""
if "prompt_path" not in st.session_state:
    st.session_state.prompt_path = None
if "previous_genre" not in st.session_state:
    st.session_state.previous_genre = GENRES[0]

with st.sidebar:
    st.header("入力")
    genre = st.selectbox("投稿ジャンル", GENRES, key="selected_genre")
    if genre != st.session_state.previous_genre:
        clear_generated_results()
        st.session_state.previous_genre = genre

    theme_source = st.radio(
        "テーマの選び方",
        ["最新ニュースから選ぶ", "テーマ候補から選ぶ", "手入力する"],
        key="theme_source",
        on_change=clear_generated_results,
    )

    selected_news = None
    if theme_source == "最新ニュースから選ぶ":
        try:
            news_items = fetch_latest_news(genre)
        except Exception as error:
            news_items = []
            st.warning(f"ニュースを取得できませんでした: {error}")

        if news_items:
            news_titles = [item["title"] for item in news_items]
            selected_title = st.selectbox(
                "最新ニュース",
                news_titles,
                key=f"latest_news_{genre}",
                on_change=clear_generated_results,
            )
            selected_news = next(item for item in news_items if item["title"] == selected_title)
            theme = selected_news["title"]
            with st.expander("選択中ニュースの情報"):
                st.write(f"公開日時: {selected_news['published'] or '取得なし'}")
                if selected_news["link"]:
                    st.link_button("ニュース元を開く", selected_news["link"])
        else:
            theme = st.selectbox(
                "代替テーマ",
                THEME_SUGGESTIONS[genre],
                key=f"fallback_theme_{genre}",
                on_change=clear_generated_results,
            )
    elif theme_source == "テーマ候補から選ぶ":
        theme = st.selectbox(
            "投稿テーマ",
            THEME_SUGGESTIONS[genre],
            key=f"suggested_theme_{genre}",
            on_change=clear_generated_results,
        )
    else:
        theme = st.text_input(
            "投稿テーマ",
            placeholder="例: BTCと米金利の関係",
            key=f"manual_theme_{genre}",
            on_change=clear_generated_results,
        )

    st.caption(f"現在の選択: {genre} / {theme_source}")
    st.info("生成文は投資助言ではありません。最新ニュースは投稿前に必ず元記事や一次情報を確認してください。")

prompt_mode = st.radio(
    "4コマ漫画用プロンプト",
    ["作成する", "作成しない"],
    horizontal=True,
)
generate_simple_comic = st.checkbox("確認用の簡易4コマPNGも作成する", value=False)

generate_button = st.button("投稿文を5個生成する", type="primary", use_container_width=True)

if generate_button:
    if not theme.strip():
        st.error("投稿テーマを入力してください。")
    else:
        st.session_state.posts = generate_posts(theme.strip(), genre)
        st.session_state.csv_path = save_to_csv(theme.strip(), genre, st.session_state.posts)
        if prompt_mode == "作成する":
            st.session_state.comic_prompt = build_comic_prompt(theme.strip(), genre, st.session_state.posts)
            st.session_state.prompt_path = save_comic_prompt(theme.strip(), genre, st.session_state.comic_prompt)
        else:
            st.session_state.comic_prompt = ""
            st.session_state.prompt_path = None

        if generate_simple_comic:
            st.session_state.comic_path = generate_four_panel_comic(theme.strip(), genre)
        else:
            st.session_state.comic_path = None

if st.session_state.posts:
    st.subheader("生成結果")
    warnings = validate_posts(st.session_state.posts)
    if warnings:
        st.warning("\n".join(warnings))
    else:
        st.success("禁止表現と文字数のチェックを通過しました。")

    for index, post in enumerate(st.session_state.posts, start=1):
        st.text_area(
            f"{index}. {len(post)}字",
            value=post,
            height=150,
            key=f"post_{index}",
        )
        copy_button(f"{index}件目の投稿文をコピー", post, f"post_{index}")

    if st.session_state.csv_path:
        csv_text = build_csv_text(theme.strip(), genre, st.session_state.posts)
        with st.expander("CSV形式でコピーする"):
            st.text_area(
                "スプレッドシートやメモに貼り付けるCSV形式テキストです。",
                value=csv_text,
                height=180,
            )
            copy_button("CSV形式テキストをコピー", csv_text, "csv_text")

    if st.session_state.comic_prompt:
        st.subheader("4コマ漫画作成プロンプト")
        st.text_area(
            "このプロンプトをChatGPTの画像生成に貼り付けてください。",
            value=st.session_state.comic_prompt,
            height=520,
        )
        copy_button("4コマ漫画プロンプトをコピー", st.session_state.comic_prompt, "comic_prompt")

    if st.session_state.comic_path:
        comic_path = Path(st.session_state.comic_path)
        st.subheader("確認用の簡易4コマ漫画")
        st.image(str(comic_path), caption="投稿用4コマ漫画PNG", use_container_width=True)
        with comic_path.open("rb") as image_file:
            st.download_button(
                "4コマ漫画PNGをダウンロード",
                data=image_file,
                file_name=comic_path.name,
                mime="image/png",
                use_container_width=True,
            )

st.divider()
st.caption("注意: このツールは投稿文の下書きを作る目的です。売買判断や投資助言を行うものではありません。")
