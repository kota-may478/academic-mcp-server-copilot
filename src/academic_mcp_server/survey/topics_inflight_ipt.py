"""Topic assignment for in-flight inductive power transfer (UAV WPT) surveys."""
from __future__ import annotations

SEED_SUMMARIES = {
    "DOI:10.1109/ACCESS.2021.3077041": (
        "UAV向け無線充電の基礎・応用・充電方式・規格を横断整理したレビュー。"
        "飛行中IPT/WPTの背景技術として中核的。"
    ),
    "DOI:10.1109/JESTIE.2022.3213138": (
        "UAV向け近接界WPTの体系レビュー。コイル設計、補償、制御、事例比較を含む。"
    ),
    "DOI:10.1109/ACCESS.2023.3332470": (
        "UAV WPTの結合機構・補償トポロジ・制御・課題を俯瞰する最新レビュー。"
    ),
}

TOPIC_SUMMARIES = {
    "T1": "飛行中・ホバリング中のinductive給電は航続時間延伸の中核技術。",
    "T2": "コイル・磁気結合設計はミスアライメントと効率のトレードオフが鍵。",
    "T3": "補償ネットワークとパワーエレクトロニクスは軽量高効率化が課題。",
    "T4": "UAV/FANET文脈では給電スケジュールと通信・位置制御の統合が必要。",
    "T5": "磁気共鳴・近接界IPTの理論モデルと効率解析が設計の基盤。",
    "T6": "RF/SWIPT等の遠方界方式は飛行IPTの隣接・比較技術として位置づく。",
}

RESEARCH_GAPS = [
    ("飛行中IPT標準ベンチマーク", "ミスアライメント・速度・高度を含む統一評価指標が不足。", []),
    ("FANET協調充電", "スウォーム単位の充電スケジューリング研究が限定的。", []),
    ("軽量化と効率", "機体搭載レクテナ/コイルの重量制約下での系統最適化。", []),
]

TOPICS = {
    "T1": {
        "name": "飛行中・ホバリングIPT",
        "name_en": "In-flight / hovering IPT",
        "subtopics": {
            "T1a": "ホバリング給電",
            "T1b": "飛行軌道給電",
            "T1c": "離着陸区間給電",
            "T1d": "動的ミスアライメント",
        },
    },
    "T2": {
        "name": "コイル・磁気結合",
        "name_en": "Coil and magnetic coupling",
        "subtopics": {
            "T2a": "ミスアライメント耐性",
            "T2b": "3D・多コイルアレイ",
            "T2c": "結合係数・効率モデル",
        },
    },
    "T3": {
        "name": "補償・パワーエレクトロニクス",
        "name_en": "Compensation and power electronics",
        "subtopics": {
            "T3a": "SS/S/SP/PP補償",
            "T3b": "整流・AC-DC",
            "T3c": "インバータ・高周波駆動",
        },
    },
    "T4": {
        "name": "UAV・FANET・運用",
        "name_en": "UAV/FANET operations",
        "subtopics": {
            "T4a": "充電スケジュール",
            "T4b": "スウォーム協調",
            "T4c": "ミッション・航続",
        },
    },
    "T5": {
        "name": "磁気共鳴・近接界理論",
        "name_en": "Magnetic resonance / near-field theory",
        "subtopics": {
            "T5a": "共鳴周波数設計",
            "T5b": "磁束解析",
            "T5c": "効率最適化",
        },
    },
    "T6": {
        "name": "RF/SWIPT（隣接）",
        "name_en": "RF / SWIPT (adjacent)",
        "subtopics": {
            "T6a": "レクテナ",
            "T6b": "SWIPT",
            "T6c": "ビームフォーミング",
        },
    },
}

_IPT_TERMS = (
    "inductive", "ipt", "wpt", "wireless power", "magnetic coupling",
    "magnetic resonance", "near-field", "coil", "misalignment",
)
_UAV_TERMS = ("uav", "drone", "fanet", "unmanned aerial", "swarm", "aerial vehicle")
_RF_TERMS = ("rf energy", "rectenna", "swipt", "microwave power", "far-field")


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

    if hit("in-flight", "in flight", "hover", "hovering", "aerial charging", "while flying", "during flight"):
        out.append(("T1", "T1b" if hit("trajectory", "flight path", "cruise") else "T1a" if "hover" in blob else "T1c"))
    elif hit("misalignment", "dynamic", "moving") and hit(*_IPT_TERMS):
        out.append(("T1", "T1d"))

    if hit("coil", "coupling", "misalignment", "magnetic field", "receiver coil", "transmitter coil"):
        out.append(("T2", "T2a" if "misalignment" in blob else "T2b" if hit("array", "3-d", "3d") else "T2c"))

    if hit("compensation", "ss ", " s ", "sp ", "pp ", "rectifier", "inverter", "converter", "resonant"):
        out.append(("T3", "T3a" if "compensation" in blob or "resonant" in blob else "T3b" if "rectifier" in blob else "T3c"))

    if hit(*_UAV_TERMS):
        out.append(("T4", "T4a" if hit("schedule", "charging station") else "T4b" if "swarm" in blob else "T4c"))

    if hit("magnetic resonance", "resonance frequency", "mutual inductance", "flux"):
        out.append(("T5", "T5a" if "frequency" in blob else "T5b" if "flux" in blob else "T5c"))

    if hit(*_RF_TERMS):
        out.append(("T6", "T6a" if "rectenna" in blob else "T6b" if "swipt" in blob else "T6c"))

    if not out and hit(*_IPT_TERMS):
        out.append(("T1", "T1c"))
    if not out and hit(*_UAV_TERMS) and hit("wireless", "charging", "power"):
        out.append(("T4", "T4c"))

    return list(dict.fromkeys(out))
