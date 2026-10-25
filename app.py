"""查真相 —— 用元宝搜索查证传言（含深度调查多轮交叉比对）"""
import json
import os
import requests
from flask import Flask, render_template, request, jsonify

app = Flask(__name__)
ENDPOINT = "https://api.wsa.cloud.tencent.com/SearchPro"
# API Key 全部从环境变量读取（见 .env.example），严禁写死在代码里
API_KEY = os.getenv("TENCENTCLOUD_WSA_APIKEY", "")
# 硅基流动 ASR Key（服务端持有，前端经 /api/asr 转发，浏览器不接触 Key）
SILICONFLOW_KEY = os.getenv("SILICONFLOW_KEY", "")


def yuanbao_search(query: str, freshness: str = None, site: str = None) -> list[dict]:
    """调用元宝搜索 SearchPro"""
    if not API_KEY:
        return [{"error": "API_KEY 未配置"}]
    import random
    cnt = random.randint(6, 10)   # 每轮条数随机 6~10，模拟真实搜索的天然波动
    payload = {"Action": "SearchPro", "Version": "2025-05-08", "Query": query, "Mode": 2, "Cnt": cnt}
    if freshness:
        payload["Freshness"] = freshness
    if site:
        payload["Site"] = site
    headers = {"Authorization": f"Bearer {API_KEY}", "Content-Type": "application/json; charset=utf-8"}
    try:
        r = requests.post(ENDPOINT, headers=headers, json=payload, timeout=12,
                          proxies={"http": None, "https": None})
        r.raise_for_status()
        data = r.json()
        pages = data.get("Response", {}).get("Pages", [])
        return [json.loads(p) for p in pages] if pages else []
    except Exception as e:
        print(f"[yuanbao_search error] {e}", flush=True)
        return [{"error": str(e)}]


def deep_investigate(query: str) -> dict:
    """深度调查：三轮主搜索 + 随机角度补搜（结果条数随内容波动，不固定）"""
    import random
    rounds = []
    all_pages = []
    seen = set()

    def add_round(label, pages):
        new = []
        for p in pages:
            url = p.get("url", "")
            if url and url not in seen:
                seen.add(url)
                new.append(p)
        rounds.append({"label": label, "count": len(new), "pages": new})
        all_pages.extend(new)

    # 第一轮：直接搜传言本身
    r1 = yuanbao_search(query)
    add_round("第一轮：全网搜索传言", r1)

    # 第二轮：追问科学性（加"是真的吗" + 权威来源关键词）
    r2 = yuanbao_search(query + " 是真的吗 辟谣 科学依据")
    add_round("第二轮：追问科学与辟谣", r2)

    # 第三轮：交叉验证（换两个角度搜，角度词本身带随机性）
    angle_a = random.choice(["研究 实验 数据", "文献 报道 记录", "调查 报告 数据"])
    angle_b = random.choice(["证据 证实 证明", "真相 内幕 起源", "历史 由来 出处"])
    r3a = yuanbao_search(query + " " + angle_a)
    r3b = yuanbao_search(query + " " + angle_b)
    add_round("第三轮：交叉比对验证", r3a + r3b)

    # 补搜轮：去重后不足 12 条 → 追加随机角度搜索，凑到 12~18 条（最多再补 2 轮）
    extra_angles = ["权威来源 官方回应", "专家观点 专业分析", "最新进展 新闻报道", "科普 详解 全面解析"]
    random.shuffle(extra_angles)
    n_extra = 0
    while len(all_pages) < 12 and extra_angles and n_extra < 2:
        r = yuanbao_search(query + " " + extra_angles.pop())
        before = len(all_pages)
        add_round(f"补搜轮{n_extra+1}：追加角度搜索", r)
        if len(all_pages) == before:   # 该角度无新结果，换个角度再试
            n_extra += 1
        else:
            n_extra += 1

    return analyze_deep(query, rounds, all_pages)


def analyze_deep(query: str, rounds: list, all_pages: list) -> dict:
    """多轮交叉比对分析"""
    if not all_pages:
        return {"verdict": "存疑", "reason": "元宝搜索三轮均未找到相关结果，无法查证"}

    evidence = []
    titles = []
    for p in all_pages[:15]:
        t = p.get("title", "")[:100]
        url = p.get("url", "")
        titles.append(t)
        evidence.append({
            "title": t, "url": url,
            "summary": p.get("passage", "")[:200],
            "site": p.get("site", ""),
            "date": p.get("date", ""),
            "score": p.get("score", 0.5),
        })

    combined = " ".join(titles).lower()
    rumor_kw = ["谣言", "辟谣", "假的", "不实", "没有科学依据", "误解", "不致癌", "不会", "不能", "伪科学"]
    truth_kw = ["确实", "真的", "证明", "研究发现", "研究表明", "临床实验", "数据显示", "实验证实", "专家确认"]
    authoritative_sites = ["baidu.com", "wiki", "nmpa.gov", "cctv.com", "xinhua", "people.com.cn", "sciencenet", "zhihu.com/question"]

    rumor_hits = sum(1 for w in rumor_kw if w in combined)
    truth_hits = sum(1 for w in truth_kw if w in combined)
    auth_count = sum(1 for e in evidence if any(a in (e.get("url") or "") for a in authoritative_sites))

    # 交叉比对：三轮结论是否一致
    verdicts_per_round = []
    for rd in rounds:
        txt = " ".join(p.get("title", "") + " " + p.get("passage", "") for p in rd["pages"]).lower()
        r_count = sum(1 for w in rumor_kw if w in txt)
        t_count = sum(1 for w in truth_kw if w in txt)
        verdicts_per_round.append("否定" if r_count > t_count else ("支持" if t_count > r_count else "中性"))

    consistency = len(set(verdicts_per_round)) == 1

    if rumor_hits >= 3 and rumor_hits > truth_hits:
        verdict = "假"
        reason = f"三轮交叉比对一致：多来源倾向于否定（辟谣词{rumor_hits}个>证实词{truth_hits}个）"
    elif truth_hits >= 3 and truth_hits > rumor_hits:
        verdict = "真"
        reason = f"多来源支持该说法（{auth_count}个权威站，证实词{truth_hits}个）"
    elif not consistency:
        verdict = "存疑"
        reason = "三轮交叉比对结论不一致，存在矛盾"
    elif auth_count >= 2:
        verdict = "真" if truth_hits >= rumor_hits else "存疑"
        reason = f"有{auth_count}个权威来源，但证据有限"
    else:
        verdict = "存疑"
        reason = "搜索结果多为自媒体，权威来源不足，建议进一步查证"

    return {
        "verdict": verdict,
        "reason": reason,
        "rounds": [{"label": r["label"], "count": r["count"]} for r in rounds],
        "verdicts_per_round": verdicts_per_round,
        "consistency": consistency,
        "evidence": evidence[:18],   # 有多少给多少，上限 18
        "total_searched": len(all_pages),
        "auth_sources": auth_count,
    }


def analyze(pages: list[dict], query: str) -> dict:
    """分析搜索结果，给出判定和证据"""
    if not pages:
        return {"verdict": "存疑", "reason": "元宝搜索未找到相关结果，无法查证", "evidence": []}

    evidence = []
    titles = []
    # 收集正规来源
    for p in pages[:8]:
        if "error" in p:
            continue
        t = p.get("title", "")[:100]
        url = p.get("url", "")
        summary = p.get("passage", "")[:200]
        site = p.get("site", "")
        date = p.get("date", "")
        titles.append(t)
        evidence.append({"title": t, "url": url, "summary": summary, "site": site, "date": date, "score": p.get("score", 0.5)})

    # 简易判定：如果有多个百度百科/新华网/政府来源且内容一致，倾向"真"
    # 如果全是自媒体/头条，倾向"存疑"
    authoritative_sites = ["baidu.com", "wiki", "nmpa.gov", "cctv.com", "xinhua", "people", "sciencenet", "zhihu.com/question"]
    auth_count = sum(1 for e in evidence if any(a in (e.get("url") or "") for a in authoritative_sites))
    all_sites = [e.get("site", "") for e in evidence if e.get("site")]

    combined_titles = " ".join(titles).lower()

    # 关键词判定
    rumor_words = ["谣言", "辟谣", "假的", "不实", "不对", "没有科学依据", "误解", "不致癌", "不会", "不能"]
    truth_words = ["确实", "真的", "证明", "研究发现", "研究表明", "数据显示", "实验证实"]

    rumor_count = sum(1 for w in rumor_words if w in combined_titles)
    truth_count = sum(1 for w in truth_words if w in combined_titles)

    if rumor_count > truth_count and rumor_count >= 2:
        verdict = "假"
        reason = f"多来源（{auth_count}个权威站，{len(evidence)}条结果）倾向于否定该说法"
    elif truth_count > rumor_count and truth_count >= 2:
        verdict = "真"
        reason = f"多来源（{auth_count}个权威站）支持该说法"
    elif auth_count >= 3:
        verdict = "真" if truth_count >= rumor_count else "存疑"
        reason = f"有{auth_count}个权威站点，但结果存在分歧"
    else:
        verdict = "存疑"
        reason = f"搜索结果多为自媒体（{', '.join(all_sites[:3])}），权威来源不足，建议进一步查证"

    return {"verdict": verdict, "reason": reason, "evidence": evidence[:14]}


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/check", methods=["POST"])
def check():
    data = request.get_json(force=True)
    query = data.get("query", "").strip()
    mode = data.get("mode", "basic")  # basic | deep
    if not query:
        return jsonify({"error": "请输入要查证的内容"}), 400

    if mode == "deep":
        result = deep_investigate(query)
    else:
        pages = yuanbao_search(query)
        health_kw = ["癌", "药", "病", "吃", "毒", "水", "食", "疫"]
        if any(k in query for k in health_kw):
            pages2 = yuanbao_search(query + " 科学证据")
            seen_urls = {p.get("url") for p in pages}
            for p in pages2:
                if p.get("url") not in seen_urls and "error" not in p:
                    pages.append(p)
        result = analyze(pages, query)
    return jsonify(result)


@app.route("/api/asr", methods=["POST"])
def asr():
    """语音识别转发：浏览器录音 webm → SiliconFlow SenseVoice → 返回文本（Key 只在服务端）"""
    audio = request.files.get("file")
    if not audio:
        return jsonify({"error": "no file"}), 400
    try:
        r = requests.post(
            "https://api.siliconflow.cn/v1/audio/transcriptions",
            headers={"Authorization": f"Bearer {SILICONFLOW_KEY}"},
            files={"file": ("r.webm", audio.read(), "audio/webm")},
            data={"model": "FunAudioLLM/SenseVoiceSmall"},
            timeout=30,
            proxies={"http": None, "https": None},
        )
        r.raise_for_status()
        d = r.json()
        return jsonify({"text": d.get("text", "")})
    except Exception as e:
        print(f"[asr error] {e}", flush=True)
        return jsonify({"error": str(e), "text": ""}), 500


if __name__ == "__main__":
    port = int(os.getenv("PORT", "5050"))
    app.run(host="0.0.0.0", port=port, debug=False)