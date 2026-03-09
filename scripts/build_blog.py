from __future__ import annotations

import datetime as dt
import html
import json
import re
import shutil
from pathlib import Path
from typing import Any

import markdown


ROOT = Path(__file__).resolve().parent.parent
CONFIG_PATH = ROOT / "blog_config.json"
CONTENT_DIR = ROOT / "content"
POSTS_DIR = ROOT / "posts"
CATEGORIES_DIR = ROOT / "categories"

FONT_LINK = (
    '<link rel="preconnect" href="https://fonts.googleapis.com">\n'
    '  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>\n'
    '  <link '
    'href="https://fonts.googleapis.com/css2?family=Manrope:wght@400;500;700;800&'
    'family=Cormorant+Garamond:wght@500;600;700&display=swap" rel="stylesheet">'
)


def load_config() -> dict[str, Any]:
    return json.loads(CONFIG_PATH.read_text(encoding="utf-8"))


def slugify(value: str) -> str:
    cleaned = re.sub(r"\s+", "-", value.strip().lower())
    cleaned = re.sub(r"[\\/]+", "-", cleaned)
    cleaned = re.sub(r"[^0-9a-z\u4e00-\u9fff\-_]+", "-", cleaned)
    cleaned = re.sub(r"-{2,}", "-", cleaned).strip("-_")
    return cleaned or "post"


def parse_front_matter(raw_text: str) -> tuple[dict[str, str], str]:
    if not raw_text.startswith("---\n"):
        return {}, raw_text

    end_index = raw_text.find("\n---\n", 4)
    if end_index == -1:
        return {}, raw_text

    header = raw_text[4:end_index]
    body = raw_text[end_index + 5 :]
    meta: dict[str, str] = {}

    for line in header.splitlines():
        if ":" not in line:
            continue
        key, value = line.split(":", 1)
        meta[key.strip().lower()] = value.strip()

    return meta, body


def first_heading(lines: list[str]) -> str | None:
    for line in lines:
        stripped = line.strip()
        if stripped.startswith("# "):
            return stripped[2:].strip()
    return None


def strip_first_heading(lines: list[str]) -> list[str]:
    stripped_once = False
    kept: list[str] = []

    for line in lines:
        if not stripped_once and line.strip().startswith("# "):
            stripped_once = True
            continue
        kept.append(line)

    return kept


def plain_excerpt(markdown_text: str) -> str:
    text = re.sub(r"```.*?```", "", markdown_text, flags=re.S)
    text = re.sub(r"`([^`]*)`", r"\1", text)
    text = re.sub(r"!\[[^\]]*\]\([^)]+\)", "", text)
    text = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", text)
    text = re.sub(r"^[#>\-\*\d\.\s]+", "", text, flags=re.M)
    paragraphs = [item.strip() for item in text.split("\n\n")]

    for paragraph in paragraphs:
        compact = " ".join(paragraph.split())
        if compact:
            if len(compact) <= 110:
                return compact

            clipped = compact[:110].strip()
            if " " in clipped:
                clipped = clipped.rsplit(" ", 1)[0].strip()

            return clipped.rstrip("，。；、,.!?！？:：") + "..."

    return "这篇文章还没有摘要。"


def format_date(value: str | None, fallback: dt.datetime) -> tuple[str, dt.datetime]:
    if value:
        for fmt in ("%Y-%m-%d", "%Y/%m/%d", "%Y.%m.%d"):
            try:
                parsed = dt.datetime.strptime(value, fmt)
                return parsed.strftime("%Y.%m.%d"), parsed
            except ValueError:
                continue

    return fallback.strftime("%Y.%m.%d"), fallback


def render_markdown(body: str) -> str:
    return markdown.markdown(
        body,
        extensions=["extra", "fenced_code", "tables", "sane_lists", "nl2br"],
        output_format="html5",
    )


def page_template(
    *,
    page_title: str,
    description: str,
    rel_prefix: str,
    hero_anchor: str,
    body: str,
    config: dict[str, Any],
) -> str:
    site_title = html.escape(config["site_title"])
    page_title_text = html.escape(page_title)
    meta_description = html.escape(description)
    github_url = html.escape(config["github_url"])
    stylesheet = f"{rel_prefix}assets/styles.css"
    script_path = f"{rel_prefix}assets/site.js"
    home_href = f"{rel_prefix}index.html"
    title_text = site_title if page_title == config["site_title"] else f"{page_title_text} | {site_title}"

    return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{title_text}</title>
  <meta name="description" content="{meta_description}">
  {FONT_LINK}
  <link rel="stylesheet" href="{stylesheet}">
  <script defer src="{script_path}"></script>
</head>
<body>
  <div class="page-shell">
    <header class="site-header">
      <a class="brand" href="{home_href}">{site_title}</a>
      <nav class="site-nav">
        <a href="{home_href}{hero_anchor}">板块</a>
        <a href="{home_href}#latest">最新</a>
        <a href="{github_url}" target="_blank" rel="noreferrer">GitHub</a>
      </nav>
    </header>
    <main>
      {body}
    </main>
    <footer class="site-footer">
      <p>© <span id="year"></span> {site_title}. Content-first, generated from Markdown.</p>
    </footer>
  </div>
</body>
</html>
"""


def section_cards(sections: list[dict[str, Any]], counts: dict[str, int]) -> str:
    cards = []
    for section in sections:
        topics = "".join(f"<span>{html.escape(item)}</span>" for item in section["topics"])
        cards.append(
            f"""
            <article class="section-card" data-reveal>
              <div class="section-card-head">
                <div>
                  <p class="eyebrow">{html.escape(section["badge"])}</p>
                  <h3>{html.escape(section["label"])}</h3>
                </div>
                <span class="count-pill">{counts.get(section["slug"], 0)} 篇</span>
              </div>
              <p class="section-intro">{html.escape(section["description"])}</p>
              <div class="topic-list">{topics}</div>
              <a class="text-link" href="./categories/{section["slug"]}.html">进入这个板块</a>
            </article>
            """
        )

    return "".join(cards)


def post_card(post: dict[str, Any], href_prefix: str = "./") -> str:
    href = html.escape(f"{href_prefix}posts/{post['section_slug']}/{post['slug']}.html")
    category_href = html.escape(f"{href_prefix}categories/{post['section_slug']}.html")
    return f"""
    <article class="post-card" data-reveal>
      <div class="post-list-top">
        <a class="post-chip" href="{category_href}">{html.escape(post["section_label"])}</a>
        <p class="post-meta">{html.escape(post["date_display"])}</p>
      </div>
      <h3>{html.escape(post["title"])}</h3>
      <p>{html.escape(post["summary"])}</p>
      <a class="text-link" href="{href}">阅读全文</a>
    </article>
    """


def list_card(post: dict[str, Any], href_prefix: str = "../") -> str:
    href = html.escape(f"{href_prefix}posts/{post['section_slug']}/{post['slug']}.html")
    return f"""
    <article class="post-list-card" data-reveal>
      <div class="post-list-top">
        <span class="post-chip">{html.escape(post["section_label"])}</span>
        <p class="post-meta">{html.escape(post["date_display"])}</p>
      </div>
      <h3>{html.escape(post["title"])}</h3>
      <p>{html.escape(post["summary"])}</p>
      <a class="text-link" href="{href}">打开文章</a>
    </article>
    """


def render_index(config: dict[str, Any], posts: list[dict[str, Any]], counts: dict[str, int]) -> str:
    latest_cards = "".join(post_card(post) for post in posts[:6])
    if not latest_cards:
        latest_cards = '<div class="empty-state" data-reveal>还没有文章，先往任意内容目录里放入一个 Markdown 文件吧。</div>'
    guide_cards = """
      <article class="guide-card" data-reveal>
        <h3>以后怎么发内容</h3>
        <p class="guide-note">直接把 Markdown 文件放进对应板块目录。我来帮你执行生成并推送到 GitHub。</p>
      </article>
      <article class="guide-card" data-reveal>
        <h3>最适合写什么</h3>
        <p class="guide-note">软硬件适合写设备和工具，合约交易适合写风控和复盘，项目实验适合记录过程，周记观察适合写阶段性总结。</p>
      </article>
    """

    body = f"""
      <section class="hero" data-reveal>
        <div class="hero-copy">
          <p class="eyebrow">Markdown Driven Blog</p>
          <h1>{html.escape(config["hero_title"])}</h1>
          <p class="hero-text">{html.escape(config["hero_description"])}</p>
          <div class="hero-actions">
            <a class="button button-primary" href="#sections">看板块</a>
            <a class="button button-secondary" href="#latest">看最新文章</a>
          </div>
        </div>
        <aside class="hero-panel">
          <p class="panel-label">写作规则</p>
          <ul class="panel-list">
            <li>你以后只需要往内容文件夹里放 Markdown。</li>
            <li>首页、分类页、文章页都会自动生成。</li>
            <li>当前已经预设 4 个板块，后面还能继续扩展。</li>
          </ul>
          <p class="panel-footnote">现在站点已经支持长期往里堆内容了。</p>
        </aside>
      </section>

      <section class="section" id="sections">
        <div class="section-heading" data-reveal>
          <p class="eyebrow">Sections</p>
          <h2>博客板块</h2>
        </div>
        <div class="section-grid">
          {section_cards(config["sections"], counts)}
        </div>
      </section>

      <section class="section" id="latest">
        <div class="section-heading" data-reveal>
          <p class="eyebrow">Latest Posts</p>
          <h2>最近更新</h2>
        </div>
        <div class="post-grid">
          {latest_cards}
        </div>
      </section>

      <section class="section">
        <div class="section-heading" data-reveal>
          <p class="eyebrow">Publishing Flow</p>
          <h2>以后怎么维护</h2>
        </div>
        <div class="guide-grid">
          {guide_cards}
        </div>
      </section>
    """

    return page_template(
        page_title=config["site_title"],
        description=config["site_description"],
        rel_prefix="./",
        hero_anchor="#sections",
        body=body,
        config=config,
    )


def render_category_page(
    config: dict[str, Any],
    section: dict[str, Any],
    posts: list[dict[str, Any]],
) -> str:
    cards = "".join(list_card(post) for post in posts)
    if not cards:
        cards = '<div class="empty-state" data-reveal>这个板块还没有文章，往对应文件夹里放入 Markdown 就会显示在这里。</div>'

    body = f"""
      <section class="hero" data-reveal>
        <div class="hero-copy">
          <p class="eyebrow">{html.escape(section["badge"])}</p>
          <h1>{html.escape(section["label"])}</h1>
          <p class="hero-text">{html.escape(section["description"])}</p>
          <div class="hero-actions">
            <a class="button button-primary" href="../index.html#latest">回首页看最新</a>
          </div>
        </div>
        <aside class="hero-panel">
          <p class="panel-label">适合写的内容</p>
          <div class="topic-list">
            {"".join(f"<span>{html.escape(item)}</span>" for item in section["topics"])}
          </div>
          <p class="panel-footnote">当前文章数：{len(posts)} 篇</p>
        </aside>
      </section>

      <section class="section">
        <div class="section-heading" data-reveal>
          <p class="eyebrow">Posts</p>
          <h2>{html.escape(section["label"])}文章列表</h2>
        </div>
        <div class="post-list">
          {cards}
        </div>
      </section>
    """

    return page_template(
        page_title=section["label"],
        description=section["description"],
        rel_prefix="../",
        hero_anchor="#sections",
        body=body,
        config=config,
    )


def render_post_page(config: dict[str, Any], post: dict[str, Any]) -> str:
    tags_html = ""
    if post["section_topics"]:
        tags_html = "".join(f"<span>{html.escape(item)}</span>" for item in post["section_topics"][:4])

    body = f"""
      <div class="article-page" data-reveal>
        <a class="back-link" href="../../categories/{post["section_slug"]}.html">← 返回{html.escape(post["section_label"])}板块</a>
        <p class="eyebrow">{html.escape(post["section_badge"])}</p>
        <h1>{html.escape(post["title"])}</h1>
        <div class="article-meta">
          <span class="post-chip">{html.escape(post["section_label"])}</span>
          <span class="count-pill">{html.escape(post["date_display"])}</span>
        </div>
        <p class="article-lead">{html.escape(post["summary"])}</p>
        <div class="tag-list">{tags_html}</div>
        <div class="article-body">
          {post["html_body"]}
        </div>
      </div>
    """

    return page_template(
        page_title=post["title"],
        description=post["summary"],
        rel_prefix="../../",
        hero_anchor="#sections",
        body=body,
        config=config,
    )


def collect_posts(config: dict[str, Any]) -> list[dict[str, Any]]:
    posts: list[dict[str, Any]] = []
    sections = {section["slug"]: section for section in config["sections"]}

    for section_slug, section in sections.items():
        source_dir = CONTENT_DIR / section_slug
        source_dir.mkdir(parents=True, exist_ok=True)

        for md_file in sorted(source_dir.glob("*.md")):
            raw_text = md_file.read_text(encoding="utf-8")
            metadata, body_text = parse_front_matter(raw_text)
            lines = body_text.splitlines()
            title = metadata.get("title") or first_heading(lines) or md_file.stem
            content_without_heading = "\n".join(strip_first_heading(lines)).strip()
            if not content_without_heading:
                content_without_heading = body_text.strip()

            modified = dt.datetime.fromtimestamp(md_file.stat().st_mtime)
            date_display, sort_date = format_date(metadata.get("date"), modified)
            summary = metadata.get("summary") or plain_excerpt(content_without_heading or body_text)

            posts.append(
                {
                    "source_path": md_file,
                    "slug": slugify(md_file.stem),
                    "title": title,
                    "summary": summary,
                    "date_display": date_display,
                    "sort_date": sort_date,
                    "section_slug": section_slug,
                    "section_label": section["label"],
                    "section_badge": section["badge"],
                    "section_topics": section["topics"],
                    "html_body": render_markdown(content_without_heading or body_text),
                }
            )

    posts.sort(key=lambda item: (item["sort_date"], item["title"]), reverse=True)
    return posts


def write_output(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def build() -> None:
    config = load_config()
    POSTS_DIR.mkdir(exist_ok=True)
    CATEGORIES_DIR.mkdir(exist_ok=True)

    shutil.rmtree(POSTS_DIR, ignore_errors=True)
    shutil.rmtree(CATEGORIES_DIR, ignore_errors=True)
    POSTS_DIR.mkdir(parents=True, exist_ok=True)
    CATEGORIES_DIR.mkdir(parents=True, exist_ok=True)

    posts = collect_posts(config)
    counts = {section["slug"]: 0 for section in config["sections"]}
    grouped: dict[str, list[dict[str, Any]]] = {section["slug"]: [] for section in config["sections"]}

    for post in posts:
        counts[post["section_slug"]] += 1
        grouped[post["section_slug"]].append(post)
        output_path = POSTS_DIR / post["section_slug"] / f"{post['slug']}.html"
        write_output(output_path, render_post_page(config, post))

    for section in config["sections"]:
        page_path = CATEGORIES_DIR / f"{section['slug']}.html"
        write_output(page_path, render_category_page(config, section, grouped[section["slug"]]))

    write_output(ROOT / "index.html", render_index(config, posts, counts))


if __name__ == "__main__":
    build()
