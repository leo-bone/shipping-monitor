#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
水道数据快照更新 —— 2026-09-15

用途：
    把人工核实的地缘/通航/安全快照写入 data/full_data.json 与
    public/data/full_data.json，并把 data_date 推进到快照日期。

为什么不直接让 update_data.py 生成：
    update_data.py 里的地缘与通航数字是硬编码的旧快照（停留在 2026-05-04），
    而 last_updated 每次抓取都会刷新，导致站点「看着是今天更新，内容却是四个月前」。
    本脚本只更新人工核实的部分，天气仍由 update_data.py 实时抓取，互不覆盖。

数据来源（2026-09-15 核实）：
    - 新华社/路透 2026-09-14：霍尔木兹单日通行量降至个位数
    - straits.live 2026-09-15：Hormuz 关闭第 198 天
    - Maritime News 2026-09-11/13：Hormuz 通行低迷、9/13 船只被击中
    - Windward 2026-09：巴拿马运河 9/15 起降至 32 艘/日
    - Zencargo 2026-09-08：苏伊士 8 月通行 196 艘（同比 +36%）
    - 中新社 2026-09-08：伊朗议会审议海峡管理、伊阿谈判进入最后阶段

用法：
    python3 scripts/apply_snapshot_2026_09.py
"""

import json
import os
from datetime import datetime, timedelta, timezone

SNAPSHOT_DATE = "2026-09-15"
SCRIPT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TARGETS = [
    os.path.join(SCRIPT_DIR, "data", "full_data.json"),
    os.path.join(SCRIPT_DIR, "public", "data", "full_data.json"),
]

NOW = datetime.now(timezone(timedelta(hours=8)))
NOW_ISO = NOW.isoformat()
UPDATED_Z = NOW.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"


def sec(d, name, wid):
    """安全取分区字典。"""
    return d.setdefault(name, {}).setdefault(wid, {})


def update(d):
    # ---------- 顶层元信息 ----------
    d["data_date"] = SNAPSHOT_DATE
    d["last_updated"] = NOW_ISO
    d["version"] = "7.0"
    d["next_update"] = "地缘/通航快照为人工核实，建议每周复核；天气每小时自动抓取"

    # ---------- 关键看点 ----------
    d["key_highlights"] = [
        "🔴 霍尔木兹海峡：自 2026-02-28 起对正常商业通行实际关闭，已第 198 天。"
        "近期日均通行降至个位数（6-10 艘），远低于危机前约 85-125 艘/日。",
        "🔴 曼德海峡：胡塞武装 9 月相继控制红海摩卡港与丕林岛，"
        "南部红海—曼德海峡威胁等级维持「重大」，苏伊士复航因此仍脆弱。",
        "🟠 苏伊士运河：8 月通行 196 艘（同比 +36%），运力 168 万 TEU（同比 +184%），"
        "但东—西向份额仅约 18.7%（危机前约 80%），复苏可逆。",
        "🟠 巴拿马运河：因干旱 9 月 15 日起日均通行降至 32 艘（原约 40 艘），"
        "9 月 1 日单个 Neopanamax 船位拍出 530 万美元历史高价。",
        "🟢 好望角：同时承接霍尔木兹、苏伊士、巴拿马三条通道的分流，"
        "已成为默认绕行路线，航程与成本显著增加。",
    ]

    # ---------- 霍尔木兹 ----------
    s = sec(d, "security", "ormuz")
    s.update({
        "risk_level": "极高",
        "risk_score": 98,
        "status": "实际关闭（仅供特许船只通行）",
        "status_icon": "🔴",
        "days_closed": 198,
        "last_incident": "2026-09-13 一艘过境商船被不明飞行物击中起火，船员撤离（UKMTO）；"
                         "另有一艘伊朗商船在格什姆岛附近被击中，至少 1 人死亡。",
        "data_source": "新华社/路透 2026-09-14 + straits.live 2026-09-15 + UKMTO + Maritime News 2026-09-13",
        "updated": UPDATED_Z,
        "alerts": [
            {"type": "海峡实际关闭", "severity": "极高", "location": "霍尔木兹海峡全域",
             "time": "2026-09-15",
             "detail": "自 2026-02-28 关闭声明起已第 198 天。通行不再是权利而是逐船审批："
                       "伊朗通过新设的波斯湾海峡管理局发放许可，并按船收取据报道达七位数美元的通行费。"
                       "战争险保费约为正常水平的 40 倍（约船体价值的 10%），"
                       "全球前九大集装箱班轮公司中已有 4 家公开表示停止使用该海峡。"},
            {"type": "外交进程反复", "severity": "高", "location": "波斯湾",
             "time": "2026-06-17 起",
             "detail": "6 月 17 日《伊斯兰堡备忘录》（巴基斯坦斡旋、卡塔尔/沙特/土耳其/埃及协助的 14 点美伊协议）"
                       "曾短暂重开海峡，但停火数日内破裂。原定 9 月 14 日在塞拉莱举行的"
                       "伊朗—伊拉克—海湾国家新航线会议于前一天宣布延期，且伊方表示该航线不等于重开海峡。"
                       "伊朗议会在审议海峡未来管理事项，伊朗与阿曼就临时安全航道的谈判称已进入「最后阶段」。"},
            {"type": "绕行通道受挫", "severity": "高", "location": "阿拉伯半岛",
             "time": "2026-09-11",
             "detail": "自伊拉克方向发射的无人机 9 月 11 日击中沙特东西向输油管道，该管道已停输——"
                       "这是绕过霍尔木兹的最大单一替代路径被切断。约有 300-400 艘船在湾内锚泊待命，" 
                       "水雷威胁仍在。"},
        ],
    })

    t = sec(d, "traffic", "ormuz")
    t.update({
        "status": "实际关闭（通行量极低）",
        "daily_transit": "个位数：约 6-10 艘/日（10 日均值约 10-15 艘），危机前约 85-125 艘/日",
        "wait_hours": "不适用（多数船舶绕行或锚泊待命）",
        "queue_status": "约 300-400 艘在湾内及外围锚泊",
        "queue_icon": "🔴",
        "congestion_level": "通行受限",
        "risk_score": 98,
        "notes": "【2026-09-15 更新】据新华社援引路透 9 月 14 日报道，上周末两天内单日通行量降至个位数："
                 "4 艘驶出（含能源运输船）、10 艘货船驶入，低于此前 10 天日均 14 艘。"
                 "克普勒数据显示 9 月 7 日仅 7 艘商船过境，创 5 月以来最低。"
                 "部分船舶关闭 AIS 通行，实际数字可能更高但仍处极低水平。"
                 "值得注意的是，经霍尔木兹的石油出口近期回升至约 1000 万桶/日（7 月以来首次），"
                 "卡塔尔能源的 LNG 船在严密监视下维持有限通行。",
        "alternative": "好望角绕行（+10-14 天）；沙特东西向管道（9/11 起停输）；"
                       "阿联酋富查伊拉路线（本轮周期内亦曾遭袭）",
        "data_source": "新华社/路透 2026-09-14 + Kpler + IMF PortWatch + straits.live",
        "updated": UPDATED_Z,
    })

    g = sec(d, "geopolitics", "ormuz")
    g.update({
        "status": "实际关闭 · 特许通行制",
        "detail": "伊朗实行「审批 + 付费」的通行制度，通行费据报道每船每次 100-200 万美元；"
                  "美方警告支付该费用可能触发制裁风险。布伦特原油前月期货约 106.93 美元。",
        "last_review": SNAPSHOT_DATE,
        "advisory_level": "极高（JMIC 维持 critical）",
    })

    # ---------- 曼德海峡 ----------
    s = sec(d, "security", "mandeb")
    s.update({
        "risk_level": "极高",
        "risk_score": 95,
        "status": "重大威胁（胡塞已控制丕林岛）",
        "status_icon": "🔴",
        "last_incident": "2026-09 胡塞武装先后控制红海摩卡港与曼德海峡内的丕林岛；"
                         "8 月 24 日一艘沙特籍油轮在延布以西被击中起火；"
                         "本周胡塞在红海袭击中致 6 人死亡，并再次袭击沙特吉赞炼油厂。",
        "data_source": "straits.live 2026-09-15 + global-energy-flow 2026-09 + UKMTO",
        "updated": UPDATED_Z,
    })
    t = sec(d, "traffic", "mandeb")
    t.update({
        "status": "高风险绕行",
        "congestion_level": "通行受安全形势抑制",
        "risk_score": 95,
        "notes": "【2026-09-15 更新】胡塞武装 9 月控制丕林岛后，曼德海峡的军事控制能力显著增强。"
                 "海事安全当局对南红海与曼德海峡的威胁等级维持「重大」评估，认为后续袭击仍可能发生。"
                 "MSC 已指示船长同时避开曼德海峡与霍尔木兹海峡。",
        "queue_icon": "🔴",
        "data_source": "straits.live + global-energy-flow + UKMTO 2026-09",
        "updated": UPDATED_Z,
    })

    # ---------- 苏伊士 ----------
    s = sec(d, "security", "suez")
    s.update({
        "risk_level": "中高",
        "risk_score": 62,
        "status": "选择性复航（安全形势仍脆弱）",
        "status_icon": "🟠",
        "data_source": "Zencargo 2026-09-08 + BIMCO + S&P Global + SCA",
        "updated": UPDATED_Z,
    })
    t = sec(d, "traffic", "suez")
    t.update({
        "status": "复苏中（仍显著低于危机前）",
        "daily_transit": "8 月通行 196 艘（同比 +36%）；平均船型由 3,800 TEU 升至 6,000 TEU",
        "congestion_level": "中等",
        "risk_score": 62,
        "queue_icon": "🟠",
        "notes": "【2026-09-15 更新】MDS Transmodal 数据显示 8 月通行 196 艘、同比 +36%，"
                 "运力 168 万 TEU、同比 +184%，8 月单月即有 9 艘 20,000 TEU 以上船舶通过——"
                 "数字在恢复，但船上运力结构变化才是主因。"
                 "BIMCO 指出 2026 年首周通行量仍比 2023 年同期低约 60%；"
                 "S&P Global 数据显示东—西向经运河份额为 18.7%（危机前约 80%）。"
                 "真正的制约不是运河本身（2026 年运河未出现物理性拥堵），"
                 "而是船东是否愿意穿越曼德海峡。埃及对大型船舶提供通行费折扣以留住运量。",
        "alternative": "好望角绕行（亚欧航线 +10-14 天）",
        "data_source": "Zencargo 2026-09-08 + MDS Transmodal + BIMCO + S&P Global",
        "updated": UPDATED_Z,
    })

    # ---------- 巴拿马 ----------
    s = sec(d, "security", "panama")
    s.update({
        "risk_level": "低（运营风险上升）",
        "risk_score": 55,
        "status": "干旱限流（非安全因素）",
        "status_icon": "🟠",
        "data_source": "Windward 2026-09 + Zencargo 2026-09-08 + ACP",
        "updated": UPDATED_Z,
    })
    t = sec(d, "traffic", "panama")
    t.update({
        "status": "限流（9/15 起 32 艘/日）",
        "daily_transit": "9 月 4 日起 34 艘/日（Neopanamax 9 + Panamax 25）；"
                         "9 月 15 日起降至 32 艘/日（Panamax 降至 23）。运力约 40 艘/日。",
        "wait_hours": "无预订船只等待时间延长（预订是唯一能保证过闸日期的方式）",
        "congestion_level": "中高（船位紧张）",
        "risk_score": 55,
        "queue_icon": "🟠",
        "notes": "【2026-09-15 更新】5-8 月降雨量比历史均值低约 34%，流域来水低 44%，"
                 "且限流发生在本应补水的雨季，令 2027 年 1-4 月旱季形势承压。"
                 "最大吃水已由 15.24 米分阶段下调至 14.94 米（7 月 24 日），"
                 "后续 14.63 米与 14.48 米分别推迟至 9 月 2 日与 10 月 1 日生效。"
                 "9 月 1 日 SK Gas 以 530 万美元拍得 G. SPIRIT 号的 Neopanamax 船位，为历史最高价。"
                 "新任管理局局长未排除若干旱持续，2027 年 2-3 月进一步降至 29 艘/日的可能。"
                 "LNG 通行量仍比干旱前低约 73%。",
        "alternative": "好望角；美西港口 + 陆运；苏伊士（受红海风险制约）",
        "data_source": "Windward 2026-09 + Zencargo 2026-09-08 + ACP 公告",
        "updated": UPDATED_Z,
    })

    # ---------- 好望角 ----------
    t = sec(d, "traffic", "cape")
    t.update({
        "status": "分流主通道（运量高）",
        "congestion_level": "中高",
        "risk_score": 40,
        "queue_icon": "🟢",
        "notes": "【2026-09-15 更新】霍尔木兹实际关闭、苏伊士仅选择性复航、巴拿马又限流，"
                 "好望角正同时承接三条通道的分流，成为默认泄压阀。"
                 "亚欧航程增加约 10-14 天，成本显著上升。"
                 "运河船位稀缺也反过来推高绕行需求。"
                 "本水道本身无安全威胁，风险主要来自高密度的交通与天气。",
        "data_source": "Windward 2026-09 + Zencargo 2026-09-08",
        "updated": UPDATED_Z,
    })

    # ---------- 马六甲 ----------
    t = sec(d, "traffic", "malacca")
    t.update({
        "congestion_level": "偏高（分流导致密度上升）",
        "risk_score": 45,
        "notes": "【2026-09-15 更新】承担全球约 25-30% 海运贸易量。"
                 "受霍尔木兹货物改道影响，马六甲与新加坡海峡一带交通密度进一步上升，"
                 "新加坡与柔佛附近出现密集锚泊，通行余量偏紧。该水道目前无直接安全威胁。",
        "data_source": "global-energy-flow 2026-09 + AIS 观测",
        "updated": UPDATED_Z,
    })

    # ---------- 数据质量：修正「谎报新鲜度」 ----------
    dq = d.setdefault("data_quality", {})
    dq["overall_freshness"] = "medium"
    dq["last_major_update"] = SNAPSHOT_DATE
    dq["traffic_update_date"] = SNAPSHOT_DATE
    dq["note"] = ("天气为 Open-Meteo 实时抓取；地缘政治、通航量、安全事件为人工核实快照，"
                  "快照日期见 data_date，不会随抓取自动更新。")
    inner = dq.setdefault("data_quality", {})
    for wid in ("ormuz", "mandeb", "suez", "panama"):
        inner[wid] = {
            "quality": "high",
            "latest_date": SNAPSHOT_DATE,
            "source": "2026-09-15 人工核实（见 scripts/apply_snapshot_2026_09.py 头部来源清单）",
        }

    # ---------- 数据来源 ----------
    d["data_sources"] = {
        "weather": "Open-Meteo API v2 (https://open-meteo.com) - 真实实时海象",
        "traffic": "Kpler + IMF PortWatch + MDS Transmodal + ACP 公告（2026-09 核实）",
        "security": "UKMTO + straits.live + Maritime News + Windward + 新华社/路透（2026-09 核实）",
        "geopolitics": "中新社 2026-09-08 + straits.live 2026-09-15 + BIMCO + S&P Global",
        "vessels": "AIS 观测（注：部分船舶为安全原因关闭 AIS，计数存在低估）",
    }
    d["disclaimer"] = ("本页天气为实时数据；地缘政治、通航量与安全事件为人工核实快照，"
                       "快照日期为 " + SNAPSHOT_DATE + "，可能滞后于最新局势。"
                       "数据仅供参考，不构成航行建议。用于实际决策前请核对官方最新通告"
                       "（UKMTO、JMIC、各运河管理局）。")

    return d


def main():
    for path in TARGETS:
        if not os.path.exists(path):
            print("跳过（不存在）:", path)
            continue
        with open(path, encoding="utf-8") as f:
            d = json.load(f)
        before = d.get("data_date")
        update(d)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(d, f, ensure_ascii=False, indent=2)
        print(f"已更新 {os.path.relpath(path, SCRIPT_DIR)}: data_date {before} -> {d['data_date']}")


if __name__ == "__main__":
    main()
