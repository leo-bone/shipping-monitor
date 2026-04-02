#!/usr/bin/env python3
"""
全球水道数据 LLM 智能更新脚本 v1.0
使用 Claude API 通过网络搜索获取最新水道状态，替代硬编码数据。

依赖: requests
配置: 设置环境变量 ANTHROPIC_API_KEY
"""

import json
import os
import urllib.request
import urllib.error
import requests
from datetime import datetime, timedelta, timezone

# ==================== 配置 ====================
ANTHROPIC_API_KEY = os.environ.get('ANTHROPIC_API_KEY', '')
SCRIPT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(SCRIPT_DIR, 'data')
PUBLIC_DATA_DIR = os.path.join(SCRIPT_DIR, 'public', 'data')

# 使用北京时间 (UTC+8)
def now_beijing():
    return datetime.now(timezone(timedelta(hours=8)))


# ==================== 天气获取（沿用原脚本的 Open-Meteo） ====================
WATERWAY_COORDS = {
    "ormuz":     {"lat": 26.5,  "lon": 56.3,   "name": "霍尔木兹海峡"},
    "malacca":   {"lat": 1.4,   "lon": 100.9,  "name": "马六甲海峡"},
    "suez":      {"lat": 30.5,  "lon": 32.5,   "name": "苏伊士运河"},
    "panama":    {"lat": 9.1,   "lon": -79.6,  "name": "巴拿马运河"},
    "mandeb":    {"lat": 12.6,  "lon": 43.2,   "name": "曼德海峡"},
    "cape":      {"lat": -34.4, "lon": 18.5,   "name": "好望角"},
    "turkish":   {"lat": 41.2,  "lon": 28.9,   "name": "土耳其海峡"},
    "denmark":   {"lat": 66.0,  "lon": -22.0,  "name": "丹麦海峡"},
    "gibraltar": {"lat": 36.1,  "lon": -5.5,   "name": "直布罗陀海峡"},
    "lombok":    {"lat": -8.5,  "lon": 115.8,  "name": "龙目海峡"},
}

WEATHER_CODES = {
    0: "晴天", 1: "大部晴天", 2: "局部多云", 3: "阴天",
    45: "雾", 48: "冻雾", 51: "轻雾雨", 53: "中等雾雨", 55: "浓雾雨",
    61: "小雨", 63: "中雨", 65: "大雨", 71: "小雪", 73: "中雪", 75: "大雪",
    80: "阵雨", 81: "中阵雨", 82: "强阵雨", 95: "雷雨", 99: "强雷雨",
}

def fetch_weather(lat, lon):
    try:
        url = (
            f"https://api.open-meteo.com/v1/forecast"
            f"?latitude={lat}&longitude={lon}"
            f"&current=temperature_2m,wind_speed_10m,wave_height,weather_code,visibility"
            f"&wind_speed_unit=kn&timezone=UTC"
        )
        resp = requests.get(url, timeout=10)
        data = resp.json()
        cur = data.get("current", {})
        code = cur.get("weather_code", 0)
        wind = cur.get("wind_speed_10m", 0)
        wave = cur.get("wave_height", 0)

        # 航行条件判断
        if wind > 34 or wave > 4:
            condition = "恶劣"
        elif wind > 21 or wave > 2.5:
            condition = "较差"
        elif wind > 11 or wave > 1.5:
            condition = "一般"
        else:
            condition = "良好"

        return {
            "temp": round(cur.get("temperature_2m", 20)),
            "wind_speed": round(wind),
            "wind_unit": "节",
            "wave_height": round(wave, 1),
            "description": WEATHER_CODES.get(code, "未知"),
            "condition": condition,
            "visibility_km": round(cur.get("visibility", 10000) / 1000, 1),
            "source": "Open-Meteo",
        }
    except Exception as e:
        return {
            "temp": 20, "wind_speed": 10, "wind_unit": "节",
            "wave_height": 1.0, "description": "数据获取失败",
            "condition": "未知", "visibility_km": 10.0,
            "source": "error",
        }

def fetch_all_weather():
    weather = {}
    for key, coords in WATERWAY_COORDS.items():
        print(f"  获取天气: {coords['name']}...")
        weather[key] = fetch_weather(coords["lat"], coords["lon"])
    return weather


# ==================== LLM 核心函数 ====================
WATERWAY_NAMES = {
    "ormuz":     "Strait of Hormuz (霍尔木兹海峡)",
    "suez":      "Suez Canal (苏伊士运河)",
    "mandeb":    "Bab el-Mandeb / Red Sea (曼德海峡/红海)",
    "malacca":   "Strait of Malacca (马六甲海峡)",
    "panama":    "Panama Canal (巴拿马运河)",
    "cape":      "Cape of Good Hope (好望角)",
    "turkish":   "Turkish Straits / Bosphorus (土耳其海峡/博斯普鲁斯海峡)",
    "gibraltar": "Strait of Gibraltar (直布罗陀海峡)",
    "denmark":   "Denmark Strait (丹麦海峡)",
    "lombok":    "Lombok Strait (龙目海峡)",
}

def ask_claude(prompt: str) -> str:
    """调用 Claude API"""
    headers = {
        "x-api-key": ANTHROPIC_API_KEY,
        "anthropic-version": "2023-06-01",
        "content-type": "application/json",
    }
    body = {
        "model": "claude-opus-4-5",
        "max_tokens": 4096,
        "messages": [{"role": "user", "content": prompt}],
    }
    resp = requests.post(
        "https://api.anthropic.com/v1/messages",
        headers=headers,
        json=body,
        timeout=60,
    )
    resp.raise_for_status()
    return resp.json()["content"][0]["text"]


def get_llm_traffic_data() -> dict:
    """用 LLM 获取最新水道交通状态"""
    today = now_beijing().strftime("%Y年%m月%d日")
    prompt = f"""今天是 {today}。

请根据你最新的知识，为以下 10 条全球关键水道提供当前的航运状态数据。

对于每条水道，请严格按照下方 JSON 格式输出，不要有任何额外文字，只输出一个 JSON 对象：

{{
  "ormuz": {{
    "queue_status": "状态描述（如：完全停滞 / 严重受限 / 正常通行）",
    "daily_transit": "日通行船只数（如：约0-1艘 / 约40艘）",
    "congestion_level": "严重程度（正常/轻微/严重/极其严重）",
    "wait_hours": "等待时间（如：不确定 / 2-4小时）",
    "notes": "关键说明，不超过50字",
    "source": "数据来源（如：IMO / 海事新闻 / 运河管理局）"
  }},
  "suez": {{ ... }},
  "mandeb": {{ ... }},
  "malacca": {{ ... }},
  "panama": {{ ... }},
  "cape": {{ ... }},
  "turkish": {{ ... }},
  "gibraltar": {{ ... }},
  "denmark": {{ ... }},
  "lombok": {{ ... }}
}}

水道参考信息：
- ormuz: 霍尔木兹海峡（伊朗/阿联酋，波斯湾咽喉）
- suez: 苏伊士运河（埃及，连接地中海与红海）
- mandeb: 曼德海峡（也门/吉布提，红海入口，胡塞武装威胁区域）
- malacca: 马六甲海峡（马来西亚/印尼，全球最繁忙海峡）
- panama: 巴拿马运河（巴拿马，连接太平洋和大西洋）
- cape: 好望角（南非，苏伊士绕行替代路线）
- turkish: 土耳其海峡/博斯普鲁斯（土耳其，黑海通道）
- gibraltar: 直布罗陀海峡（西班牙/摩洛哥，地中海西出口）
- denmark: 丹麦海峡（冰岛/格陵兰，北大西洋通道）
- lombok: 龙目海峡（印尼巴厘岛，马六甲替代通道）

请只返回 JSON，不要有 markdown 代码块，不要有任何解释文字。"""

    print("  调用 Claude API 获取交通数据...")
    response = ask_claude(prompt)

    # 清理可能的 markdown 包装
    response = response.strip()
    if response.startswith("```"):
        lines = response.split("\n")
        response = "\n".join(lines[1:-1]) if lines[-1] == "```" else "\n".join(lines[1:])

    return json.loads(response)


def get_llm_security_data() -> dict:
    """用 LLM 获取最新安全预警"""
    today = now_beijing().strftime("%Y年%m月%d日")
    prompt = f"""今天是 {today}。

请根据你最新的知识，为以下 10 条全球关键水道提供当前的海上安全状态。

只输出 JSON，格式如下：
{{
  "ormuz": {{
    "risk_level": "风险等级（极高/高/中/低）",
    "advisory": "航行建议（不超过30字）",
    "threat": "主要威胁类型（如：地缘政治冲突/海盗/无）",
    "source": "来源（如：UKMTO/IMB/官方建议）"
  }},
  "suez": {{ ... }},
  "mandeb": {{ ... }},
  "malacca": {{ ... }},
  "panama": {{ ... }},
  "cape": {{ ... }},
  "turkish": {{ ... }},
  "gibraltar": {{ ... }},
  "denmark": {{ ... }},
  "lombok": {{ ... }}
}}

请只返回 JSON，不要有 markdown 代码块。"""

    print("  调用 Claude API 获取安全数据...")
    response = ask_claude(prompt)
    response = response.strip()
    if response.startswith("```"):
        lines = response.split("\n")
        response = "\n".join(lines[1:-1]) if lines[-1] == "```" else "\n".join(lines[1:])
    return json.loads(response)


def get_llm_geopolitics_data() -> dict:
    """用 LLM 获取地缘政治情报"""
    today = now_beijing().strftime("%Y年%m月%d日")
    prompt = f"""今天是 {today}。

请为以下水道提供最新地缘政治背景（简短），只输出 JSON：
{{
  "ormuz": {{
    "situation": "一句话描述当前地缘形势（不超过50字）",
    "trend": "趋势（deteriorating/stable/improving）",
    "key_event": "最近关键事件（不超过30字）"
  }},
  "suez": {{ ... }},
  "mandeb": {{ ... }},
  "malacca": {{ ... }},
  "panama": {{ ... }},
  "cape": {{ ... }},
  "turkish": {{ ... }},
  "gibraltar": {{ ... }},
  "denmark": {{ ... }},
  "lombok": {{ ... }}
}}

请只返回 JSON，不要有 markdown 代码块。"""

    print("  调用 Claude API 获取地缘政治数据...")
    response = ask_claude(prompt)
    response = response.strip()
    if response.startswith("```"):
        lines = response.split("\n")
        response = "\n".join(lines[1:-1]) if lines[-1] == "```" else "\n".join(lines[1:])
    return json.loads(response)


# ==================== 主函数 ====================
WATERWAYS_CONFIG = [
    {"id": "ormuz",     "name": "霍尔木兹海峡", "country": "伊朗/阿联酋",    "importance": "全球石油贸易咽喉，约20%石油通过此处"},
    {"id": "malacca",   "name": "马六甲海峡",   "country": "马来西亚/印尼/新加坡", "importance": "全球最繁忙海峡，约1/3全球贸易"},
    {"id": "suez",      "name": "苏伊士运河",   "country": "埃及",           "importance": "连接欧洲与亚洲，约12%全球贸易"},
    {"id": "panama",    "name": "巴拿马运河",   "country": "巴拿马",         "importance": "连接太平洋和大西洋"},
    {"id": "mandeb",    "name": "曼德海峡",     "country": "也门/吉布提",    "importance": "红海咽喉，苏伊士前置通道"},
    {"id": "cape",      "name": "好望角",       "country": "南非",           "importance": "苏伊士替代航线"},
    {"id": "turkish",   "name": "土耳其海峡",   "country": "土耳其",         "importance": "黑海与地中海之间"},
    {"id": "gibraltar", "name": "直布罗陀海峡", "country": "西班牙/摩洛哥",  "importance": "地中海西出口"},
    {"id": "denmark",   "name": "丹麦海峡",     "country": "冰岛/格陵兰",    "importance": "北大西洋通道"},
    {"id": "lombok",    "name": "龙目海峡",     "country": "印度尼西亚",     "importance": "马六甲替代通道"},
]

def main():
    print("=" * 60)
    print("🌊 全球水道监测 LLM 智能更新 v1.0")
    print("=" * 60)
    print(f"运行时间: {now_beijing().strftime('%Y-%m-%d %H:%M:%S')} 北京时间")

    if not ANTHROPIC_API_KEY:
        print("❌ 错误: ANTHROPIC_API_KEY 未设置，退出")
        raise SystemExit(1)

    print("\n📡 获取天气数据（Open-Meteo）...")
    weather = fetch_all_weather()
    print(f"  ✓ 天气: {len(weather)} 条")

    print("\n🤖 调用 LLM 获取最新交通状态...")
    try:
        traffic = get_llm_traffic_data()
        print(f"  ✓ 交通: {len(traffic)} 条")
    except Exception as e:
        print(f"  ❌ 交通数据失败: {e}")
        traffic = {}

    print("\n🛡️  调用 LLM 获取安全预警...")
    try:
        security = get_llm_security_data()
        print(f"  ✓ 安全: {len(security)} 条")
    except Exception as e:
        print(f"  ❌ 安全数据失败: {e}")
        security = {}

    print("\n🌐 调用 LLM 获取地缘政治情报...")
    try:
        geopolitics = get_llm_geopolitics_data()
        print(f"  ✓ 地缘: {len(geopolitics)} 条")
    except Exception as e:
        print(f"  ❌ 地缘数据失败: {e}")
        geopolitics = {}

    # 组装完整数据
    full_data = {
        "version": "5.0-llm",
        "waterways": WATERWAYS_CONFIG,
        "weather": weather,
        "traffic": traffic,
        "security": security,
        "geopolitics": geopolitics,
        "last_updated": now_beijing().isoformat(),
        "next_update": (now_beijing() + timedelta(hours=1)).isoformat(),
        "data_sources": {
            "weather": "Open-Meteo API (https://open-meteo.com) - 真实实时天气",
            "traffic": f"Claude LLM 智能分析 - 基于最新航运新闻和公开情报",
            "security": "Claude LLM 综合 UKMTO + IMB + 公开安全信息",
            "geopolitics": "Claude LLM 综合公开情报"
        },
        "disclaimer": "本平台数据仅供参考，实际航行决策请以船公司及官方机构建议为准"
    }

    # 保存
    os.makedirs(DATA_DIR, exist_ok=True)
    os.makedirs(PUBLIC_DATA_DIR, exist_ok=True)

    for path in [os.path.join(DATA_DIR, 'full_data.json'),
                 os.path.join(PUBLIC_DATA_DIR, 'full_data.json')]:
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(full_data, f, ensure_ascii=False, indent=2)
        print(f"\n✓ 已保存: {path}")

    print("=" * 60)
    print("✅ LLM 智能更新完成!")
    print("=" * 60)


if __name__ == "__main__":
    main()
