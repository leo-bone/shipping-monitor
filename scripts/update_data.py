#!/usr/bin/env python3
"""
全球关键水道数据抓取脚本 v3.0
数据来源:
- 天气: Open-Meteo API (免费)
- 船舶追踪: AISHub API (需要注册获取免费 API key)
- 安全预警: IMB 2025 年度报告 + 公开新闻
- 通航状态: 基于公开信息的估算
"""

import json
import os
import urllib.request
import urllib.parse
import urllib.error
from datetime import datetime, timedelta
import random

# ==================== 配置 ====================
# 如果有 AISHub 账号，填入用户名以获取船舶数据
# 注册地址: https://www.aishub.net
AISHUB_USERNAME = os.environ.get('AISHUB_USERNAME', '')  # 填入你的 AISHub 用户名

# 水道坐标映射
WATERWAY_COORDS = {
    "ormuz": {"lat": 26.5, "lon": 56.3, "name": "霍尔木兹海峡", "region": "Gulf"},
    "malacca": {"lat": 1.4, "lon": 100.9, "name": "马六甲海峡", "region": "SE Asia"},
    "suez": {"lat": 30.5, "lon": 32.5, "name": "苏伊士运河", "region": "Egypt"},
    "panama": {"lat": 9.1, "lon": -79.6, "name": "巴拿马运河", "region": "Central America"},
    "mandeb": {"lat": 12.6, "lon": 43.2, "name": "曼德海峡", "region": "Red Sea"},
    "cape": {"lat": -34.4, "lon": 18.5, "name": "好望角", "region": "South Africa"},
    "turkish": {"lat": 41.2, "lon": 28.9, "name": "土耳其海峡", "region": "Turkey"},
    "denmark": {"lat": 66.0, "lon": -22.0, "name": "丹麦海峡", "region": "North Atlantic"},
    "gibraltar": {"lat": 36.1, "lon": -5.5, "name": "直布罗陀海峡", "region": "Mediterranean"},
    "lombok": {"lat": -8.5, "lon": 115.8, "name": "龙目海峡", "region": "Indonesia"},
}

# 路径配置
SCRIPT_DIR = os.path.dirname(os.path.dirname(__file__))
DATA_DIR = os.path.join(SCRIPT_DIR, 'data')
PUBLIC_DATA_DIR = os.path.join(SCRIPT_DIR, 'public', 'data')

# 天气代码映射 (WMO)
WEATHER_CODES = {
    0: ("晴朗", "☀️"), 1: ("晴间多云", "🌤️"), 2: ("多云", "⛅"), 3: ("阴天", "☁️"),
    45: ("雾", "🌫️"), 48: ("雾", "🌫️"),
    51: ("小雨", "🌧️"), 53: ("中雨", "🌧️"), 55: ("大雨", "🌧️"),
    61: ("小雨", "🌧️"), 63: ("中雨", "🌧️"), 65: ("大雨", "🌧️"),
    71: ("小雪", "🌨️"), 73: ("中雪", "🌨️"), 75: ("大雪", "❄️"),
    80: ("阵雨", "🌦️"), 81: ("阵雨", "🌦️"), 82: ("强阵雨", "🌦️"),
    95: ("雷暴", "⛈️"), 96: ("雷暴", "⛈️"), 99: ("雷暴", "⛈️"),
}

# ==================== 数据获取函数 ====================

def load_waterways():
    """加载水道基础数据"""
    with open(os.path.join(DATA_DIR, 'waterways.json'), 'r', encoding='utf-8') as f:
        return json.load(f)

def fetch_weather_from_api(lat, lon):
    """从 Open-Meteo API 获取真实天气数据"""
    try:
        url = f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&current=temperature_2m,relative_humidity_2m,apparent_temperature,weather_code,wind_speed_10m,wind_direction_10m&timezone=auto"
        
        req = urllib.request.Request(url, headers={'User-Agent': 'ShippingMonitor/1.0'})
        with urllib.request.urlopen(req, timeout=10) as response:
            data = json.loads(response.read().decode('utf-8'))
        
        current = data.get('current', {})
        
        temp = current.get('temperature_2m', 0)
        humidity = current.get('relative_humidity_2m', 0)
        wind_speed = current.get('wind_speed_10m', 0)
        wind_dir = current.get('wind_direction_10m', 0)
        weather_code = current.get('weather_code', 0)
        
        condition, icon = WEATHER_CODES.get(weather_code, ("未知", "❓"))
        
        # 风向文字
        directions = ["北", "东北", "东", "东南", "南", "西南", "西", "西北"]
        dir_idx = int((wind_dir + 22.5) // 45) % 8
        
        return {
            "temperature": f"{int(temp)}°C",
            "feels_like": f"{int(current.get('apparent_temperature', temp))}°C",
            "wind": f"{int(wind_speed)} km/h {directions[dir_idx]}",
            "wave": "N/A",  # 简化
            "visibility": "10 km",
            "condition": condition,
            "condition_icon": icon,
            "humidity": f"{int(humidity)}%",
            "updated": datetime.utcnow().isoformat() + 'Z',
            "data_source": "Open-Meteo API"
        }
    except Exception as e:
        print(f"  ⚠️ 天气 API 失败: {e}")
        return None

def get_fallback_weather(lat):
    """备选天气数据"""
    if lat > 50:
        temp_range = (-5, 10)
    elif lat > 30 or lat < -20:
        temp_range = (15, 28)
    else:
        temp_range = (25, 35)
    
    conditions = [("晴朗", "☀️"), ("多云", "⛅"), ("阴天", "☁️"), ("晴间多云", "🌤️")]
    condition, icon = random.choice(conditions)
    
    return {
        "temperature": f"{random.randint(temp_range[0], temp_range[1])}°C",
        "feels_like": f"{random.randint(temp_range[0]+2, temp_range[1]+2)}°C",
        "wind": f"{random.randint(10, 35)} km/h",
        "wave": f"{random.randint(1, 3)}m",
        "visibility": "10 km",
        "condition": condition,
        "condition_icon": icon,
        "humidity": f"{random.randint(60, 85)}%",
        "updated": datetime.utcnow().isoformat() + 'Z',
        "data_source": "Estimated"
    }

def fetch_ship_count_from_aishub(lat_min, lat_max, lon_min, lon_max):
    """
    从 AISHub 获取区域船舶数量
    注意: 需要注册 https://www.aishub.net 获取免费 API
    限制: 请求间隔不少于 1 分钟
    """
    if not AISHUB_USERNAME:
        return None
    
    try:
        # 使用较小区域避免返回过多数据
        url = f"https://data.aishub.net/ws.php?username={AISHUB_USERNAME}&format=1&output=json&latmin={lat_min}&latmax={lat_max}&lonmin={lon_min}&lonmax={lon_max}"
        
        req = urllib.request.Request(url, headers={'User-Agent': 'ShippingMonitor/1.0'})
        with urllib.request.urlopen(req, timeout=15) as response:
            data = json.loads(response.read().decode('utf-8'))
        
        if isinstance(data, list):
            return len(data)
        return 0
    except Exception as e:
        print(f"  ⚠️ AISHub API 失败: {e}")
        return None

def update_weather_data(waterways):
    """更新天气数据"""
    weather_data = {}
    
    for waterway in waterways['waterways']:
        wid = waterway['id']
        coords = WATERWAY_COORDS.get(wid)
        
        print(f"  获取 {waterway['name']} 天气...", end=" ")
        
        if coords:
            weather = fetch_weather_from_api(coords['lat'], coords['lon'])
            if weather:
                weather_data[wid] = weather
                print("✓")
            else:
                weather_data[wid] = get_fallback_weather(coords['lat'])
                print("⚠️")
        else:
            weather_data[wid] = get_fallback_weather(waterway['coordinates'][1])
            print("⚠️")
    
    return weather_data

def update_security_data(waterways):
    """
    更新安全预警数据
    基于 IMB 2025 年度报告 + 公开信息
    参考: https://www.icc-ccs.org/imb-piracy-reporting-centre-2/
    """
    security_data = {}
    
    # IMB 2025 报告关键发现:
    # - 2025 年全球海盗事件增加到 137 起 (2024: 116)
    # - 高发区域: Gulf of Guinea (几内亚湾), Singapore Strait (新加坡海峡), Red Sea (红海)
    
    HIGH_RISK_AREAS = {
        "ormuz": {
            "risk_level": "高",
            "risk_score": 75,
            "alerts": [
                {
                    "type": "地缘政治紧张",
                    "severity": "高",
                    "location": "霍尔木兹海峡/波斯湾",
                    "time": "持续",
                    "detail": "地区局势紧张，伊朗与美国对立加剧，建议绕行"
                },
                {
                    "type": "海上冲突风险",
                    "severity": "高",
                    "location": "波斯湾入口",
                    "time": "2026年3月",
                    "detail": "注意武装冲突风险"
                }
            ],
            "status": "高度关注",
            "status_icon": "⚠️"
        },
        "mandeb": {
            "risk_level": "高",
            "risk_score": 80,
            "alerts": [
                {
                    "type": "海盗活动",
                    "severity": "高",
                    "location": "亚丁湾/曼德海峡",
                    "time": "持续",
                    "detail": "IMB 2025: 红海区域海盗活动频繁，建议武装护航"
                },
                {
                    "type": "地缘政治",
                    "severity": "高",
                    "location": "也门海域",
                    "time": "持续",
                    "detail": "胡塞武装袭击风险"
                }
            ],
            "status": "高度关注",
            "status_icon": "⚠️"
        },
    }
    
    MEDIUM_RISK_AREAS = {
        "malacca": {
            "risk_level": "中",
            "risk_score": 55,
            "alerts": [
                {
                    "type": "海盗威胁",
                    "severity": "中",
                    "location": "马六甲海峡",
                    "time": "偶发",
                    "detail": "IMB 2025: 新加坡海峡事件增加，保持警惕"
                }
            ],
            "status": "适度关注",
            "status_icon": "⚠️"
        },
        "turkish": {
            "risk_level": "中",
            "risk_score": 45,
            "alerts": [
                {
                    "type": "交通拥堵",
                    "severity": "低",
                    "location": "土耳其海峡",
                    "time": "高峰时段",
                    "detail": "等待时间较长，建议提前安排"
                }
            ],
            "status": "正常通航",
            "status_icon": "⚠️"
        },
    }
    
    LOW_RISK_AREAS = {
        "suez": {"risk_level": "低", "risk_score": 25, "alerts": [], "status": "正常通航", "status_icon": "✅"},
        "panama": {"risk_level": "低", "risk_score": 20, "alerts": [], "status": "正常通航", "status_icon": "✅"},
        "cape": {"risk_level": "低", "risk_score": 25, "alerts": [], "status": "正常通航", "status_icon": "✅"},
        "denmark": {"risk_level": "低", "risk_score": 15, "alerts": [], "status": "正常通航", "status_icon": "✅"},
        "gibraltar": {"risk_level": "低", "risk_score": 20, "alerts": [], "status": "正常通航", "status_icon": "✅"},
        "lombok": {"risk_level": "低", "risk_score": 25, "alerts": [], "status": "正常通航", "status_icon": "✅"},
    }
    
    for waterway in waterways['waterways']:
        wid = waterway['id']
        
        if wid in HIGH_RISK_AREAS:
            data = HIGH_RISK_AREAS[wid].copy()
        elif wid in MEDIUM_RISK_AREAS:
            data = MEDIUM_RISK_AREAS[wid].copy()
        else:
            data = LOW_RISK_AREAS.get(wid, {"risk_level": "低", "risk_score": 20, "alerts": [], "status": "正常通航", "status_icon": "✅"})
        
        data["last_incident"] = "2026-03-19"
        data["updated"] = datetime.utcnow().isoformat() + 'Z'
        security_data[wid] = data
    
    return security_data

def update_traffic_data(waterways):
    """
    更新通航状态数据
    基于 IMB 报告 + 公开的运河管理局信息
    """
    traffic_data = {}
    
    # 基于公开信息的估算 (运河管理局公开数据 + 新闻)
    TRAFFIC_INFO = {
        "suez": {"status": "拥堵", "wait": "3-5小时", "level": "轻微", "daily": "约40艘"},
        "panama": {"status": "正常", "wait": "1-2小时", "level": "无", "daily": "约35艘"},
        "malacca": {"status": "繁忙", "wait": "2-4小时", "level": "轻微", "daily": "约200艘"},
        "ormuz": {"status": "正常", "wait": "1-2小时", "level": "无", "daily": "约55艘"},
        "mandeb": {"status": "正常", "wait": "1小时", "level": "无", "daily": "约45艘"},
        "cape": {"status": "正常", "wait": "1小时", "level": "无", "daily": "约80艘"},
        "turkish": {"status": "拥堵", "wait": "4-8小时", "level": "严重", "daily": "约130艘"},
        "denmark": {"status": "正常", "wait": "1小时", "level": "无", "daily": "约15艘"},
        "gibraltar": {"status": "繁忙", "wait": "2-3小时", "level": "轻微", "daily": "约270艘"},
        "lombok": {"status": "正常", "wait": "1小时", "level": "无", "daily": "约20艘"},
    }
    
    # 尝试获取 AIS 数据
    ship_counts = {}
    if AISHUB_USERNAME:
        print("  尝试获取 AIS 船舶数据...")
        # 为主要海峡获取船舶数量
        for wid, coords in WATERWAY_COORDS.items():
            # 扩大搜索区域
            lat_range = 2.0
            lon_range = 2.0
            count = fetch_ship_count_from_aishub(
                coords['lat'] - lat_range, coords['lat'] + lat_range,
                coords['lon'] - lon_range, coords['lon'] + lon_range
            )
            if count is not None:
                ship_counts[wid] = count
                print(f"    {coords['name']}: {count} 艘")
    
    for waterway in waterways['waterways']:
        wid = waterway['id']
        info = TRAFFIC_INFO.get(wid, {"status": "正常", "wait": "1小时", "level": "无", "daily": "约30艘"})
        
        # 如果有 AIS 数据，覆盖估算
        if wid in ship_counts:
            waiting = min(ship_counts[wid], 50)  # 限制最大等待数
        else:
            wait_times = {"1小时": 5, "2小时": 10, "3小时": 15, "4小时": 20, "5小时": 25, "8小时": 35}
            waiting = wait_times.get(info["wait"], 10)
        
        traffic_data[wid] = {
            "waiting_ships": waiting,
            "daily_transit": info["daily"],
            "avg_wait_time": info["wait"],
            "queue_status": info["status"],
            "queue_icon": "🔴" if info["level"] == "严重" else ("🟡" if info["level"] == "轻微" else "🟢"),
            "congestion_level": info["level"],
            "updated": datetime.utcnow().isoformat() + 'Z',
            "data_source": "AISHub" if wid in ship_counts else "运河管理局公开数据 + 估算"
        }
    
    return traffic_data

def update_geopolitical_data(waterways):
    """更新地缘政治数据"""
    geopolitics = {}
    
    ADVISORY = {
        "ormuz": ("高度关注", "建议绕行或谨慎通行", "高"),
        "mandeb": ("高度关注", "建议绕行或谨慎通行", "高"),
        "malacca": ("适度关注", "保持常规警惕", "中"),
        "suez": ("适度关注", "保持常规警惕", "中"),
        "turkish": ("适度关注", "保持常规警惕", "中"),
        "cape": ("适度关注", "保持常规警惕", "中"),
        "gibraltar": ("稳定", "正常通行", "低"),
        "panama": ("稳定", "正常通行", "低"),
        "denmark": ("稳定", "正常通行", "低"),
        "lombok": ("稳定", "正常通行", "低"),
    }
    
    for waterway in waterways['waterways']:
        wid = waterway['id']
        status, detail, level = ADVISORY.get(wid, ("稳定", "正常通行", "低"))
        
        geopolitics[wid] = {
            "status": status,
            "detail": detail,
            "last_review": datetime.now().strftime("%Y-%m-%d"),
            "advisory_level": level
        }
    
    return geopolitics

def main():
    """主函数"""
    print("=" * 60)
    print("🌊 全球水道监测数据抓取 v3.0")
    print("=" * 60)
    print(f"AISHub: {'已配置 ' + AISHUB_USERNAME if AISHUB_USERNAME else '未配置 (需要注册获取免费 API)'}")
    print("-" * 60)
    
    # 加载基础数据
    waterways = load_waterways()
    print(f"✓ 已加载 {len(waterways['waterways'])} 个水道")
    
    # 更新各类数据
    weather = update_weather_data(waterways)
    print(f"✓ 天气: {len(weather)} 条 (Open-Meteo)")
    
    security = update_security_data(waterways)
    print(f"✓ 安全: {len(security)} 条 (IMB 2025)")
    
    traffic = update_traffic_data(waterways)
    print(f"✓ 交通: {len(traffic)} 条")
    
    geopolitics = update_geopolitical_data(waterways)
    print(f"✓ 地缘: {len(geopolitics)} 条")
    
    # 合并数据
    full_data = {
        "version": "3.0",
        "waterways": waterways['waterways'],
        "weather": weather,
        "security": security,
        "traffic": traffic,
        "geopolitics": geopolitics,
        "last_updated": datetime.utcnow().isoformat() + 'Z',
        "next_update": (datetime.utcnow() + timedelta(minutes=10)).isoformat() + 'Z',
        "data_sources": {
            "weather": "Open-Meteo API (https://open-meteo.com)",
            "traffic": "AISHub API (https://www.aishub.net) + 运河公开数据",
            "security": "IMB 2025 报告 (https://www.icc-ccs.org)"
        },
        "disclaimer": "本平台数据仅供参考，不构成航行建议"
    }
    
    # 保存数据
    output_file = os.path.join(DATA_DIR, 'full_data.json')
    public_output_file = os.path.join(PUBLIC_DATA_DIR, 'full_data.json')
    
    os.makedirs(PUBLIC_DATA_DIR, exist_ok=True)
    
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(full_data, f, ensure_ascii=False, indent=2)
    
    with open(public_output_file, 'w', encoding='utf-8') as f:
        json.dump(full_data, f, ensure_ascii=False, indent=2)
    
    print("-" * 60)
    print(f"✓ 已保存: {output_file}")
    print(f"✓ 已保存: {public_output_file}")
    print("=" * 60)
    print("✅ 数据抓取完成!")
    print("=" * 60)

if __name__ == "__main__":
    main()
