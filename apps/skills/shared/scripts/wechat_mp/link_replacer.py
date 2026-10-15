"""引用链接替换：将 HTML 中的本地 .md 链接替换为已发布的公众号文章 URL

工作流：
  1. sync-links 命令：从微信 API 拉取已发布文章（≥ PUBLISH_START），
     通过两层匹配（草稿标题 → H1 标题）自动建立 stem→URL 映射
  2. draft 流程：md→html 转换后，自动将 href="xxx.md" 替换为对应的公众号 URL
"""

import json
import re
from datetime import datetime, timezone, timedelta
from pathlib import Path

from wechat_mp import WeChatClient

# 映射表文件：articles/article_links.json
LINKS_PATH = Path(__file__).parent.parent.parent.parent / "articles" / "article_links.json"

# 只处理 2026-06-20 及之后发布的文章
PUBLISH_START = datetime(2026, 6, 20, tzinfo=timezone(timedelta(hours=8)))


def load_mapping() -> dict:
    """加载映射表，返回 {stem: {title, url}} 字典"""
    if LINKS_PATH.exists():
        try:
            return json.loads(LINKS_PATH.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, KeyError):
            pass
    return {}


def save_mapping(mapping: dict):
    """保存映射表到 JSON 文件（保持发布时间顺序，新文章在最前面）"""
    LINKS_PATH.parent.mkdir(parents=True, exist_ok=True)
    LINKS_PATH.write_text(
        json.dumps(mapping, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def replace_md_links(html: str, mapping: dict) -> tuple[str, int]:
    """将 HTML 中 href 指向 .md 文件的链接替换为映射表中的公众号 URL，
    同时将链接文字替换为公众号文章标题。

    Args:
        html: 待替换的 HTML 内容
        mapping: {stem: {title, url}} 映射表

    Returns:
        (替换后的 HTML, 替换次数)
    """
    count = 0

    def _replace(m):
        nonlocal count
        href = m.group(1)
        # 提取 md 文件名（去掉目录路径），再去掉 .md 后缀得到 stem
        stem = Path(href).stem
        if stem in mapping and "url" in mapping[stem]:
            count += 1
            title = mapping[stem].get("title", m.group(2))
            return f'<a href="{mapping[stem]["url"]}">{title}</a>'
        return m.group(0)

    result = re.sub(r'<a\s+href="([^"]*?\.md)"[^>]*>(.*?)</a>', _replace, html)
    return result, count


def _extract_h1(md_path: Path) -> str:
    """从 MD 文件提取 H1 标题"""
    try:
        text = md_path.read_text(encoding="utf-8-sig")
        m = re.search(r'^#\s+(.*)', text, re.MULTILINE)
        return m.group(1).strip() if m else ""
    except Exception:
        return ""


def _load_draft_metas() -> dict[str, dict]:
    """扫描 articles/**/draft_meta.json，返回 {media_id: {stem, title}} 索引"""
    articles_dir = LINKS_PATH.parent
    result = {}
    for meta_path in articles_dir.glob("**/draft_meta.json"):
        try:
            meta = json.loads(meta_path.read_text(encoding="utf-8"))
            media_id = meta.get("media_id", "")
            if media_id:
                result[media_id] = {
                    "stem": meta.get("stem", meta_path.parent.name),
                    "title": meta.get("title", ""),
                }
        except (json.JSONDecodeError, KeyError):
            continue
    return result


def _build_h1_index(docs_dir: Path) -> dict[str, str]:
    """扫描 docs_dir 下所有 .md 文件，构建 {H1标题(小写): stem} 索引"""
    index = {}
    for md_file in docs_dir.rglob("*.md"):
        if md_file.name == "README.md":
            continue
        h1 = _extract_h1(md_file)
        if h1:
            index[h1.lower()] = md_file.stem
    return index


def sync_from_published(
    client: WeChatClient,
    docs_dir: Path,
    force: bool = False,
) -> dict:
    """从已发布文章列表同步映射表（两层匹配策略）

    匹配优先级：
      1. 草稿标题匹配（draft_meta.json 中的 title，即发给公众号的实际标题）
      2. H1 标题匹配（MD 文件的一级标题，作为兜底）

    只处理 2026-06-21 及之后发布的文章。

    Args:
        client: WeChatClient 实例
        docs_dir: 本地 MD 文件根目录（递归扫描）
        force: 为 True 时覆盖已有映射条目；为 False 时只添加新条目

    Returns:
        {"new": 新增数量, "updated": 更新数量, "skipped": 跳过数量,
         "by_draft_title": 草稿标题匹配数, "by_h1": H1匹配数}
    """
    mapping = load_mapping()
    start_ts = PUBLISH_START.timestamp()

    # 分页拉取全部已发布文章，过滤日期
    published = []
    offset = 0
    while True:
        data = client.list_articles(offset=offset, count=20)
        items = data.get("item", [])
        for item in items:
            if item.get("update_time", 0) < start_ts:
                continue
            news = item.get("content", {}).get("news_item", [{}])[0]
            title = news.get("title", "").strip()
            url = news.get("url", "")
            if title and url:
                published.append({"title": title, "url": url})
        if len(items) < 20:
            break
        offset += 20

    # 构建两层匹配索引
    draft_metas = _load_draft_metas()                     # media_id → {stem, title}
    draft_title_to_stem = {                               # 草稿标题(小写) → stem
        v["title"].lower(): v["stem"]
        for v in draft_metas.values() if v["title"]
    }
    h1_to_stem = _build_h1_index(docs_dir)                # H1标题(小写) → stem

    # 逐篇匹配
    stats = {"new": 0, "updated": 0, "skipped": 0,
             "by_draft_title": 0, "by_h1": 0}

    for article in published:
        stem = None
        match_by = None

        # 层1: 草稿标题匹配（draft_meta.json 中存的公众号标题）
        stem = draft_title_to_stem.get(article["title"].lower())
        if stem:
            match_by = "by_draft_title"

        # 层2: H1 标题匹配（兜底）
        if not stem:
            stem = h1_to_stem.get(article["title"].lower())
            if stem:
                match_by = "by_h1"

        if not stem:
            stats["skipped"] += 1
            continue

        if stem in mapping and not force:
            stats["skipped"] += 1
            continue

        if stem in mapping:
            stats["updated"] += 1
        else:
            stats["new"] += 1

        if match_by:
            stats[match_by] += 1

        mapping[stem] = {
            "title": article["title"],
            "url": article["url"],
        }

    if stats["new"] + stats["updated"] > 0:
        save_mapping(mapping)
    return stats
