#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
热梗工作台 - 多平台热搜数据抓取脚本 (云端版)
支持平台: 抖音、微博、B站、知乎、百度、头条
数据输出: data/data.js (供前端 dashboard 直接加载)

API 源 (按优先级):
  1. tenapi.cn  - 免费公开 API，响应快
  2. vvhan API  - 备用源
"""

import json
import time
import hashlib
import os
import sys
import random
from datetime import datetime, timezone, timedelta

try:
    import requests
except ImportError:
    print("[ERROR] requests 库未安装，请运行: pip install requests")
    sys.exit(1)

# ============================================================
# 配置区
# ============================================================

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
OUTPUT_DIR = os.path.join(SCRIPT_DIR, "data")
OUTPUT_FILE = os.path.join(OUTPUT_DIR, "data.js")

# 多平台 API 配置 (双源备份，按顺序尝试)
API_SOURCES = {
    "douyin": {
        "name": "抖音热搜",
        "color": "#000000",
        "icon": "tiktok",
        "apis": [
            {"name": "tenapi", "url": "https://tenapi.cn/v2/douyinhot", "field": "data", "titleKey": "name", "hotKey": "hot"},
            {"name": "vvhan",  "url": "https://api.vvhan.com/api/hotlist/douyin", "field": "data", "titleKey": "title", "hotKey": "hot"},
        ],
    },
    "weibo": {
        "name": "微博热搜",
        "color": "#E6162D",
        "icon": "weibo",
        "apis": [
            {"name": "tenapi", "url": "https://tenapi.cn/v2/weibohot", "field": "data", "titleKey": "name", "hotKey": "hot"},
            {"name": "vvhan",  "url": "https://api.vvhan.com/api/hotlist/wbHot", "field": "data", "titleKey": "title", "hotKey": "hot"},
        ],
    },
    "bilibili": {
        "name": "B站热搜",
        "color": "#FB7299",
        "icon": "bilibili",
        "apis": [
            {"name": "tenapi", "url": "https://tenapi.cn/v2/bilihot", "field": "data", "titleKey": "name", "hotKey": "hot"},
            {"name": "vvhan",  "url": "https://api.vvhan.com/api/hotlist/bili", "field": "data", "titleKey": "title", "hotKey": "hot"},
        ],
    },
    "zhihu": {
        "name": "知乎热榜",
        "color": "#0066FF",
        "icon": "zhihu",
        "apis": [
            {"name": "tenapi", "url": "https://tenapi.cn/v2/zhihuhot", "field": "data", "titleKey": "name", "hotKey": "hot"},
            {"name": "vvhan",  "url": "https://api.vvhan.com/api/hotlist/zhihu", "field": "data", "titleKey": "title", "hotKey": "hot"},
        ],
    },
    "baidu": {
        "name": "百度热搜",
        "color": "#2932E1",
        "icon": "baidu",
        "apis": [
            {"name": "tenapi", "url": "https://tenapi.cn/v2/baiduhot", "field": "data", "titleKey": "name", "hotKey": "hot"},
            {"name": "vvhan",  "url": "https://api.vvhan.com/api/hotlist/baidu", "field": "data", "titleKey": "title", "hotKey": "hot"},
        ],
    },
    "toutiao": {
        "name": "头条热搜",
        "color": "#FF5722",
        "icon": "toutiao",
        "apis": [
            {"name": "tenapi", "url": "https://tenapi.cn/v2/toutiaohot", "field": "data", "titleKey": "name", "hotKey": "hot"},
            {"name": "vvhan",  "url": "https://api.vvhan.com/api/hotlist/toutiao", "field": "data", "titleKey": "title", "hotKey": "hot"},
        ],
    },
}

REQUEST_TIMEOUT = 15
MAX_RETRIES = 2

# ============================================================
# 分类关键词
# ============================================================

CATEGORY_KEYWORDS = {
    "舞蹈挑战": ["舞", "扭", "跳", "挑战", "dance", "健身操", "律动", "卡点", "变装", "换装", "手势舞", "扭腰", "街舞", "广场舞"],
    "搞笑段子": ["搞笑", "段子", "梗", "名场面", "笑死", "哈哈", "沙雕", "整活", "抽象", "离谱", "绷不住"],
    "音乐热歌": ["歌", "曲", "音乐", "BGM", "翻唱", "原唱", "MV", "专辑", "演唱会", "说唱", "rap"],
    "影视综艺": ["电影", "电视剧", "综艺", "剧集", "番", "导演", "演员", "票房", "开播", "收官", "预告"],
    "社会热点": ["通报", "官方", "政策", "发布", "声明", "回应", "调查", "事故", "灾害", "预警"],
    "科技数码": ["AI", "芯片", "手机", "发布", "科技", "互联网", "算法", "大模型", "智能", "数码", "评测"],
    "游戏电竞": ["游戏", "电竞", "赛事", "通关", "攻略", "皮肤", "角色", "赛季", "排位", "MOBA"],
    "生活日常": ["美食", "旅游", "打卡", "探店", "穿搭", "美妆", "护肤", "减肥", "养生", "萌宠", "猫", "狗"],
}

# ============================================================
# 多闪匹配度评分
# ============================================================

CATEGORY_BASE_SCORE = {
    "舞蹈挑战": 90, "搞笑段子": 85, "音乐热歌": 80, "生活日常": 70,
    "影视综艺": 60, "游戏电竞": 55, "科技数码": 40, "社会热点": 30, "其他热点": 25,
}

DUOSHAN_BOOST_KEYWORDS = [
    "挑战", "舞", "扭", "跳", "翻唱", "变装", "模仿", "整活",
    "搞笑", "段子", "鬼畜", "穿搭", "种草", "打卡", "vlog", "教程",
    "滤镜", "特效", "bgm", "翻跳", "手势舞", "卡点",
]

DUOSHAN_PENALTY_KEYWORDS = [
    "通报", "政策", "事故", "声明", "调查", "回应", "公告", "法规",
    "犯罪", "遇难", "死亡", "起诉", "判决",
]

# ============================================================
# 多闪产品功能矩阵 (基于 2026.08 推广文档)
# ============================================================

DUOSHAN_SKILLS = {
    "今日塔罗": "【文字+生图】小火人抽塔罗牌，解读今日运势/测合盘适配度",
    "恋爱军师": "【文字+表情包】小火人分析聊天记录，给出高情商回复建议",
    "精灵法庭": "【文字+生图】小火人审判「罪行」，出恶搞诉状图",
    "TA啥意思": "【文字】小火人做阅读理解，翻译导师/领导/crush的潜台词",
    "取名大师": "【文字】小火人玩文字梗，谐音/拆字/姓氏联想生成名字",
    "做个表情包": "【生图】小火人识别图片+用户文案，生成可发送的表情包",
    "畅聊晚自习": "【文字】小火人出二选一争议话题，从意想不到角度抬杠接梗",
    "阅宠理解": "【文字+生图】小火人翻译宠物os，制作宠物表情包",
}

DUOSHAN_BRIEF_BLUEPRINTS = {
    "舞蹈挑战": {
        "zaiZai": "在仔仔世界用Open仔仔发起同名舞蹈挑战，仔仔替你@同好来PK",
        "skill": ["精灵法庭", "做个表情包"],
        "circle": ["舞蹈圈", "校园圈", "追星圈"],
        "event": "KOC通用",
        "script_templates": [
            "用仔仔还原「{title}」经典动作，在仔仔世界搭舞台场景，和好友仔仔牵手跳舞",
            "发起精灵法庭审判:「谁的{title}跳得最烂」，判罚仔仔世界罚站3分钟",
            "用「做个表情包」技能把{title}名场面做成仔仔表情包，聊天时甩出来",
        ],
        "tags": ["#多闪仔仔", "#有多闪不孤单", "#仔仔世界代餐文学"],
    },
    "搞笑段子": {
        "zaiZai": "用仔仔世界演绎「{title}」段子剧情，仔仔替你扮演搞笑角色",
        "skill": ["精灵法庭", "做个表情包", "畅聊晚自习"],
        "circle": ["搞笑圈", "校园圈", "二次元"],
        "event": "KOC通用",
        "script_templates": [
            "用仔仔还原「{title}」搞笑名场面，制作成二创小剧场发布",
            "发起精灵法庭：「{title}里谁最离谱」，请小火人当庭审判",
            "用「做个表情包」技能截取{title}最搞笑瞬间生成专属表情包",
        ],
        "tags": ["#多闪仔仔", "#开拍吧多闪", "#全员多闪qq人"],
    },
    "音乐热歌": {
        "zaiZai": "在仔仔世界搭舞台场景，仔仔翻唱「{title}」，邀请同好仔仔合唱",
        "skill": ["畅聊晚自习", "取名大师"],
        "circle": ["音乐圈", "追星圈", "校园圈"],
        "event": "KOC通用",
        "script_templates": [
            "用仔仔搭音乐会场景，仔仔翻唱{title}并@好友仔仔来听",
            "畅聊晚自习发起「{title} vs XX 哪首更上头」话题，让小火人抬杠",
            "用取名大师给粉丝起{title}相关的专属昵称",
        ],
        "tags": ["#多闪仔仔", "#有多闪不孤单", "#在多闪跨次元相遇"],
    },
    "影视综艺": {
        "zaiZai": "用仔仔世界复刻「{title}」影视名场面，仔仔平替角色演绎",
        "skill": ["TA啥意思", "恋爱军师"],
        "circle": ["影视圈", "追星圈", "二次元"],
        "event": "七夕/KOC通用",
        "script_templates": [
            "用仔仔还原「{title}」经典场景，制作成CP向二创小剧场",
            "TA啥意思：把{title}角色台词发给小火人做阅读理解",
            "恋爱军师分析{title}中CP的聊天记录，教你怎么和crush聊出同款氛围",
        ],
        "tags": ["#多闪仔仔", "#仔仔世界代餐文学", "#在多闪跨次元相遇"],
    },
    "社会热点": {
        "zaiZai": "在仔仔世界发起「{title}」话题讨论，仔仔替你表达观点",
        "skill": ["TA啥意思", "精灵法庭"],
        "circle": ["生活圈", "校园圈"],
        "event": "KOC通用",
        "script_templates": [
            "用仔仔世界搭讨论场景，仔仔们围绕「{title}」展开辩论",
            "精灵法庭：围绕{title}中的争议人物/事件发起审判",
            "Open仔仔替你发表对{title}的看法，吸引同观点的好友来交流",
        ],
        "tags": ["#多闪仔仔", "#有多闪不孤单"],
    },
    "科技数码": {
        "zaiZai": "用仔仔世界展演「{title}」相关内容，仔仔做科技解说",
        "skill": ["取名大师", "畅聊晚自习"],
        "circle": ["科技圈", "数码圈", "校园圈"],
        "event": "KOC通用",
        "script_templates": [
            "用仔仔搭科技发布会场景，仔仔介绍{title}相关内容",
            "畅聊晚自习发起「{title} A vs B 哪个更值得」话题讨论",
            "取名大师给{title}相关产品起搞笑昵称",
        ],
        "tags": ["#多闪仔仔", "#有多闪不孤单"],
    },
    "游戏电竞": {
        "zaiZai": "在仔仔世界搭游戏场景，仔仔还原「{title}」游戏高光",
        "skill": ["畅聊晚自习", "做个表情包"],
        "circle": ["游戏圈", "二次元", "校园圈"],
        "event": "七夕/KOC通用",
        "script_templates": [
            "用仔仔搭游戏场景，仔仔还原{title}高光操作",
            "畅聊晚自习发起游戏圈争议话题，让小火人加入抬杠",
            "用做个表情包把{title}游戏梗图做成仔仔表情包",
        ],
        "tags": ["#多闪仔仔", "#全员多闪qq人", "#在多闪跨次元相遇"],
    },
    "生活日常": {
        "zaiZai": "在仔仔世界复刻「{title}」生活场景，仔仔替你记录日常",
        "skill": ["今日塔罗", "做个表情包", "取名大师"],
        "circle": ["生活圈", "校园圈", "穿搭圈"],
        "event": "七夕/精灵学院/KOC通用",
        "script_templates": [
            "用仔仔还原{title}日常场景，仔仔陪你打卡生活仪式感",
            "今日塔罗：出门前让小火人抽牌看{title}是否适合今天尝试",
            "用做个表情包把{title}相关日常做成仔仔版表情包发动态",
        ],
        "tags": ["#多闪仔仔", "#有多闪不孤单"],
    },
    "其他热点": {
        "zaiZai": "在仔仔世界发起「{title}」话题活动，仔仔替你找到同好",
        "skill": ["畅聊晚自习", "TA啥意思"],
        "circle": ["综合圈"],
        "event": "KOC通用",
        "script_templates": [
            "用Open仔仔替你发起{title}相关话题，精准匹配同好交流",
            "TA啥意思：把{title}相关迷惑发言发给小火人解读",
            "仔仔世界搭场景讨论{title}，让仔仔们各抒己见",
        ],
        "tags": ["#多闪仔仔", "#有多闪不孤单"],
    },
}

QIXI_BOOST_CATEGORIES = ["影视综艺", "生活日常", "音乐热歌", "游戏电竞", "舞蹈挑战"]
QIXI_BOOST_TAGS = ["#多闪二次元相亲角", "#在多闪遇到正缘了", "#我在多闪办婚礼", "#在多闪实现嗑糖自由"]


# ============================================================
# 核心函数
# ============================================================

def calc_duoshan_score(title: str, category: str) -> int:
    score = CATEGORY_BASE_SCORE.get(category, 25)
    title_lower = title.lower()
    for kw in DUOSHAN_BOOST_KEYWORDS:
        if kw in title_lower:
            score += 5
    for kw in DUOSHAN_PENALTY_KEYWORDS:
        if kw in title_lower:
            score -= 15
    return max(0, min(100, score))


def classify_topic(title: str) -> str:
    title_lower = title.lower()
    for category, keywords in CATEGORY_KEYWORDS.items():
        for kw in keywords:
            if kw.lower() in title_lower:
                return category
    return "其他热点"


def _pick_blueprint(category: str) -> dict:
    return DUOSHAN_BRIEF_BLUEPRINTS.get(category, DUOSHAN_BRIEF_BLUEPRINTS["其他热点"])


def generate_duoshan_brief(title: str, platform: str, category: str,
                           duoshan_score: int) -> dict:
    bp = _pick_blueprint(category)

    skills_to_use = bp["skill"][:2] if duoshan_score >= 60 else bp["skill"][:1]
    skill_desc = []
    for sk in skills_to_use:
        skill_desc.append(f"{sk}（{DUOSHAN_SKILLS[sk][:12]}）")
    skill_str = " + ".join(skill_desc)

    circles = bp["circle"][:2]
    circle_str = "、".join(circles)

    title_lower = title.lower()
    qixi_kw = ["七夕", "情人节", "浪漫", "cp", "婚礼", "结婚", "恋爱", "配对", "相亲", "冷圈", "同好", "交友", "匹配", "正缘", "认亲"]
    if any(kw in title_lower for kw in qixi_kw):
        event = "七夕"
    elif category in QIXI_BOOST_CATEGORIES and duoshan_score >= 75:
        event = "七夕/KOC通用"
    else:
        event = bp["event"]

    script = random.choice(bp["script_templates"]).format(title=title)

    base_tags = bp["tags"].copy()
    if "七夕" in event:
        base_tags.extend(QIXI_BOOST_TAGS[:2])

    zaiZai_play = bp["zaiZai"]
    if "{title}" in zaiZai_play:
        zaiZai_play = zaiZai_play.replace("{title}", title)

    return {
        "zaiZaiPlay": zaiZai_play,
        "skillBind": f"技能：{skill_str}",
        "circle": f"圈层：{circle_str}",
        "event": event,
        "script": script,
        "tags": " ".join(base_tags[:4]),
    }


def generate_creative_idea(title: str, platform: str, category: str) -> str:
    bp = _pick_blueprint(category)
    scripts = bp.get("script_templates", [
        f"用仔仔世界把「{title}」玩出新花样，Open仔仔替你找到同好一起嗨"
    ])
    idea = random.choice(scripts).format(title=title)
    return idea[:60] + ("..." if len(idea) > 60 else "")


def format_hot(hot_num: int) -> str:
    if hot_num >= 100000000:
        return f"{hot_num / 100000000:.1f}亿"
    elif hot_num >= 10000:
        return f"{hot_num / 10000:.1f}万"
    elif hot_num > 0:
        return str(hot_num)
    return "-"


def parse_hot_value(raw) -> int:
    """将热度的各种格式转为整数"""
    if raw is None:
        return 0
    try:
        if isinstance(raw, (int, float)):
            return int(raw)
        s = str(raw).replace(",", "").strip()
        if "万" in s:
            return int(float(s.replace("万", "")) * 10000)
        if "亿" in s:
            return int(float(s.replace("亿", "")) * 100000000)
        return int(float(s))
    except (ValueError, TypeError):
        return 0


# ============================================================
# 数据抓取
# ============================================================

def fetch_single_source(platform_key: str, source_config: dict) -> list:
    """从单个平台抓取热搜 (依次尝试多个 API 源)"""
    for api_cfg in source_config["apis"]:
        items = _try_api(api_cfg, platform_key, source_config)
        if items:
            print(f"  [OK] {source_config['name']} (via {api_cfg['name']}): {len(items)} 条")
            return items
    print(f"  [FAIL] {source_config['name']}: 所有 API 源均失败")
    return []


def _try_api(api_cfg: dict, platform_key: str, source_config: dict) -> list:
    """尝试单个 API 端点"""
    url = api_cfg["url"]
    field = api_cfg.get("field", "data")
    title_key = api_cfg.get("titleKey", "title")
    hot_key = api_cfg.get("hotKey", "hot")

    for attempt in range(MAX_RETRIES + 1):
        try:
            headers = {
                "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                              "AppleWebKit/537.36 (KHTML, like Gecko) "
                              "Chrome/120.0.0.0 Safari/537.36",
                "Accept": "application/json, text/plain, */*",
            }
            resp = requests.get(url, headers=headers, timeout=REQUEST_TIMEOUT)
            resp.raise_for_status()
            data = resp.json()

            # 兼容不同的返回格式
            raw_items = []
            if field:
                raw_items = data.get(field, [])
                if isinstance(raw_items, dict):
                    raw_items = raw_items.get("data", raw_items.get("list", []))
            if not raw_items:
                raw_items = data.get("items", data.get("list", []))

            if not isinstance(raw_items, list):
                continue

            items = []
            for idx, item in enumerate(raw_items):
                title = item.get(title_key, "")
                if not title:
                    continue

                hot = parse_hot_value(item.get(hot_key, 0))
                link = item.get("url", item.get("link", item.get("mobil_url", "")))
                category = classify_topic(title)
                score = calc_duoshan_score(title, category)

                items.append({
                    "id": hashlib.md5(f"{platform_key}_{title}_{idx}".encode()).hexdigest()[:12],
                    "rank": idx + 1,
                    "title": title,
                    "hot": hot,
                    "hotDisplay": format_hot(hot),
                    "platform": platform_key,
                    "platformName": source_config["name"],
                    "platformColor": source_config["color"],
                    "category": category,
                    "link": link,
                    "duoshanScore": score,
                    "idea": generate_creative_idea(title, platform_key, category),
                    "brief": generate_duoshan_brief(title, platform_key, category, score),
                })

            if items:
                return items

        except Exception as e:
            if attempt < MAX_RETRIES:
                print(f"  [重试 {attempt+1}/{MAX_RETRIES}] {api_cfg['name']}: {e}")
                time.sleep(2)
            else:
                print(f"  [ERROR] {api_cfg['name']}: {e}")

    return []


def get_fallback_data() -> dict:
    """所有 API 均失败时的降级数据"""
    tz = timezone(timedelta(hours=8))
    now = datetime.now(tz)

    fallback_trends = [
        {"title": "⚠️ 数据管道暂未连接，API 源均不可用", "hot": 0, "platform": "douyin", "category": "其他热点"},
        {"title": "请检查 GitHub Actions 执行日志排查故障", "hot": 0, "platform": "weibo", "category": "其他热点"},
        {"title": "或手动触发 Workflow Dispatch 重试", "hot": 0, "platform": "bilibili", "category": "其他热点"},
        {"title": "数据源: tenapi.cn / vvhan API", "hot": 0, "platform": "zhihu", "category": "其他热点"},
    ]

    trends = []
    for item in fallback_trends:
        platform_key = item["platform"]
        source = API_SOURCES.get(platform_key, {})
        category = item.get("category", "其他热点")
        score = calc_duoshan_score(item["title"], category)

        trends.append({
            "id": hashlib.md5(f"fb_{platform_key}_{item['title']}".encode()).hexdigest()[:12],
            "rank": len([t for t in trends if t.get("platform") == platform_key]) + 1,
            "title": item["title"],
            "hot": 0,
            "hotDisplay": "-",
            "platform": platform_key,
            "platformName": source.get("name", platform_key),
            "platformColor": source.get("color", "#666"),
            "category": category,
            "link": "",
            "duoshanScore": score,
            "idea": "数据源不可用，请检查 Actions 日志",
            "brief": generate_duoshan_brief(item["title"], platform_key, category, score),
            "isFallback": True,
        })

    return {
        "date": now.strftime("%Y-%m-%d"),
        "time": now.strftime("%H:%M:%S"),
        "timestamp": int(now.timestamp()),
        "platforms": {},
        "total": len(trends),
        "trends": trends,
        "isFallback": True,
    }


def fetch_all_trends() -> dict:
    """抓取所有平台的热搜数据"""
    tz = timezone(timedelta(hours=8))
    now = datetime.now(tz)

    print(f"\n{'='*60}")
    print(f"  热梗工作台 - 数据抓取 (云端版)")
    print(f"  时间: {now.strftime('%Y-%m-%d %H:%M:%S')} (北京时间)")
    print(f"{'='*60}\n")

    all_trends = []
    platform_counts = {}

    for platform_key, source_config in API_SOURCES.items():
        print(f"[{source_config['name']}] 正在抓取...")
        items = fetch_single_source(platform_key, source_config)
        if items:
            all_trends.extend(items)
            platform_counts[platform_key] = len(items)

    if not all_trends:
        print("\n[WARN] 所有 API 均未返回数据，使用降级数据...")
        return get_fallback_data()

    # 按热度排序
    all_trends.sort(key=lambda x: x.get("hot", 0), reverse=True)

    # 重新分配全局排名
    for idx, trend in enumerate(all_trends):
        trend["globalRank"] = idx + 1

    result = {
        "date": now.strftime("%Y-%m-%d"),
        "time": now.strftime("%H:%M:%S"),
        "timestamp": int(now.timestamp()),
        "platforms": platform_counts,
        "total": len(all_trends),
        "trends": all_trends,
        "isFallback": False,
    }

    print(f"\n{'='*60}")
    print(f"  抓取完成! 共 {len(all_trends)} 条热搜")
    for p, c in platform_counts.items():
        print(f"    {API_SOURCES[p]['name']}: {c} 条")
    print(f"{'='*60}\n")

    return result


def write_data_js(data: dict):
    """将数据写入 data.js 文件"""
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    js_lines = [
        "// 自动生成 - 请勿手动编辑",
        f"// 更新时间: {data['date']} {data['time']} (北京时间)",
        f"// 数据来源: tenapi.cn + vvhan API",
        f"// 云端自动化: GitHub Actions (每天 9:00 自动更新)",
        f"const TREND_DATA = {json.dumps(data, ensure_ascii=False, indent=2)};",
        "",
    ]
    js_content = "\n".join(js_lines)

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        f.write(js_content)

    print(f"[OK] 数据已写入: {OUTPUT_FILE}")


def main():
    data = fetch_all_trends()
    write_data_js(data)

    # 输出状态信息供 GitHub Actions 使用
    if data.get("isFallback"):
        print("\n::warning:: 使用降级数据 — 所有 API 源均失败")
        # 不 exit(1)，因为降级数据至少让页面保持可用
        # 但设置一个特殊输出让 workflow 可以判断
    else:
        print(f"\n::notice:: 成功抓取 {data['total']} 条真实热搜数据")

    return data


if __name__ == "__main__":
    main()
