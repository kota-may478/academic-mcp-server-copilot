"""Topic assignment for ground-effect (IGE) multicopter / UAV power and energy surveys."""
from __future__ import annotations

SEED_SUMMARIES = {
    "DOI:10.1007/s11370-020-00344-5": (
        "ロータクラフトUAVの地面効果に関するレビュー。"
        "モデリング・制御の観点から小規模マルチロータのIGE研究を整理した中核文献。"
    ),
    "DOI:10.3390/drones9030195": (
        "クロスメディア機体のロータ近水面効果レビュー。"
        "地面効果との対比・連続性を論じる補助シード。"
    ),
    "DOI:10.1108/EB033078": (
        "ヘリコプタロータ近傍の誘導流に関する古典的レビュー。"
        "IGE理論の歴史的基盤文献。"
    ),
    "DOI:10.3389/fpace.2022.975158": (
        "低レイノルズ数翼の地面効果実験レビュー。"
        "前進・並進飛行GEの翼側面の背景として参照。"
    ),
    "DOI:10.1016/J.PAEROSCI.2005.03.002": (
        "STOVL機のOGE推進干渉レビュー。"
        "前進飛行・地面効果境界領域の航空力学背景。"
    ),
}

TOPIC_SUMMARIES = {
    "T1": "ホバリング時の地面効果（IGE）における推力・揚力・誘導電力の理論・実験・数値解析。",
    "T2": "ホバリング時の地面効果における消費電力・エネルギー・効率・誘導電力の定量的解析。",
    "T3": "前進飛行・並進飛行と地面効果の空力・推力・揚力連成解析。",
    "T4": "前進飛行・並進飛行と地面効果における消費電力・エネルギー・効率解析。",
    "T5": "低高度飛行・地上近接飛行（proximity / nap-of-earth）とエネルギー・航続。",
    "T6": "地面効果を考慮した制御・経路計画・飛行モード最適化とエネルギー削減。",
}

RESEARCH_GAPS = [
    (
        "前進飛行＋GE＋消費電力",
        "推力・揚力次元のGE研究は多いが、前進飛行時に電力・エネルギー次元でGEを解析した体系文献が限定的。",
        [],
    ),
    (
        "ホバリングGE電力の実飛行検証",
        "風洞・単ロータ実験はあるが、実機マルチロータでの消費電力とGEの対応の系統データが不足。",
        [],
    ),
    (
        "推力係数と電力係数の対応",
        "推力削減と電力削減の定量対応（誘導電力・プロファイル電力の分離）の標準手順が未統一。",
        [],
    ),
    (
        "前進速度と地上高の二変数マップ",
        "巡航高度・前進速度・地上高を同時に変化させた電力マップの実験・モデル化が少ない。",
        [],
    ),
    (
        "制御・経路へのGE電力モデル統合",
        "GEを考慮したエネルギー最適経路・飛行モード切替の実機検証が限定的。",
        [],
    ),
    (
        "マルチロータ固有の下洗流干渉",
        "複数ロータ間の下洗流と地面反射の連成が電力に与える影響の分離手法が不足。",
        [],
    ),
]

TOPICS = {
    "T1": {
        "name": "ホバリングGE・推力・誘導電力",
        "name_en": "Hovering ground effect — thrust and induced power",
        "subtopics": {
            "T1a": "理論・半経験モデル（Cheeseman & Bennett 等）",
            "T1b": "風洞・単ロータ・台架実験",
            "T1c": "CFD・数値流体力学",
        },
    },
    "T2": {
        "name": "ホバリングGE・消費電力・効率",
        "name_en": "Hovering ground effect — power and energy",
        "subtopics": {
            "T2a": "実験・飛行試験による電力計測",
            "T2b": "シミュレーション・モデルベース電力推定",
            "T2c": "効率・figure of merit・誘導電力の定量化",
        },
    },
    "T3": {
        "name": "前進飛行＋GE・空力・推力",
        "name_en": "Forward flight ground effect — aerodynamics and thrust",
        "subtopics": {
            "T3a": "前進速度・前進比を含む空力解析",
            "T3b": "並進飛行・巡航時のGE",
            "T3c": "過渡・離着陸遷移域",
        },
    },
    "T4": {
        "name": "前進飛行＋GE・消費電力",
        "name_en": "Forward flight ground effect — power and energy",
        "subtopics": {
            "T4a": "前進飛行時の電力・エネルギー実験",
            "T4b": "前進＋GEの電力モデル・シミュレーション",
            "T4c": "ホバリングと前進の電力比較",
        },
    },
    "T5": {
        "name": "低高度・地上近接飛行エネルギー",
        "name_en": "Low-altitude / proximity flight energy",
        "subtopics": {
            "T5a": "nap-of-earth・地上追従飛行",
            "T5b": "建設現場・屋内低高度運用",
            "T5c": "航続・バッテリー消費への影響",
        },
    },
    "T6": {
        "name": "GE考慮の制御・経路・最適化",
        "name_en": "Control, planning, and optimization with ground effect",
        "subtopics": {
            "T6a": "エネルギー最適経路計画",
            "T6b": "飛行モード・高度制御",
            "T6c": "タスク指向のGE活用（省電力ホバリング等）",
        },
    },
}

_GE_CORE = (
    "ground effect", "in ground effect", "ige", "out of ground effect", "oge",
    "proximity to ground", "near ground", "close to ground", "ground clearance",
    "cushion effect", "ground plane", "wall effect",
)
_POWER_TERMS = (
    "power consumption", "energy consumption", "electrical power", "power required",
    "power saving", "power reduction", "energy efficiency", "specific power",
    "induced power", "figure of merit", "battery", "energy model", "power model",
    "efficiency", "watt", "wh/kg",
)
_THRUST_TERMS = (
    "thrust", "lift", "thrust coefficient", "lift coefficient", "induced velocity",
    "momentum theory", "blade element",
)
_FORWARD_TERMS = (
    "forward flight", "forward speed", "translational", "cruise", "advance ratio",
    "forward velocity", "horizontal flight", "translational flight",
)
_UAV_TERMS = (
    "uav", "drone", "quadcopter", "multicopter", "multi-rotor", "multirotor",
    "unmanned aerial", "rotorcraft", "hexacopter", "octocopter",
)
_CONTROL_TERMS = (
    "trajectory", "path planning", "energy optimal", "minimum power",
    "flight control", "guidance", "autonomous",
)


def _blob(entry: dict) -> str:
    title = (entry.get("title") or "").lower()
    kws = entry.get("keywords") or {}
    parts = [title, (entry.get("abstract") or "").lower()]
    for ax in "PAOM":
        parts.extend(str(k).lower() for k in (kws.get(ax) or []))
    return " ".join(parts)


def assign_subtopics(entry: dict) -> list[tuple[str, str]]:
    blob = _blob(entry)
    out: list[tuple[str, str]] = []

    def hit(*words: str) -> bool:
        return any(w in blob for w in words)

    if not hit(*_GE_CORE):
        return out

    has_power = hit(*_POWER_TERMS)
    has_thrust = hit(*_THRUST_TERMS)
    has_forward = hit(*_FORWARD_TERMS)
    has_uav = hit(*_UAV_TERMS)

    if not has_uav and not hit("rotor", "helicopter", "propeller", "vtol"):
        if not has_power and not has_thrust:
            return out

    if has_forward:
        if has_power:
            out.append(
                (
                    "T4",
                    "T4a"
                    if hit("experiment", "flight test", "measurement", "wind tunnel")
                    else "T4b"
                    if hit("simulation", "model", "cfd", "numerical")
                    else "T4c",
                )
            )
        if has_thrust or hit("aerodynamic", "aerodynamics", "lift", "thrust"):
            out.append(
                (
                    "T3",
                    "T3a"
                    if hit("forward speed", "advance ratio", "forward velocity")
                    else "T3b"
                    if hit("cruise", "translational")
                    else "T3c",
                )
            )

    if not has_forward or hit("hover", "hovering"):
        if has_power:
            out.append(
                (
                    "T2",
                    "T2a"
                    if hit("experiment", "flight test", "measurement")
                    else "T2b"
                    if hit("simulation", "model", "estimation")
                    else "T2c",
                )
            )
        if has_thrust or not has_power:
            out.append(
                (
                    "T1",
                    "T1a"
                    if hit("theory", "momentum", "analytical", "semi-empirical")
                    else "T1b"
                    if hit("experiment", "wind tunnel", "test bench", "measurement")
                    else "T1c",
                )
            )

    if hit("nap-of-earth", "low altitude", "proximity flight", "near-ground flight"):
        out.append(
            (
                "T5",
                "T5a"
                if hit("nap-of-earth", "terrain following")
                else "T5b"
                if hit("construction", "indoor", "urban")
                else "T5c",
            )
        )

    if hit(*_CONTROL_TERMS) and (has_power or hit("energy", "power")):
        out.append(
            (
                "T6",
                "T6a"
                if hit("path planning", "trajectory", "route")
                else "T6b"
                if hit("control", "altitude", "guidance")
                else "T6c",
            )
        )

    if not out:
        out.append(("T1", "T1a"))

    return out
