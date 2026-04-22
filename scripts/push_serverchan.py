#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
QQMando 周报推送 - Server酱 Turbo
用法：
    python3 push_serverchan.py                  # 推送当前最新一期
    python3 push_serverchan.py 2026-W16         # 推送指定一期
环境变量：
    SERVERCHAN_SENDKEY  必填
    QQMANDO_WEEK        可选，指定期号（优先级高于命令行参数）
"""
import json
import os
import sys
import urllib.request
import urllib.parse
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data"
SITE_URL = "https://neo0604.github.io/QQMando/"


def pick_latest_week() -> str:
    """data/ 下找最新的 YYYY-Www.json（排除 index.json 等辅助文件）"""
    import re
    pat = re.compile(r"^\d{4}-W\d{1,2}$")
    files = sorted([p for p in DATA_DIR.glob("*.json") if pat.match(p.stem)])
    if not files:
        raise SystemExit("❌ data/ 下没有任何期号数据（YYYY-Www.json）")
    return files[-1].stem  # e.g. 2026-W16


def build_markdown(data: dict) -> tuple[str, str]:
    """返回 (title, markdown_body)"""
    meta = data.get("meta", {})
    issue = meta.get("issueNo", "新一期")
    window = meta.get("rangeLabel", "")
    headline = meta.get("headline", "")
    lead = meta.get("lead", "")

    # TOP 3 爆款
    hot = data.get("hotContent", [])[:3]
    # QQ 策略核心判断 + P0 行动
    qq = data.get("qqStrategy", {})
    core = qq.get("coreJudgment", "")
    p0_actions = [a for a in qq.get("actions", []) if a.get("priority") == "P0"]

    # 关键政策（取前 3 条）
    policies = data.get("policyCompare", [])[:3]

    title = f"📊 QQMando {issue}已更新"

    lines = []
    lines.append(f"## 📰 {headline}")
    lines.append("")
    lines.append(f"> {lead}")
    lines.append("")
    lines.append(f"**窗口期**：{window}")
    lines.append("")

    if hot:
        lines.append("---")
        lines.append("## 🎬 本周 TOP 3 爆款")
        lines.append("")
        for i, h in enumerate(hot, 1):
            t = h.get("title", "—")
            plat = h.get("platform", "")
            peak = h.get("peakMetric") or h.get("plays", "—")
            genre = h.get("genre", "")
            lines.append(f"**{i}. {t}**")
            lines.append(f"　{plat} · {genre} · {peak}")
            synopsis = h.get("synopsis", "")
            if synopsis:
                # 控制长度
                s = synopsis if len(synopsis) <= 60 else synopsis[:60] + "…"
                lines.append(f"　_{s}_")
            lines.append("")

    if policies:
        lines.append("---")
        lines.append("## ⚡ 关键政策动向")
        lines.append("")
        for p in policies:
            plat = p.get("platform", "—")
            sig = p.get("signature") or p.get("focus", "")
            note = p.get("note", "")
            is_new = "🆕 " if p.get("isNew") else ""
            main = sig if sig else note
            tail = f"（{note}）" if (note and sig and note != sig) else ""
            lines.append(f"- {is_new}**{plat}**：{main}{tail}")
        lines.append("")

    if core or p0_actions:
        lines.append("---")
        lines.append("## 🎯 QQ 视角")
        lines.append("")
        if core:
            lines.append(f"> {core}")
            lines.append("")
        if p0_actions:
            lines.append("**P0 优先行动：**")
            for a in p0_actions:
                lines.append(f"- **{a.get('action','')}** — {a.get('rationale','')}")
            lines.append("")

    lines.append("---")
    lines.append(f"👉 **[查看完整周报]({SITE_URL})**")
    lines.append("")
    lines.append(f"_发送时间：{datetime.now().strftime('%Y-%m-%d %H:%M')}_")

    return title, "\n".join(lines)


def push_serverchan(title: str, body: str, sendkey: str) -> dict:
    """Server酱 Turbo 推送"""
    url = f"https://sctapi.ftqq.com/{sendkey}.send"
    payload = urllib.parse.urlencode({
        "title": title,
        "desp": body,
    }).encode("utf-8")
    req = urllib.request.Request(url, data=payload, method="POST")
    req.add_header("Content-Type", "application/x-www-form-urlencoded")
    with urllib.request.urlopen(req, timeout=10) as resp:
        return json.loads(resp.read().decode("utf-8"))


def main():
    sendkey = os.environ.get("SERVERCHAN_SENDKEY", "").strip()
    if not sendkey:
        print("❌ 请设置环境变量 SERVERCHAN_SENDKEY")
        sys.exit(1)

    week = os.environ.get("QQMANDO_WEEK") or (sys.argv[1] if len(sys.argv) > 1 else pick_latest_week())
    data_file = DATA_DIR / f"{week}.json"
    if not data_file.exists():
        print(f"❌ 找不到期号文件：{data_file}")
        sys.exit(1)

    with open(data_file, "r", encoding="utf-8") as f:
        data = json.load(f)

    title, body = build_markdown(data)
    print(f"📤 准备推送：{title}")
    print("─" * 40)
    print(body)
    print("─" * 40)

    result = push_serverchan(title, body, sendkey)
    if result.get("code") == 0 or result.get("data", {}).get("pushid"):
        print(f"✅ 推送成功 pushid={result.get('data', {}).get('pushid', '?')}")
    else:
        print(f"⚠️ 推送返回：{result}")
        sys.exit(2)


if __name__ == "__main__":
    main()
