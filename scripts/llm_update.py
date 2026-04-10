#!/usr/bin/env python3
"""
全球水道数据 LLM 智能更新脚本 v3.0
使用 Google Gemini API 分析最新水道状态，更新 full_data.json。

依赖: requests
配置: 设置环境变量 GEMINI_API_KEY
"""

import json
import os
import requests
from datetime import datetime, timedelta, timezone

# ==================== 配置 ====================
GEMINI_API_KEY = os.environ.get('GEMINI_API_KEY', '')
SCRIPT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PUBLIC_DATA_DIR = os.path.join(SCRIPT_DIR, 'public', 'data')
DATA_FILE = os.path.join(PUBLIC_DATA_DIR, 'full_data.json')  # 修正：正确文件名

def now_beijing():
    return datetime.now(timezone(timedelta(hours=8)))


# ==================== 天气获取（Open-Meteo 免费无需 API Key） ====================
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
    0: ("晴朗", "☀️"), 1: ("晴间多云", "🌤️"), 2: ("多云", "⛅"), 3: ("阴天", "☁️"),
    45: ("雾", "🌫️"), 48: ("雾", "🌫️"),
    51: ("小雨", "🌧️"), 53: ("中雨", "🌧️"), 55: ("大雨", "🌧️"),
    61: ("小雨", "🌧️"), 63: ("中雨", "🌧️"), 65: ("大雨", "🌧️"),
    71: ("小雪", "🌨️"), 73: ("中雪", "🌨️"), 75: ("大雪", "❄️"),
    80: ("阵雨", "🌦️"), 81: ("阵雨", "🌦️"), 82: ("强阵雨", "🌦️"),
    95: ("雷暴", "⛈️"), 96: ("雷暴", "⛈️"), 99: ("雷暴", "⛈️"),
}

def fetch_weather(wid):
    """获取指定水道的真实天气数据"""
    coords = WATERWAY_COORDS.get(wid)
    if not coords:
        return None
    lat, lon = coords["lat"], coords["lon"]
    url = (
        f"https://api.open-meteo.com/v1/forecast"
        f"?latitude={lat}&longitude={lon}"
        f"&current=temperature_2m,relative_humidity_2m,apparent_temperature,"
        f"weather_code,wind_speed_10m,wind_direction_10m"
        f"&timezone=auto"
    )
    try:
        r = requests.get(url, timeout=10)
        r.raise_for_status()
        current = r.json().get("current", {})
        wcode = current.get("weather_code", 0)
        cond, icon = WEATHER_CODES.get(wcode, ("未知", "❓"))
        wind_spd = current.get("wind_speed_10m", 0)
        wind_dir = current.get("wind_direction_10m", 0)
        directions = ["北", "东北", "东", "东南", "南", "西南", "西", "西北"]
        dir_idx = int((wind_dir + 22.5) // 45) % 8
        return {
            "temperature": f"{int(current.get('temperature_2m', 0))}°C",
            "feels_like": f"{int(current.get('apparent_temperature', 0))}°C",
            "wind": f"{int(wind_spd)} km/h {directions[dir_idx]}",
            "wave": "N/A",
            "visibility": "10 km",
            "condition": cond,
            "condition_icon": icon,
            "humidity": f"{int(current.get('relative_humidity_2m', 0))}%",
            "updated": datetime.utcnow().isoformat() + 'Z',
            "data_source": "Open-Meteo API"
        }
    except Exception as e:
        print(f"  ⚠️  {wid} 天气获取失败: {e}")
        return None


# ==================== Gemini LLM 批量分析 ====================
BATCH_PROMPT_TEMPLATE = """你是航运情报分析师。请根据当前（{date}）最新情况，分析以下10个关键水道的航运状态。

请以严格的JSON格式返回，结构如下：
{{
  "ormuz":     {{"traffic": "交通量描述", "risk_level": "高/中/低", "risk_score": 数字0-100, "status": "状态", "notes": "备注", "advisory": "建议"}},
  "malacca":   {{"traffic": "交通量描述", "risk_level": "高/中/低", "risk_score": 数字0-100, "status": "状态", "notes": "备注", "advisory": "建议"}},
  "suez":      {{"traffic": "交通量描述", "risk_level": "高/中/低", "risk_score": 数字0-100, "status": "状态", "notes": "备注", "advisory": "建议"}},
  "panama":    {{"traffic": "交通量描述", "risk_level": "高/中/低", "risk_score": 数字0-100, "status": "状态", "notes": "备注", "advisory": "建议"}},
  "mandeb":    {{"traffic": "交通量描述", "risk_level": "高/中/低", "risk_score": 数字0-100, "status": "状态", "notes": "备注", "advisory": "建议"}},
  "cape":      {{"traffic": "交通量描述", "risk_level": "高/中/低", "risk_score": 数字0-100, "status": "状态", "notes": "备注", "advisory": "建议"}},
  "turkish":   {{"traffic": "交通量描述", "risk_level": "高/中/低", "risk_score": 数字0-100, "status": "状态", "notes": "备注", "advisory": "建议"}},
  "denmark":   {{"traffic": "交通量描述", "risk_level": "高/中/低", "risk_score": 数字0-100, "status": "状态", "notes": "备注", "advisory": "建议"}},
  "gibraltar": {{"traffic": "交通量描述", "risk_level": "高/中/低", "risk_score": 数字0-100, "status": "状态", "notes": "备注", "advisory": "建议"}},
  "lombok":    {{"traffic": "交通量描述", "risk_level": "高/中/低", "risk_score": 数字0-100, "status": "状态", "notes": "备注", "advisory": "建议"}}
}}

重要要求：
1. 所有回答用中文
2. risk_score 为 0-100 的整数
3. 基于 {date} 最新的地缘政治/航运实际情况给出评估
4. notes 字段包含当前最重要的一句简洁提示（30字以内）
5. 只返回 JSON，不要任何其他文字"""


def analyze_all_with_gemini():
    """一次性调用 Gemini 分析所有水道，节省 API 配额"""
    today = now_beijing().strftime("%Y年%m月%d日")
    prompt = BATCH_PROMPT_TEMPLATE.format(date=today)

    url = (
        "https://generativelanguage.googleapis.com/v1beta/"
        f"models/gemini-2.0-flash:generateContent?key={GEMINI_API_KEY}"
    )
    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {
            "responseMimeType": "application/json",
            "maxOutputTokens": 2048,
            "temperature": 0.3,
        }
    }

    try:
        r = requests.post(url, json=payload, timeout=60)
        r.raise_for_status()
        text = r.json()["candidates"][0]["content"]["parts"][0]["text"]
        result = json.loads(text)
        print(f"  ✅ Gemini 分析完成，覆盖 {len(result)} 个水道")
        return result
    except Exception as e:
        print(f"  ⚠️  Gemini 批量分析失败: {e}")
        return {}


# ==================== 主逻辑 ====================
def main():
    ts_beijing = now_beijing()
    timestamp = ts_beijing.strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{timestamp}] 开始 LLM 智能更新 v3.0...")

    if not GEMINI_API_KEY:
        print("⚠️  未设置 GEMINI_API_KEY，跳过 LLM 更新")
        return

    # 加载现有数据
    if not os.path.exists(DATA_FILE):
        print(f"⚠️  数据文件不存在: {DATA_FILE}")
        return

    with open(DATA_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)

    # 1. 更新天气数据（每次都刷新）
    print("📡 更新天气数据...")
    weather = data.get("weather", {})
    for wid in WATERWAY_COORDS:
        w = fetch_weather(wid)
        if w:
            weather[wid] = w
            print(f"  ✅ {WATERWAY_COORDS[wid]['name']}: {w['condition']} {w['temperature']}")
    data["weather"] = weather

    # 2. 调用 Gemini 分析所有水道（仅1次请求，节省配额）
    print("🤖 调用 Gemini 分析水道状态...")
    llm_results = analyze_all_with_gemini()

    security = data.get("security", {})
    traffic = data.get("traffic", {})
    geopolitics = data.get("geopolitics", {})
    now_iso = ts_beijing.isoformat()
    today_str = ts_beijing.strftime("%Y-%m-%d")

    if llm_results:
        # ── Gemini 成功：用 AI 分析结果更新 ──
        for wid, result in llm_results.items():
            risk_level = result.get("risk_level", "中")
            risk_score = result.get("risk_score", 50)
            notes = result.get("notes", "")
            advisory = result.get("advisory", "正常通行")
            status = result.get("status", "正常")
            traffic_desc = result.get("traffic", "正常")

            # 更新 security
            if wid in security:
                security[wid]["risk_level"] = risk_level
                security[wid]["risk_score"] = int(risk_score)
                security[wid]["updated"] = now_iso
                security[wid]["last_incident"] = today_str
                if risk_level == "高":
                    security[wid]["status"] = "高度关注"
                    security[wid]["status_icon"] = "⚠️"
                elif risk_level == "中":
                    security[wid]["status"] = "适度关注"
                    security[wid]["status_icon"] = "⚠️"
                else:
                    security[wid]["status"] = "正常通航"
                    security[wid]["status_icon"] = "✅"
            else:
                security[wid] = {
                    "risk_level": risk_level,
                    "risk_score": int(risk_score),
                    "alerts": [],
                    "status": status,
                    "status_icon": "⚠️" if risk_level in ("高", "中") else "✅",
                    "last_incident": today_str,
                    "updated": now_iso
                }

            # 更新 traffic
            if wid in traffic:
                traffic[wid]["queue_status"] = status
                traffic[wid]["notes"] = notes
                traffic[wid]["data_source"] = "Gemini AI 分析"
                traffic[wid]["updated"] = datetime.utcnow().isoformat() + 'Z'
                if risk_level == "高":
                    traffic[wid]["queue_icon"] = "🔴"
                elif risk_level == "中":
                    traffic[wid]["queue_icon"] = "🟡"
                else:
                    traffic[wid]["queue_icon"] = "🟢"
            else:
                traffic[wid] = {
                    "waiting_ships": 0,
                    "daily_transit": traffic_desc,
                    "avg_wait_time": "N/A",
                    "queue_status": status,
                    "queue_icon": "🟡" if risk_level in ("高", "中") else "🟢",
                    "congestion_level": risk_level,
                    "notes": notes,
                    "updated": datetime.utcnow().isoformat() + 'Z',
                    "data_source": "Gemini AI 分析"
                }

            # 更新 geopolitics
            geopolitics[wid] = {
                "status": status,
                "detail": advisory,
                "last_review": today_str,
                "advisory_level": risk_level
            }

            print(f"  📊 {WATERWAY_COORDS.get(wid, {}).get('name', wid)}: {risk_level}风险({risk_score}) - {notes}")

    else:
        # ── Gemini 失败：fallback 到静态规则更新（确保数据不过时）──
        print("  ⚠️  Gemini 不可用，使用静态规则更新 security/traffic/geopolitics...")
        STATIC_RISK = {
            "ormuz":     ("高",  72, "约20%全球石油过境，地区紧张局势持续监控"),
            "mandeb":    ("高",  78, "胡塞武装活动区域，建议申请军事护航"),
            "malacca":   ("中",  42, "全球最繁忙海峡，ReCAAP偶发登船事件"),
            "suez":      ("中",  50, "红海局势持续影响，通航量约40-60%"),
            "turkish":   ("低",  30, "蒙特勒公约规定，商船须提前报告"),
            "panama":    ("低",  18, "降雨恢复，通航量已回升正常水平"),
            "cape":      ("低",  22, "红海替代绕行路线，通过量高于正常"),
            "denmark":   ("低",  12, "冬季偶有浮冰，夏季通行条件良好"),
            "gibraltar": ("低",  18, "地中海-大西洋要道，通行顺畅"),
            "lombok":    ("低",  22, "超大型船舶偏好路线，通行正常"),
        }
        STATIC_TRAFFIC = {
            "ormuz":     ("受监控通行",   "约18-22艘大型油轮",  "2-6"),
            "mandeb":    ("军事护航通行", "约18艘",            "不确定"),
            "malacca":   ("正常",        "约190艘",           "1-2"),
            "suez":      ("受限通航",     "约35-50艘",         "2-4"),
            "turkish":   ("正常",        "约130艘",           "2-4"),
            "panama":    ("正常",        "约36艘",            "1-2"),
            "cape":      ("繁忙",        "约100艘",           "1"),
            "denmark":   ("正常",        "约15艘",            "1"),
            "gibraltar": ("繁忙",        "约290艘",           "1-2"),
            "lombok":    ("正常",        "约22艘",            "1"),
        }
        STATIC_GEO = {
            "ormuz":     ("高度关注", "约20%全球石油过境，建议商船登记UKMTO"),
            "mandeb":    ("高度关注", "建议联系护航协调机构（Aspides/Prosperity Guardian）"),
            "malacca":   ("适度关注", "保持常规警惕，24小时船桥瞭望"),
            "suez":      ("适度关注", "红海局势持续影响，请确认最新通行建议"),
            "turkish":   ("适度关注", "蒙特勒公约规定，战舰通行限制"),
            "panama":    ("稳定",     "正常通行"),
            "cape":      ("稳定",     "正常通行，注意大浪天气"),
            "denmark":   ("稳定",     "注意浮冰季节"),
            "gibraltar": ("稳定",     "正常通行"),
            "lombok":    ("稳定",     "正常通行"),
        }
        for wid in WATERWAY_COORDS:
            risk_level, risk_score, notes = STATIC_RISK.get(wid, ("低", 20, "正常通航"))
            q_status, daily, wait = STATIC_TRAFFIC.get(wid, ("正常", "约30艘", "2"))
            geo_status, geo_detail = STATIC_GEO.get(wid, ("稳定", "正常通行"))

            # security
            if wid not in security:
                security[wid] = {}
            security[wid].update({
                "risk_level": risk_level,
                "risk_score": risk_score,
                "status": "高度关注" if risk_level == "高" else ("适度关注" if risk_level == "中" else "正常通航"),
                "status_icon": "⚠️" if risk_level in ("高", "中") else "✅",
                "last_incident": today_str,
                "updated": now_iso,
            })
            if "alerts" not in security[wid]:
                security[wid]["alerts"] = []

            # traffic
            if wid not in traffic:
                traffic[wid] = {}
            traffic[wid].update({
                "daily_transit": daily,
                "avg_wait_time": wait + "小时",
                "queue_status": q_status,
                "queue_icon": "🔴" if risk_level == "高" else ("🟡" if risk_level == "中" else "🟢"),
                "congestion_level": risk_level,
                "notes": notes,
                "updated": datetime.utcnow().isoformat() + 'Z',
                "data_source": "静态规则 (Gemini 不可用时 fallback)",
            })
            if "waiting_ships" not in traffic[wid]:
                traffic[wid]["waiting_ships"] = 0

            # geopolitics
            geopolitics[wid] = {
                "status": geo_status,
                "detail": geo_detail,
                "last_review": today_str,
                "advisory_level": risk_level
            }
            print(f"  📋 {WATERWAY_COORDS.get(wid, {}).get('name', wid)}: {risk_level}风险({risk_score})")

    data["security"] = security
    data["traffic"] = traffic
    data["geopolitics"] = geopolitics

    # 3. 更新时间戳
    data["last_updated"] = ts_beijing.isoformat()
    data["next_update"] = (ts_beijing + timedelta(hours=1)).isoformat()

    # 4. 保存
    os.makedirs(PUBLIC_DATA_DIR, exist_ok=True)
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    print(f"\n✅ 更新完成！时间: {timestamp}")
    print(f"   文件: {DATA_FILE}")


if __name__ == "__main__":
    main()
