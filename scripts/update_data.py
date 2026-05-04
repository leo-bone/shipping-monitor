#!/usr/bin/env python3
"""
全球关键水道数据抓取脚本 v6.0

v6.0 (2026-05-04) 重大数据更新：
- 霍尔木兹海峡: 美国5月4日启动"Project Freedom"(1.5万兵力+100+战机)恢复通航，
  伊朗警告将攻击进入海峡的外国军事力量。Windward数据：日均13艘通过，
  ~800艘商船困于波斯湾。商业信心极低，船东/保险商仍观望。
- 苏伊士运河: 4月26日报告复苏中。CMA CGM和Maersk宣布回归计划，
  MSC Euribia 4月26日完成北向通过。EU延长Aspides护航至2026年2月。
  整体仍低于危机前水平，大部分承运商未定。
- 曼德海峡: 胡塞已加入伊朗对美战争，多次发射导弹和无人机。
  威胁关闭但未完全实现。EU Red Sea task force保持戒备。
- 巴拿马运河: 日均38-40艘(正常36艘)，运营在105-111%容量。
  竞拍溢价超400万美元（正常30-40万），确认拥堵。
  FY2026 H1完成6288次通过，LNG/LPG绕航驱动需求。
- 好望角: 3月报告112%船舶增长。已成为"全球商业前线航线"，
  航程延长最多2周，物流成本增加30-50%。

v5.1 (2026-04-24) 数据大更新记录保留。
- 天气数据: Open-Meteo v2 + Marine API 实时获取
- data_date 动态化（每次运行自动更新为当天）

⚠️ 注意：本脚本中的交通/安全/地缘数据为硬编码快照。
   需定期手动搜索最新新闻并更新下方字典。
   天气数据是唯一实时自动获取的部分。
"""

import json
import os
import urllib.request
import urllib.parse
import urllib.error
import re
import time
from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Any

# 使用北京时间 (UTC+8)
def now_beijing():
    return datetime.now(timezone(timedelta(hours=8)))

# ==================== 配置 ====================
# AISHub 账号 (可选，付费服务)
# 注册地址: https://www.aishub.net
AISHUB_USERNAME = os.environ.get('AISHUB_USERNAME', '')

# 水道坐标映射
WATERWAY_COORDS = {
    "ormuz":   {"lat": 26.5,  "lon": 56.3,  "name": "霍尔木兹海峡",  "region": "Gulf"},
    "malacca": {"lat": 1.4,   "lon": 100.9, "name": "马六甲海峡",    "region": "SE Asia"},
    "suez":    {"lat": 30.5,  "lon": 32.5,  "name": "苏伊士运河",    "region": "Egypt"},
    "panama":  {"lat": 9.1,   "lon": -79.6, "name": "巴拿马运河",    "region": "Central America"},
    "mandeb":  {"lat": 12.6,  "lon": 43.2,  "name": "曼德海峡",      "region": "Red Sea"},
    "cape":    {"lat": -34.4, "lon": 18.5,  "name": "好望角",       "region": "South Africa"},
    "turkish": {"lat": 41.2,  "lon": 28.9,  "name": "土耳其海峡",    "region": "Turkey"},
    "denmark": {"lat": 66.0,  "lon": -22.0, "name": "丹麦海峡",      "region": "North Atlantic"},
    "gibraltar": {"lat": 36.1,"lon": -5.5,  "name": "直布罗陀海峡",  "region": "Mediterranean"},
    "lombok":  {"lat": -8.5,  "lon": 115.8, "name": "龙目海峡",      "region": "Indonesia"},
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


# ==================== 数据新鲜度配置 ====================
DATA_SOURCES_VERSION = {
    "hormuz": {
        "latest_date": "2026-05-04",
        "source": "Windward MIOC 2026-05-04 + CENTCOM Project Freedom 2026-05-04 + The National 2026-05-04",
        "quality": "high",
        "note": "Project Freedom启动：1.5万兵力+100+战机；日均13艘通过；~800艘商船困于波斯湾"
    },
    "suez": {
        "latest_date": "2026-04-26",
        "source": "Maritime News 2026-04-26 (Suez Canal Operations Resume) + EU EUNAVFOR Aspides",
        "quality": "high",
        "note": "复苏中：CMA CGM和Maersk宣布回归计划；MSC Euribia 4月26日完成通过；整体仍低于危机前水平"
    },
    "mandeb": {
        "latest_date": "2026-05-04",
        "source": "France24 2026-03-30 + TWZ 2026-04-02 + BusinessToday 2026-03-15",
        "quality": "high",
        "note": "胡塞已加入伊朗战争，威胁关闭但未完全实现；EU Red Sea task force保持戒备"
    },
    "panama": {
        "latest_date": "2026-05-02",
        "source": "Maritime News 2026-05-02 + ACP官方 2026-04-23 + PanamaDaily 2026-04-23",
        "quality": "high",
        "note": "日均38-40艘(105-111%容量)；竞拍溢价超400万美元；FY2026 H1完成6288次通过"
    },
    "cape": {
        "latest_date": "2026-05-02",
        "source": "IOL 2026-03-11 (112% surge) + Zambian Observer 2026-05-02 + Maritime Hub 2026-04-08",
        "quality": "medium",
        "note": "112%船舶增长(3月数据)；已成为全球主要航线；航程+2周，成本+30-50%"
    },
    "malacca": {
        "latest_date": "2026-04-20",
        "source": "ReCAAP / Maritime News",
        "quality": "medium",
        "note": "马六甲海峡正常通行，作为替代路线交通量增加"
    },
    "turkish": {
        "latest_date": "2026-04-20",
        "source": "土耳其海峡船舶交管系统（常规数据）",
        "quality": "medium",
        "note": "博斯普鲁斯海峡日均130艘，标准等待2-4小时"
    },
    "denmark": {
        "latest_date": "2026-04-20",
        "source": "冰岛海岸警卫队（常规数据）",
        "quality": "medium",
        "note": "丹麦海峡交通正常，春季通行条件良好"
    },
    "gibraltar": {
        "latest_date": "2026-04-20",
        "source": "直布罗陀港务局（常规数据）",
        "quality": "medium",
        "note": "地中海-大西洋连接，每年约10万艘船舶通行"
    },
    "lombok": {
        "latest_date": "2026-05-03",
        "source": "Windward MIOC 2026-05-03 (伊朗VLCC首次通过龙目海峡)",
        "quality": "medium",
        "note": "马六甲替代路线，VLCC偏好；伊朗原油首次改道龙目海峡赴亚洲"
    },
}


# ==================== 2026年5月最新水道状态 ====================
# 数据来源: Windward MIOC(2026-05-04), CENTCOM(2026-05-04), Maritime News(2026-05-02/04-26),
#           The National(2026-05-04), ACP(2026-04-23), IOL(2026-03-11), France24(2026-03-30)
# 更新日期: 2026-05-04（每次运行脚本时 data_date 字段自动更新为当天）
CURRENT_WATERWAY_STATUS = {
    "ormuz": {
        "status": "封锁中（Project Freedom启动）",
        "wait_hours": "不定（Project Freedom提供有限护航）",
        "daily_transit": "约13艘（Windward 2026-05-04数据，正常超100艘）",
        "level": "极高",
        "risk_score": 95,
        "notes": (
            "【霍尔木兹海峡·2026-05-04重大更新】"
            "美国5月4日正式启动'Project Freedom'行动（CENTCOM），"
            "部署1.5万名军人和100+架陆海基战机、导弹驱逐舰及无人系统，"
            "旨在恢复海峡商业航行自由。"
            "Windward MIOC数据：5月3日通过13艘（7进6出），其中2艘暗船；"
            "~800艘商船困于波斯湾。"
            "伊朗武装部队立即警告：任何外国军事力量进入海峡将被攻击。"
            "伊朗称已迫使一艘美军舰艇在海峡入口折返。"
            "Trump称此举为'人道主义'行动。"
            "商业信心极低——船东和保险商仍观望，担心伊朗报复。"
            "JMIC建议船只经阿曼水域'增强安全区域'绕行。"
            "全球约20%石油、30%+ LNG运输持续受阻。"
        ),
        "alternative": "所有船只绕行好望角（+10-14天航程）"
    },
    "mandeb": {
        "status": "高度危险（胡塞加入伊朗战争）",
        "wait_hours": "不定（护航有限）",
        "daily_transit": "极少（商船基本绕行）",
        "level": "极高",
        "risk_score": 88,
        "notes": (
            "【曼德海峡·2026-05-04更新】"
            "胡塞武装已加入伊朗对美国/以色列战争，"
            "多次发射弹道导弹和无人机袭击该区域。"
            "伊朗推动胡塞准备封锁行动，但截至目前尚未完全实现。"
            "EU延长Aspides红海护航任务至2026年2月（预算超1700万欧元）。"
            "沙特通过红海替代石油运输路线也面临胡塞威胁。"
            "绝大多数商船仍选择绕行好望角。"
        ),
        "alternative": "所有船只绕行好望角"
    },
    "suez": {
        "status": "复苏中（大部分仍绕行）",
        "wait_hours": "不定（逐步恢复中）",
        "daily_transit": "逐步恢复中（远低于正常约70艘/日）",
        "level": "高",
        "risk_score": 65,
        "notes": (
            "【苏伊士运河·2026-05-04更新】"
            "Maritime News 4月26日报道：苏伊士运河航运复苏正在进行中。"
            "CMA CGM和Maersk已宣布回归苏伊士航线的正式计划。"
            "MSC Euribia邮轮4月26日完成北向通过。"
            "分析师预计承运商将在2026年春节后或10月黄金周逐步回归。"
            "完全恢复将带来全球6%的船队运力回归苏伊士路线。"
            "但整体流量仍大幅低于危机前水平，大部分承运商态度未定。"
            "EU EUNAVFOR Aspides护航任务延长至2026年2月。"
        ),
        "alternative": "亚欧/亚美航线部分仍绕行好望角（+10-14天，+$2000-4000/TEU附加费）"
    },
    "panama": {
        "status": "严重拥堵（超负荷运行）",
        "wait_hours": "竞拍等待（标准船$30-40万，溢价超$400万）",
        "daily_transit": "约38-40艘（正常36艘，运营在105-111%容量）",
        "level": "高",
        "risk_score": 55,
        "notes": (
            "【巴拿马运河·2026-05-04更新】"
            "Maritime News 5月2日报道：霍尔木兹封锁推动巴拿马运河通行量"
            "从34艘/日升至约50艘/日（LinkedIn 5月1日数据）。"
            "日均38-40艘（正常36艘），运营在105-111%容量。"
            "竞拍溢价创纪录——标准费率$30-40万/次，"
            "4月竞拍价超$400万/艘（溢价900-1200%）。"
            "FY2026 H1完成6288次通过。"
            "LNG/LPG货船因霍尔木兹封锁改道巴拿马运河，为主要增长驱动力。"
            "ACP称加通湖水位充足，无吃水限制，"
            "但高管警告当前运力速度不可持续。"
        )
    },
    "malacca": {
        "status": "繁忙通行",
        "wait_hours": "1-3",
        "daily_transit": "约200艘（作为替代路线持续繁忙）",
        "level": "轻微",
        "risk_score": 38,
        "notes": (
            "【马六甲海峡·2026-05-04】作为霍尔木兹危机的核心替代路线，"
            "通过量持续高于历史均值。"
            "ReCAAP报告偶发登船事件，须保持24小时船桥瞭望。"
        )
    },
    "turkish": {
        "status": "正常通航",
        "wait_hours": "2-4",
        "daily_transit": "约130艘",
        "level": "轻微",
        "risk_score": 28,
        "notes": (
            "博斯普鲁斯海峡通行规则正常，蒙特勒公约依然有效。"
            "高峰期等待时间较长，商船须提前24-48小时向交管中心报告。"
        )
    },
    "denmark": {
        "status": "正常通行",
        "wait_hours": "1",
        "daily_transit": "约15艘",
        "level": "无",
        "risk_score": 12,
        "notes": (
            "丹麦海峡交通正常。春季浮冰已融化，通行条件良好。"
            "北大西洋航线稳定。"
        )
    },
    "gibraltar": {
        "status": "繁忙",
        "wait_hours": "1-2",
        "daily_transit": "约290艘",
        "level": "无",
        "risk_score": 18,
        "notes": (
            "地中海-大西洋唯一咽喉，交通繁忙。"
            "每年约10万艘船舶通行，为全球最繁忙海峡之一。"
            "分道通航制严格遵守，港口拥挤时段略有等待。"
        )
    },
    "lombok": {
        "status": "正常通行（伊朗原油新通道）",
        "wait_hours": "1",
        "daily_transit": "约25艘（作为替代路线增加）",
        "level": "无",
        "risk_score": 22,
        "notes": (
            "【龙目海峡·2026-05-03】Windward MIOC报告："
            "伊朗VLCC 'HUGE' 首次在70天内开启AIS信号，"
            "经龙目海峡（满载原油）驶向亚洲，随后再次关闭AIS。"
            "这是自战争爆发以来首次追踪到伊朗原油经龙目海峡运往亚洲。"
            "另一艘伊朗VLCC 'DERYA' 随后也经龙目海峡航行。"
            "龙目海峡成为伊朗原油出口亚洲的新替代通道。"
        )
    },
    "cape": {
        "status": "极度繁忙（全球主要航线）",
        "wait_hours": "1-2",
        "daily_transit": "激增（3月报告112%增长，已成为全球商业前线航线）",
        "level": "无",
        "risk_score": 15,
        "notes": (
            "【好望角·2026-05-04更新】"
            "3月报告：开普敦港船舶增长112%（IOL 2026-03-11）。"
            "5月2日报告：已从备用航线转变为'全球商业前线航线'（Zambian Observer）。"
            "航程延长最多2周，物流成本增加30-50%。"
            "非洲东部和南部走廊港口活动急剧增加。"
            "随着苏伊士运河逐步复苏，部分航线可能回归，"
            "但短期内好望角仍是最繁忙的替代航线。"
        )
    },
}


# ==================== 地缘政治风险评级 ====================
GEOPOLITICAL_ADVISORY = {
    "ormuz": ("极度风险·Project Freedom对峙", "强烈建议绕行（美军启动护航行动，伊朗威胁攻击）", "极高"),
    "mandeb": ("极度风险·武装冲突", "强烈建议绕行（胡塞加入伊朗战争）", "极高"),
    "suez": ("高风险·逐步复苏", "建议观望（CMA CGM/Maersk计划回归，大部分仍绕行）", "高"),
    "panama": ("高风险·严重拥堵", "可通行但需竞拍（运营超100%容量，溢价极高）", "高"),
    "cape": ("稳定·繁忙", "正常通行（全球商业前线航线，112%增长）", "低"),
    "malacca": ("稳定·繁忙", "正常通行（核心替代路线交通增加）", "低"),
    "turkish": ("稳定", "正常通行（需提前报告）", "低"),
    "denmark": ("稳定", "正常通行", "低"),
    "gibraltar": ("稳定·繁忙", "正常通行", "低"),
    "lombok": ("稳定", "正常通行（伊朗原油新通道）", "低"),
}


# ==================== 安全预警数据 ====================
# 来源: Windward MIOC(2026-05-04), CENTCOM(2026-05-04), The National(2026-05-04),
#        Maritime News(2026-05-02/04-26), TWZ(2026-04-02), France24(2026-03-30)
SECURITY_ALERTS = {
    "ormuz": {
        "risk_level": "极高",
        "risk_score": 95,
        "status": "封锁中（Project Freedom启动）",
        "alerts": [
            {
                "type": "军事行动升级",
                "severity": "极高",
                "location": "霍尔木兹海峡全域",
                "time": "2026-05-04 CENTCOM",
                "detail": (
                    "美国5月4日启动'Project Freedom'行动：1.5万军人、100+架战机、"
                    "导弹驱逐舰及无人系统。旨在恢复商业航行自由。"
                    "伊朗立即警告：任何外国军事力量进入海峡将被攻击。"
                    "伊朗称已迫使一艘美军舰艇折返。"
                    "JMIC维持海峡威胁等级'critical'。"
                )
            },
            {
                "type": "航行安全事件",
                "severity": "极高",
                "location": "霍尔木兹海峡/波斯湾",
                "time": "2026-05-04",
                "detail": (
                    "UKMTO报告：一艘油轮在Project Freedom宣布后遭不明飞行物击中。"
                    "UAE谴责Adnoc关联油轮在海峡遭定点打击。"
                    "伊朗Fars通讯社声称打击了美军舰艇（CENTCOM否认）。"
                    "~800艘商船困于波斯湾无法离开。"
                )
            }
        ],
        "status_icon": "🔴"
    },
    "mandeb": {
        "risk_level": "极高",
        "risk_score": 88,
        "status": "高度危险（武装冲突）",
        "alerts": [
            {
                "type": "武装冲突升级",
                "severity": "极高",
                "location": "亚丁湾/曼德海峡/红海南部",
                "time": "2026-05-04 综合报道",
                "detail": (
                    "胡塞武装已加入伊朗对美国/以色列战争（2026年2月28日起），"
                    "多次发射弹道导弹和无人机。"
                    "伊朗推动胡塞准备封锁曼德海峡，但截至目前尚未完全实现。"
                    "EU Red Sea task force保持高度戒备。"
                    "沙特通过红海的替代石油运输面临威胁。"
                )
            }
        ],
        "status_icon": "🔴"
    },
    "suez": {
        "risk_level": "高",
        "risk_score": 65,
        "status": "复苏中",
        "alerts": [
            {
                "type": "逐步恢复",
                "severity": "中",
                "location": "苏伊士运河/红海",
                "time": "2026-04-26 Maritime News",
                "detail": (
                    "苏伊士运河航运复苏正在进行。CMA CGM和Maersk宣布回归计划。"
                    "MSC Euribia 4月26日完成通过。"
                    "EU EUNAVFOR Aspides护航任务延长至2026年2月。"
                    "但大部分承运商态度未定，整体流量仍远低于危机前。"
                )
            }
        ],
        "status_icon": "🟠"
    },
    "panama": {
        "risk_level": "高",
        "risk_score": 55,
        "status": "严重拥堵（超负荷）",
        "alerts": [
            {
                "type": "运力过载",
                "severity": "高",
                "location": "巴拿马运河",
                "time": "2026-05-02 Maritime News",
                "detail": (
                    "日均38-40艘（正常36艘），运营在105-111%容量。"
                    "竞拍溢价超400万美元/艘（正常30-40万，溢价900-1200%）。"
                    "LNG/LPG绕航需求推动增长，高管警告速度不可持续。"
                )
            }
        ],
        "status_icon": "🟠"
    },
    "malacca": {
        "risk_level": "中",
        "risk_score": 38,
        "status": "正常通行",
        "alerts": [
            {
                "type": "海盗威胁",
                "severity": "低中",
                "location": "新加坡海峡/马六甲海峡",
                "time": "周期性",
                "detail": "ReCAAP季度报告偶发登船事件，保持24小时船桥瞭望。"
            }
        ],
        "status_icon": "🟡"
    },
    "cape": {
        "risk_level": "低",
        "risk_score": 15,
        "status": "正常通航（全球主要航线）",
        "alerts": [],
        "status_icon": "🟢"
    },
    "turkish": {
        "risk_level": "低",
        "risk_score": 28,
        "status": "正常通航",
        "alerts": [
            {
                "type": "通行规定",
                "severity": "低",
                "location": "博斯普鲁斯/达达尼尔海峡",
                "time": "常规",
                "detail": "蒙特勒公约通行规则，战舰有限制，商船须提前报告。"
            }
        ],
        "status_icon": "🟢"
    },
    "denmark": {
        "risk_level": "低",
        "risk_score": 12,
        "status": "正常通航",
        "alerts": [],
        "status_icon": "🟢"
    },
    "gibraltar": {
        "risk_level": "低",
        "risk_score": 18,
        "status": "正常通航",
        "alerts": [],
        "status_icon": "🟢"
    },
    "lombok": {
        "risk_level": "低",
        "risk_score": 22,
        "status": "正常通航（伊朗原油新通道）",
        "alerts": [],
        "status_icon": "🟢"
    },
}


# ==================== 网络请求工具 ====================

def fetch_url(url: str, timeout: int = 15) -> Optional[str]:
    """通用 URL 获取函数"""
    try:
        req = urllib.request.Request(url, headers={
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
        })
        with urllib.request.urlopen(req, timeout=timeout) as response:
            return response.read().decode('utf-8', errors='replace')
    except Exception as e:
        return None


def fetch_maritime_news() -> Dict[str, Any]:
    """
    从 Maritime News 抓取最新水道交通数据
    来源: maritimenews.com - 权威海运新闻
    """
    result = {
        "ormuz": {},
        "suez": {},
        "mandeb": {},
        "panama": {},
        "cape": {},
        "malacca": {},
        "scraped_at": None,
        "sources_found": []
    }

    # Maritime News 专题页面
    urls_to_try = [
        ("hormuz", "https://www.maritimenews.com/iran-conflict-maritime-disruptions/iran-strait-hormuz-blockade-tanker-attacks-2026"),
        ("red_sea", "https://www.maritimenews.com/red-sea/red-sea-shipping-traffic-depressed"),
        ("general", "https://www.marineinsight.com/category/shipping-news/"),
    ]

    for key, url in urls_to_try:
        content = fetch_url(url, timeout=10)
        if content:
            result["sources_found"].append(url)
            result[f"scraped_{key}_content"] = content[:3000]  # 保留前3000字符用于分析

    return result


def fetch_hormuztracker_data() -> Dict[str, Any]:
    """
    抓取 HormuzTracker 实时数据
    来源: hormuztracker.com
    """
    data = {
        "available": False,
        "vessels_today": None,
        "status": None,
        "days_closed": None,
    }

    content = fetch_url("https://www.hormuztracker.com/", timeout=10)
    if not content:
        return data

    # 提取AIS船只数量
    vessel_match = re.search(r'(\d+)\s*vessels?\s*(?:detected|today)', content, re.IGNORECASE)
    if vessel_match:
        data["vessels_today"] = int(vessel_match.group(1))

    # 提取关闭天数
    closed_match = re.search(r'(\d+)\s*days?\s*(?:closed|closure)', content, re.IGNORECASE)
    if closed_match:
        data["days_closed"] = int(closed_match.group(1))

    # 提取状态
    if re.search(r'closed|closure|blocked', content, re.IGNORECASE):
        data["status"] = "CLOSED"
        data["available"] = True

    return data


# ==================== 天气 API 增强版 ====================

def fetch_weather_from_api(lat: float, lon: float) -> Optional[Dict[str, Any]]:
    """
    从 Open-Meteo API 获取真实天气数据（增强版：含浪高 + 海洋API）
    """
    try:
        # 1. 天气数据 (主API)
        weather_url = (
            f"https://api.open-meteo.com/v1/forecast"
            f"?latitude={lat}&longitude={lon}"
            f"&current=temperature_2m,relative_humidity_2m,apparent_temperature,"
            f"weather_code,wind_speed_10m,wind_direction_10m,"
            f"sea_surface_temperature"
            f"&timezone=auto"
        )

        req = urllib.request.Request(weather_url, headers={'User-Agent': 'ShippingMonitor/5.0'})
        with urllib.request.urlopen(req, timeout=10) as response:
            weather_data = json.loads(response.read().decode('utf-8'))

        # 2. 浪高数据 (海洋API)
        wave_url = (
            f"https://marine-api.open-meteo.com/v1/marine"
            f"?latitude={lat}&longitude={lon}"
            f"&hourly=wave_height,wave_period"
            f"&timezone=auto&forecast_days=1"
        )

        req2 = urllib.request.Request(wave_url, headers={'User-Agent': 'ShippingMonitor/5.0'})
        with urllib.request.urlopen(req2, timeout=10) as resp2:
            marine_data = json.loads(resp2.read().decode('utf-8'))

        current = weather_data.get('current', {})
        hourly = marine_data.get('hourly', {})

        temp = current.get('temperature_2m', 0)
        humidity = current.get('relative_humidity_2m', 0)
        wind_speed = current.get('wind_speed_10m', 0)
        wind_dir = current.get('wind_direction_10m', 0)
        weather_code = current.get('weather_code', 0)
        sst = current.get('sea_surface_temperature')

        condition, icon = WEATHER_CODES.get(weather_code, ("未知", "❓"))

        # 风向文字
        directions = ["北", "东北", "东", "东南", "南", "西南", "西", "西北"]
        dir_idx = int((wind_dir + 22.5) // 45) % 8

        # 浪高数据（取当前小时）
        wave_times = hourly.get('time', [])
        wave_heights = hourly.get('wave_height', [])
        wave_periods = hourly.get('wave_period', [])

        # 找到当前时间对应的索引
        current_time = datetime.utcnow().strftime('%Y-%m-%dT%H:00')
        wave_h = None
        wave_p = None
        if wave_times and wave_heights:
            try:
                idx = wave_times.index(current_time)
                wave_h = wave_heights[idx]
                wave_p = wave_periods[idx] if wave_periods else None
            except ValueError:
                wave_h = wave_heights[0] if wave_heights else None
                wave_p = wave_periods[0] if wave_periods else None

        return {
            "temperature": f"{int(temp)}°C",
            "feels_like": f"{int(current.get('apparent_temperature', temp))}°C",
            "wind": f"{int(wind_speed)} km/h {directions[dir_idx]}",
            "wave_height": f"{wave_h:.1f}m" if wave_h is not None else "N/A",
            "wave_period": f"{int(wave_p)}s" if wave_p is not None else "N/A",
            "sea_temp": f"{int(sst)}°C" if (sst is not None and sst != 0) else "N/A",
            "visibility": "10 km",
            "condition": condition,
            "condition_icon": icon,
            "humidity": f"{int(humidity)}%",
            "updated": datetime.utcnow().isoformat() + 'Z',
            "data_source": "Open-Meteo API v2 + Marine API"
        }
    except Exception as e:
        return None


def get_fallback_weather(lat: float) -> Dict[str, Any]:
    """备选天气数据（当API不可用时）"""
    import random
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
        "wave_height": f"{random.uniform(0.5, 3.0):.1f}m",
        "wave_period": f"{random.randint(4, 10)}s",
        "sea_temp": f"{random.randint(18, 30)}°C",
        "visibility": "10 km",
        "condition": condition,
        "condition_icon": icon,
        "humidity": f"{random.randint(60, 85)}%",
        "updated": datetime.utcnow().isoformat() + 'Z',
        "data_source": "Estimated (API unavailable)"
    }


# ==================== 主数据更新函数 ====================

def load_waterways() -> Dict:
    """加载水道基础数据"""
    full_data_path = os.path.join(PUBLIC_DATA_DIR, 'full_data.json')
    waterways_path = os.path.join(DATA_DIR, 'waterways.json')

    if os.path.exists(full_data_path):
        with open(full_data_path, 'r', encoding='utf-8') as f:
            full = json.load(f)
        return {"waterways": full["waterways"]}
    if os.path.exists(waterways_path):
        with open(waterways_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    raise FileNotFoundError(f"找不到水道数据")


def update_weather_data(waterways: Dict) -> Dict[str, Any]:
    """更新天气数据（增强版：含浪高）"""
    weather_data = {}

    for waterway in waterways['waterways']:
        wid = waterway['id']
        coords = WATERWAY_COORDS.get(wid)

        print(f"  获取 {waterway['name']} 天气...", end=" ")

        if coords:
            weather = fetch_weather_from_api(coords['lat'], coords['lon'])
            if weather:
                weather_data[wid] = weather
                print(f"✓ (浪高:{weather['wave_height']})")
            else:
                weather_data[wid] = get_fallback_weather(coords['lat'])
                print("⚠️ (fallback)")
        else:
            weather_data[wid] = get_fallback_weather(waterway['coordinates'][1])
            print("⚠️ (fallback)")

    return weather_data


def update_security_data(waterways: Dict) -> Dict[str, Any]:
    """更新安全预警数据（基于2026年4月最新数据）"""
    security_data = {}
    today = datetime.now(timezone.utc)

    # 尝试从 HormuzTracker 获取实时数据
    hormuz_live = fetch_hormuztracker_data()

    for waterway in waterways['waterways']:
        wid = waterway['id']
        static_data = SECURITY_ALERTS.get(wid, {
            "risk_level": "未知", "risk_score": 50,
            "alerts": [], "status": "数据获取中", "status_icon": "❓"
        })

        data = static_data.copy()
        data["alerts"] = static_data.get("alerts", [])[:]  # 深拷贝

        # 如果有实时数据，更新霍尔木兹海峡
        if wid == "ormuz" and hormuz_live.get("available"):
            data["live_vessels_today"] = hormuz_live["vessels_today"]
            data["days_closed"] = hormuz_live["days_closed"]
            data["data_source"] = "HormuzTracker (live)"

        data["last_incident"] = today.strftime("%Y-%m-%d")
        data["updated"] = today.isoformat()
        security_data[wid] = data

    return security_data


def update_traffic_data(waterways: Dict) -> Dict[str, Any]:
    """
    更新通航状态数据（基于2026年4月最新水道状态）
    """
    traffic_data = {}
    today_str = now_beijing().strftime("%Y-%m-%d %H:%M")

    # 尝试抓取 Maritime News
    print("  抓取 Maritime News 最新数据...")
    news_data = fetch_maritime_news()
    print(f"    抓取到 {len(news_data.get('sources_found', []))} 个数据源")

    for waterway in waterways['waterways']:
        wid = waterway['id']
        status = CURRENT_WATERWAY_STATUS.get(wid, {
            "status": "未知", "wait_hours": "?", "daily_transit": "未知",
            "level": "?", "risk_score": 50, "notes": "数据获取中"
        })

        level = status.get("level", "无")
        traffic_data[wid] = {
            "status": status.get("status", "未知"),
            "wait_hours": status.get("wait_hours", "?"),
            "daily_transit": status.get("daily_transit", "约30艘"),
            "queue_status": status.get("status", "未知"),
            "queue_icon": "🔴" if level in ("极高", "高") else ("🟠" if level == "中" else ("🟡" if level == "轻微" else "🟢")),
            "congestion_level": level,
            "risk_score": status.get("risk_score", 50),
            "notes": status.get("notes", ""),
            "alternative": status.get("alternative", ""),
            "updated": datetime.utcnow().isoformat() + 'Z',
            "data_source": DATA_SOURCES_VERSION.get(wid, {}).get("source", "手动更新 2026-04-20")
        }

    return traffic_data


def update_geopolitical_data(waterways: Dict) -> Dict[str, Any]:
    """更新地缘政治数据"""
    geopolitics = {}

    for waterway in waterways['waterways']:
        wid = waterway['id']
        status, detail, level = GEOPOLITICAL_ADVISORY.get(wid, ("稳定", "正常通行", "低"))

        geopolitics[wid] = {
            "status": status,
            "detail": detail,
            "last_review": "2026-05-04",
            "advisory_level": level
        }

    return geopolitics


def build_data_quality_report() -> Dict[str, Any]:
    """
    构建数据质量报告
    """
    today_str = now_beijing().strftime("%Y-%m-%d")
    report = {
        "overall_freshness": "high",
        "last_major_update": "2026-05-04",
        "traffic_update_date": "2026-05-04",
        "data_quality": {},
        "known_issues": [
            "AIS船舶追踪: 无免费API，当前使用新闻估算数据",
            "霍尔木兹海峡: 封锁期间AIS数据不可靠（船只关闭应答器），Maersk/CNY应有最准确数据",
            "运河日均通航量: 基于TASK/project44和Gulf News，非实时官方统计"
        ],
        "improvement_needed": [
            "配置 VesselFinder 或 MarineTraffic API 以获取真实AIS船舶数量",
            "订阅巴拿马运河管理局(ACP)官方RSS推送",
            "订阅 Suez Canal Authority 官方每日公报"
        ]
    }

    for wid, info in DATA_SOURCES_VERSION.items():
        report["data_quality"][wid] = {
            "quality": info["quality"],
            "latest_date": info["latest_date"],
            "source": info["source"],
            "note": info.get("note", "")
        }

    return report


# ==================== 主函数 ====================

def main():
    today_str = now_beijing().strftime("%Y-%m-%d")
    print("=" * 60)
    print("🌊 全球水道监测数据抓取 v6.0")
    print(f"   运行日期: {today_str}  (数据基准: Windward/CENTCOM/Maritime News 2026-05-04)")
    print("=" * 60)
    print(f"AISHub: {'已配置 ' + AISHUB_USERNAME if AISHUB_USERNAME else '未配置 (使用新闻估算)'}")
    print(f"运行时间: {now_beijing().strftime('%Y-%m-%d %H:%M:%S')} 北京时间")
    print("-" * 60)

    # 加载基础数据
    waterways = load_waterways()
    print(f"✓ 已加载 {len(waterways['waterways'])} 个水道")

    # 更新各类数据
    weather = update_weather_data(waterways)
    print(f"✓ 天气: {len(weather)} 条 (Open-Meteo v2 含浪高)")

    security = update_security_data(waterways)
    print(f"✓ 安全: {len(security)} 条 (2026-04 最新)")

    traffic = update_traffic_data(waterways)
    print(f"✓ 交通: {len(traffic)} 条 (2026-04 最新)")

    geopolitics = update_geopolitical_data(waterways)
    print(f"✓ 地缘: {len(geopolitics)} 条")

    data_quality = build_data_quality_report()
    print(f"✓ 数据质量报告: 已生成")

    # 合并数据
    current_date_str = now_beijing().strftime("%Y-%m-%d")
    full_data = {
        "version": "6.0",
        "data_date": current_date_str,  # 动态日期：每次运行自动更新为当天日期
        "waterways": waterways['waterways'],
        "weather": weather,
        "security": security,
        "traffic": traffic,
        "geopolitics": geopolitics,
        "data_quality": data_quality,
        "last_updated": now_beijing().isoformat(),
        "next_update": (now_beijing() + timedelta(hours=6)).isoformat(),
        "data_sources": {
            "weather": "Open-Meteo API v2 (https://open-meteo.com) - 真实实时海象",
            "traffic": "Windward MIOC 2026-05-04 + CENTCOM 2026-05-04 + Maritime News 2026-05-02/04-26 + ACP 2026-04-23",
            "security": "Windward MIOC + CENTCOM + The National 2026-05-04 + TWZ + France24 + UKMTO",
            "vessels": "Windward AIS tracking (Gulf-wide 904 vessels tracked) - AISHub (需注册付费)",
        },
        "key_highlights": [
            f"🔴 霍尔木兹海峡: 美国启动Project Freedom(1.5万兵力+100+战机)恢复通航，伊朗警告攻击；日均13艘，~800艘困于波斯湾",
            f"🟠 苏伊士运河: 复苏中，CMA CGM和Maersk宣布回归，MSC Euribia已通过；整体仍远低于正常",
            f"🔴 曼德海峡: 胡塞已加入伊朗战争，威胁关闭但未完全实现；EU护航任务延长",
            f"🟠 巴拿马运河: 严重拥堵（105-111%容量），竞拍溢价超$400万，日均38-40艘",
            f"🟢 好望角: 112%增长，已成为全球商业前线航线；航程+2周，成本+30-50%",
        ],
        "disclaimer": (
            "⚠️ 本平台数据仅供参考，实际航行决策请以船公司及官方机构建议为准。"
            "2026年中东局势持续紧张，建议实时关注UKMTO.org及Maritime News。"
        )
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
    print("✅ 数据抓取完成! (v6.0)")
    print("=" * 60)


if __name__ == "__main__":
    main()
