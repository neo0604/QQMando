#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
QQMando 周报推送 - 企业微信群机器人
用法：
    python3 push_wecom.py                  # 推送当前最新一期
    python3 push_wecom.py 2026-W16         # 推送指定一期
环境变量：
    WECOM_WEBHOOK       必填，企业微信群机器人 webhook URL
    QQMANDO_WEEK        可选，指定期号
"""
import json
import os
import re
import sys
import urllib.request
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data"
SITE_URL = "https://neo0604.github.io/QQMando/"


def pick_latest_week() -> str:
    pat = re.compile(r"^\d{4}-W\d{1,2}$")
    files = sorted([p for p in DATA_DIR.glob("*.json") if pat.match(p.stem)])
    if not files:
        raise SystemExit("❌ data/ 下没有任何期号数据（YYYY-Www.json）")
    return files[-1].stem


def build_markdown(data: dict) -> tuple[str, str]:
    """企业微信 markdown 消息体：title 用于日志，body 是真正推送内容（最多 4096 字符）"""
    meta = data.get("meta", {})
    issue = meta.get("issueNo", "新一期")
    window = meta.get("rangeLabel", "")
    headline = meta.get("headline", "")
    lead = meta.get("lead", "")

    hot = data.get("hotContent", [])[:3]
    qq = data.get("qqStrategy", {})
    core = qq.get("coreJudgment", "")
    p0_actions = [a for a in qq.get("actions", []) if a.get("priority") == "P0"]
    policies = data.get("policyCompare", [])[:3]

    log_title = f"📊 QQMando {issue}已更新"

    # 企业微信 markdown 支持有限，用 ### 和 > 效果最好
    # 颜色标记支持：<font color="info|warning|comment">text</font>
    lines = []
    lines.append(f"# 📊 QQMando <font color=\"warning\">{issue}</font>已更新")
    lines.append(f"> {window}")
    lines.append("")
    lines.append(f"### 📰 {headline}")
    lines.append(f"<font color=\"comment\">{lead}</font>")
    lines.append("")

    if hot:
        lines.append("### 🎬 本周 TOP 3 爆款")
        for i, h in enumerate(hot, 1):
            t = h.get("title", "—")
            plat = h.get("platform", "")
            peak = h.get("peakMetric") or h.get("plays", "—")
            genre = h.get("genre", "")
            lines.append(f"**{i}. {t}**")
            lines.append(f"> <font color=\"comment\">{plat} · {genre}</font>")
            lines.append(f"> <font color=\"info\">🔥 {peak}</font>")
            lines.append("")

    if policies:
        lines.append("### ⚡ 关键政策动向")
        for p in policies:
            plat = p.get("platform", "—")
            sig = p.get("signature") or p.get("focus", "")
            note = p.get("note", "")
            new_tag = "🆕 " if p.get("isNew") else ""
            main = sig if sig else note
            lines.append(f"- {new_tag}**{plat}**：{main}")
            if note and note != sig:
                lines.append(f"  > <font color=\"comment\">{note}</font>")
        lines.append("")

    if core:
        lines.append("### 🎯 QQ 视角 · 核心判断")
        lines.append(f"> {core}")
        lines.append("")

    if p0_actions:
        lines.append("**P0 优先行动：**")
        for a in p0_actions:
            lines.append(f"- <font color=\"warning\">**{a.get('action','')}**</font>")
            lines.append(f"  > {a.get('rationale','')}")
        lines.append("")

    lines.append(f"👉 [**查看完整周报**]({SITE_URL})")
    lines.append(f"<font color=\"comment\">发送时间：{datetime.now().strftime('%Y-%m-%d %H:%M')}</font>")

    body = "\n".join(lines)
    # 企业微信 markdown 单条限制 4096 字节，截断保护
    if len(body.encode("utf-8")) > 4000:
        body = body[:2000] + f"\n\n...\n\n👉 [查看完整周报]({SITE_URL})"
    return log_title, body


def push_wecom(markdown_body: str, webhook: str) -> dict:
    payload = {
        "msgtype": "markdown",
        "markdown": {"content": markdown_body},
    }
    data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    req = urllib.request.Request(webhook, data=data, method="POST")
    req.add_header("Content-Type", "application/json")
    with urllib.request.urlopen(req, timeout=10) as resp:
        return json.loads(resp.read().decode("utf-8"))


def main():
    webhook = os.environ.get("WECOM_WEBHOOK", "").strip()
    if not webhook or "qyapi.weixin.qq.com" not in webhook:
        print("❌ 请设置环境变量 WECOM_WEBHOOK 为企业微信群机器人 webhook URL")
        sys.exit(1)

    week = os.environ.get("QQMANDO_WEEK") or (sys.argv[1] if len(sys.argv) > 1 else pick_latest_week())
    data_file = DATA_DIR / f"{week}.json"
    if not data_file.exists():
        print(f"❌ 找不到期号文件：{data_file}")
        sys.exit(1)

    with open(data_file, "r", encoding="utf-8") as f:
        data = json.load(f)

    log_title, body = build_markdown(data)
    print(f"📤 准备推送：{log_title}")
    print(f"📏 内容长度：{len(body.encode('utf-8'))} bytes")

    result = push_wecom(body, webhook)
    if result.get("errcode") == 0:
        print(f"✅ 推送成功")
    else:
        print(f"⚠️ 推送失败：{result}")
        sys.exit(2)


if __name__ == "__main__":
    main()
