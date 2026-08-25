"""Topic assignment for wireless power transfer (multi-modality) for robots / unmanned vehicles."""
from __future__ import annotations

SEED_SUMMARIES: dict[str, str] = {}

TOPIC_SUMMARIES: dict[str, str] = {
    "T1": "誘導・磁界共振（近接界）WPTはロボット向け給電の本流であり、コイル設計・補償・ミスアライメント耐性が中核課題である。",
    "T2": "マイクロ波・RF遠方界伝送は長距離給電に適するが、効率・安全・ビーム制御が制約となる。",
    "T3": "レーザー／光無線給電は高指向性の長距離伝送を可能にするが、天候・視線・安全規格が課題である。",
    "T4": "電界結合（CPT）は軽量電極で近接給電できるが、ギャップ・位置ずれ感度が高い。",
    "T5": "空中ロボット（UAV/drone）向けWPTはホバリング・飛行中・ドック充電の運用形態と機体制約が設計を支配する。",
    "T6": "水中・海上無人機（AUV/UUV/ROV/USV）向けWPTは媒質損失・シール・ドッキングが固有課題である。",
    "T7": "地上移動ロボット・AGV向けWPTはステーション充電から動的給電まで、産業運用との統合が焦点である。",
    "T8": "動的・移動中給電（ミスアライメント・軌道追従・制御）は最終的な磁界共振×移動ロボット研究の接続点である。",
}

RESEARCH_GAPS: list[tuple[str, str, list[str]]] = [
    ("方式横断のロボットWPTベンチマーク", "IPT/共振・マイクロ波・レーザー・CPTを同一指標で比較する枠組みが不足。", []),
    ("動的磁界共振の実機検証", "移動・飛行中の磁界共振WPTの統一評価（速度・ギャップ・効率）が限定的。", []),
    ("水中媒質下の近接界WPT", "海水・淡水での結合・損失モデルと実証が地上・空中に比べ少ない。", []),
    ("プラットフォーム横断の運用設計", "UAV/AUV/AGVで共通化できる充電スケジューリング・安全基準が未整備。", []),
]

TOPICS: dict[str, dict] = {
    "T1": {
        "name": "誘導・磁界共振（近接界）",
        "name_en": "Inductive / magnetic resonant (near-field)",
        "subtopics": {
            "T1a": "IPT・コイル結合",
            "T1b": "磁界共振・共鳴結合",
            "T1c": "補償・パワーエレクトロニクス",
        },
    },
    "T2": {
        "name": "マイクロ波・RF遠方界",
        "name_en": "Microwave / RF far-field",
        "subtopics": {
            "T2a": "マイクロ波電力伝送（MPT）",
            "T2b": "レクテナ・ビームフォーミング",
            "T2c": "SWIPT・RFハーベスティング",
        },
    },
    "T3": {
        "name": "レーザー・光無線給電",
        "name_en": "Laser / optical wireless power",
        "subtopics": {
            "T3a": "レーザーパワービーミング",
            "T3b": "光受信・光電変換",
            "T3c": "視線・安全・天候制約",
        },
    },
    "T4": {
        "name": "電界結合（CPT）",
        "name_en": "Capacitive power transfer",
        "subtopics": {
            "T4a": "電極・結合設計",
            "T4b": "高周波駆動・補償",
            "T4c": "ギャップ・位置ずれ",
        },
    },
    "T5": {
        "name": "空中ロボット（UAV）",
        "name_en": "Aerial robots (UAV/drone)",
        "subtopics": {
            "T5a": "ホバリング・飛行中給電",
            "T5b": "着陸・ドック充電",
            "T5c": "スウォーム・FANET運用",
        },
    },
    "T6": {
        "name": "水中・海上無人機",
        "name_en": "Underwater / surface vehicles",
        "subtopics": {
            "T6a": "AUV/UUV給電",
            "T6b": "ROV・ドッキング",
            "T6c": "USV・海上充電",
        },
    },
    "T7": {
        "name": "地上移動ロボット・AGV",
        "name_en": "Ground mobile robots / AGV",
        "subtopics": {
            "T7a": "モバイルロボット充電",
            "T7b": "AGV・産業搬送",
            "T7c": "ステーション・インフラ統合",
        },
    },
    "T8": {
        "name": "動的・移動中給電",
        "name_en": "Dynamic / in-motion charging",
        "subtopics": {
            "T8a": "動的ミスアライメント",
            "T8b": "軌道・位置制御との統合",
            "T8c": "走行中・航行中給電",
        },
    },
}

_IPT = ("inductive", "ipt", "magnetic resonance", "magnetic resonant", "resonant coupling", "near-field", "coil")
_MW = ("microwave", "mpt", "rectenna", "rf energy", "swipt", "far-field", "beamforming")
_LASER = ("laser", "optical wireless power", "power beaming", "photovoltaic receiver")
_CPT = ("capacitive", "cpt", "electric field coupling", "electric-field")
_UAV = ("uav", "drone", "quadrotor", "multirotor", "unmanned aerial", "aerial vehicle", "fanet")
_UW = ("auv", "uuv", "rov", "underwater", "unmanned underwater", "usv", "unmanned surface")
_GROUND = ("mobile robot", "agv", "ground robot", "wheeled robot", "legged robot")
_DYN = ("dynamic wireless", "in-motion", "in motion", "while moving", "moving receiver", "misalignment")


def _blob(entry: dict) -> str:
    title = (entry.get("title") or "").lower()
    abstract = (entry.get("abstract") or "").lower()[:800]
    kws = entry.get("keywords") or {}
    parts = [title, abstract]
    for ax in "PAOM":
        parts.extend(str(k).lower() for k in (kws.get(ax) or []))
    return " ".join(parts)


def assign_subtopics(entry: dict) -> list[tuple[str, str]]:
    blob = _blob(entry)
    out: list[tuple[str, str]] = []

    def hit(*words: str) -> bool:
        return any(w in blob for w in words)

    if hit(*_IPT):
        if hit("magnetic resonance", "magnetic resonant", "resonant coupling", "mcr-wpt"):
            out.append(("T1", "T1b"))
        elif hit("compensation", "inverter", "rectifier", "converter"):
            out.append(("T1", "T1c"))
        else:
            out.append(("T1", "T1a"))

    if hit(*_MW):
        if hit("rectenna", "beamforming", "beam forming"):
            out.append(("T2", "T2b"))
        elif hit("swipt", "harvest"):
            out.append(("T2", "T2c"))
        else:
            out.append(("T2", "T2a"))

    if hit(*_LASER):
        if hit("safety", "eye", "weather", "line of sight", "los"):
            out.append(("T3", "T3c"))
        elif hit("photovoltaic", "receiver", "pv "):
            out.append(("T3", "T3b"))
        else:
            out.append(("T3", "T3a"))

    if hit(*_CPT):
        if hit("gap", "misalignment", "alignment"):
            out.append(("T4", "T4c"))
        elif hit("compensation", "inverter", "high frequency", "high-frequency"):
            out.append(("T4", "T4b"))
        else:
            out.append(("T4", "T4a"))

    if hit(*_UAV):
        if hit("hover", "in-flight", "in flight", "while flying", "flight"):
            out.append(("T5", "T5a"))
        elif hit("swarm", "fanet"):
            out.append(("T5", "T5c"))
        else:
            out.append(("T5", "T5b"))

    if hit(*_UW):
        if hit("dock", "docking"):
            out.append(("T6", "T6b"))
        elif hit("usv", "surface"):
            out.append(("T6", "T6c"))
        else:
            out.append(("T6", "T6a"))

    if hit(*_GROUND) or (hit("robot") and not hit(*_UAV) and not hit(*_UW)):
        if hit("agv", "industrial", "warehouse"):
            out.append(("T7", "T7b"))
        elif hit("station", "infrastructure", "pad"):
            out.append(("T7", "T7c"))
        else:
            out.append(("T7", "T7a"))

    if hit(*_DYN):
        if hit("trajectory", "path", "position control", "tracking"):
            out.append(("T8", "T8b"))
        elif hit("driving", "cruising", "navigation", "underway"):
            out.append(("T8", "T8c"))
        else:
            out.append(("T8", "T8a"))

    if not out and hit("wireless power", "wireless charging", "wpt"):
        out.append(("T1", "T1a"))

    return list(dict.fromkeys(out))
