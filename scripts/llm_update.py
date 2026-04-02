#!/usr/bin/env python3
"""
全球水道数据 LLM 智能更新脚本 v2.0
使用 Google Gemini API 获取最新水道状态，替代硬编码数据。

依赖: requests
配置: 设置环境变量 GEMINI_API_KEY
"""

import json
import os
import urllib.request
import urllib.error
import requests
from datetime import datetime, timedelta, timezone

# ==================== 配置 ====================
GEMINI_API_KEY = os.environ.get('GEMINI_API_KEY', '')
SCRIPT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(SCRIPT_DIR, 'data')
PUBLIC_DATA_DIR = os.path.join(SCRIPT_DIR, 'public', 'data')

# 使用北京时间 (UTC+8)
def now_beijing():
    return datetime.now(timezone(timedelta(hours=8)))


# ==================== 天气获取（Open-Meteo 免费无需 API Key） ====================
WATERWAY_COORDS = {
    "ormuz":     {"lat": 26.5,  "lon": 56.3,   "name": "霍尔木兹海峡"},
    "malacca":   {"lat": 2.0,   "lon": 100.5,  "name": "马六甲海峡"},
    "suez":      {"lat": 30.5,  "lon": 32.5,   "name": "苏伊士运河"},
    "panama":    {"lat": 9.0,   "lon": -79.5,  "name": "巴拿马运河"},
    "bab_mandab":{"lat": 12.5,  "lon": 43.5,   "name": "曼德海峡"},
    "bosporus":  {"lat": 41.0,  "lon": 29.0,   "name": "博斯普鲁斯海峡"},
    "gibraltar": {"lat": 36.0,  "lon": -5.5,   "name": "直布罗陀海峡"},
    "sunda":     {"lat": -6.0,  "lon": 105.5,  "name": "巽他海峡"},
    "lombok":    {"lat": -8.5,  "lon": 115.5,  "name": "龙目海峡"},
    "taiwan":    {"lat": 23.5,  "lon": 121.0,  "name": "台湾海峡"},
}

def fetch_weather(lat, lon):
    url = (
        f"https://api.open-meteo.com/v1/forecast"
        f"?latitude={lat}&longitude={lon}"
        f"&current=wind_speed_10m,wind_direction_10m,weather_code"
        f"&wind_speed_unit=kn&timezone=auto"
    )
    try:
        r = requests.get(url, timeout=10)
        data = r.json().get("current", {})
        wcode = data.get("weather_code", 0)
        return {
            "wind_speed": round(data.get("wind_speed_10m", 0) * 0.539957, 1),
            "wind_dir": data.get("wind_direction_10m", 0),
            "description": WEATHER_CODES.get(wcode, "未知"),
        }
    except Exception as e:
        return {"wind_speed": 0, "wind_dir": 0, "description": f"获取失败: {e}"}

WEATHER_CODES = {
    0: "晴朗", 1: "晴间多云", 2: "多云", 3: "阴天",
    45: "雾", 48: "霜雾", 51: "小毛毛雨", 53: "中毛毛雨",
    55: "大毛毛雨", 61: "小雨", 63: "中雨", 65: "大雨",
    80: "阵雨", 81: "中阵雨", 82: "强阵雨",
    95: "雷暴", 96: "雷暴伴小冰雹", 99: "雷暴伴大冰雹",
}


# ==================== Gemini LLM 分析 ====================
WATERWAY_PROMPTS = {
    "ormuz": "分析霍尔木兹海峡当前航运状况：1) 近期船只通行量 2) 地缘政治紧张程度（美伊/中东局势） 3) 保险费用/战争险 4) 整体风险评级。简洁输出JSON格式。",
    "malacca": "分析马六甲海峡当前航运状况：1) 近期船只通行量 2) 海盗/安全威胁情况 3) 通行效率 4) 整体风险评级。简洁输出JSON格式。",
    "suez": "分析苏伊士运河当前航运状况：1) 近期通行船只数量 2) 运河通航状况/维护情况 3) 胡塞武装/红海局势影响 4) 整体风险评级。简洁输出JSON格式。",
    "panama": "分析巴拿马运河当前航运状况：1) 水位/干旱情况对通行的影响 2) 等待船只数量 3) 通行费变化 4) 整体风险评级。简洁输出JSON格式。",
    "bab_mandab": "分析曼德海峡当前航运状况：1) 胡塞武装袭击情况 2) 船只通行量变化 3) 保险费用 4) 整体风险评级。简洁输出JSON格式。",
    "bosporus": "分析博斯普鲁斯海峡当前航运状况：1) 近期通行船只数量 2) 土俄局势影响 3) 等待时间 4) 整体风险评级。简洁输出JSON格式。",
    "gibraltar": "分析直布罗陀海峡当前航运状况：1) 近期通行量 2) 天气/海况 3) 地缘因素（俄乌/地中海局势） 4) 整体风险评级。简洁输出JSON格式。",
    "sunda": "分析巽他海峡当前航运状况：1) 近期通行量 2) 海盗/安全威胁 3) 相比马六甲的选择情况 4) 整体风险评级。简洁输出JSON格式。",
    "lombok": "分析龙目海峡当前航运状况：1) 近期通行量 2) 海况 3) 作为马六甲替代路线的使用情况 4) 整体风险评级。简洁输出JSON格式。",
    "taiwan": "分析台湾海峡当前航运状况：1) 近期两岸紧张局势 2) 商船通行情况 3) 军事活动影响 4) 整体风险评级。简洁输出JSON格式。",
}

def analyze_with_gemini(wave_id, current_data):
    """调用 Gemini API 获取水道智能分析"""
    prompt = WATERWAY_PROMPTS.get(wave_id, f"分析 {wave_id} 水道当前状况。")
    context = f"当前数据: 交通量{current_data.get('traffic', 'N/A')}, "
    context += f"风险评级{current_data.get('risk_level', 'N/A')}, "
    context += f"天气{current_data.get('weather', 'N/A')}, "
    context += f"备注{current_data.get('notes', 'N/A')}"
    full_prompt = f"{prompt}\n\n{context}\n\n请以JSON格式返回，字段：traffic(交通量描述), risk_level(1-5), reason(原因简述), notes(补充备注)，中文回答。"

    url = (
        f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent"
        f"?key={GEMINI_API_KEY}"
    )
    payload = {
        "contents": [{"parts": [{"text": full_prompt}]}],
        "generationConfig": {
            "responseMimeType": "application/json",
            "maxOutputTokens": 256,
            "temperature": 0.3,
        }
    }

    try:
        r = requests.post(url, json=payload, timeout=30)
        r.raise_for_status()
        data = r.json()
        text = data["candidates"][0]["content"]["parts"][0]["text"]
        return json.loads(text)
    except Exception as e:
        return {
            "traffic": current_data.get("traffic", "未知"),
            "risk_level": current_data.get("risk_level", 3),
            "reason": f"LLM分析获取失败: {e}",
            "notes": current_data.get("notes", "")
        }


# ==================== 主逻辑 ====================
def main():
    timestamp = now_beijing().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{timestamp}] 开始 LLM 智能更新...")

    if not GEMINI_API_KEY:
        print("⚠️  未设置 GEMINI_API_KEY，跳过 LLM 更新")
        return

    data_file = os.path.join(PUBLIC_DATA_DIR, "shipping_data.json")
    if not os.path.exists(data_file):
        print(f"⚠️  数据文件不存在: {data_file}")
        return

    with open(data_file, "r", encoding="utf-8") as f:
        data = json.load(f)

    updated_count = 0
    for waterway in data.get("waterways", []):
        wid = waterway.get("id")
        if wid not in WATERWAY_COORDS:
            continue

        coords = WATERWAY_COORDS[wid]
        weather = fetch_weather(coords["lat"], coords["lon"])
        waterway["weather"] = f"{weather['description']}, 风速{weather['wind_speed']}节"
        waterway["last_updated"] = timestamp

        # 优先使用 LLM 分析（覆盖风险和备注）
        llm_result = analyze_with_gemini(wid, waterway)
        if llm_result:
            waterway["risk_level"] = llm_result.get("risk_level", waterway["risk_level"])
            waterway["traffic"] = llm_result.get("traffic", waterway["traffic"])
            waterway["notes"] = llm_result.get("notes", waterway.get("notes", ""))
            print(f"  ✅ {coords['name']}: 风险{waterway['risk_level']} | {llm_result.get('reason', '')}")
        else:
            print(f"  ⚠️  {coords['name']}: LLM 失败，使用缓存")

        updated_count += 1

    with open(data_file, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    print(f"\n✅ 更新完成！共更新 {updated_count} 条水道数据")


if __name__ == "__main__":
    main()
