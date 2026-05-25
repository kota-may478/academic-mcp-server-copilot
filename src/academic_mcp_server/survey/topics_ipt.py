from __future__ import annotations

SEED_SUMMARIES = {
    "DOI:10.1109/COMST.2014.2368999": "RFエネルギーハーベスティングを含む無線ネットワークの総合サーベイ。SWIPT・レクテナ・ビームフォーミングなど、飛行IPTの隣接技術として参照価値が高い。",
    "DOI:10.3390/drones6060147": "UAVの機体・推進・制御・運用を横断整理。航続時間制約と地上充電運用の背景として空中給電の動機を説明する。",
    "DOI:10.3390/aerospace8120363": "UAVの通信・センシング・自律化の将来方向を整理。FANET・ミッション設計と給電インフラ統合の観点でIPT文脈に接続する。",
}

TOPIC_SUMMARIES = {
    "T1": "飛行中IPTは航続時間とミッション連続性の中核。",
    "T2": "コイル設計はミスアライメント耐性が鍵。",
    "T3": "パワーエレクトロニクスは軽量高効率が課題。",
    "T4": "UAV/FANETでは給電と通信の同時設計が必要。",
    "T5": "RFハーベスティングは隣接領域としてSWIPT等を提供。",
}

RESEARCH_GAPS = [
    ("飛行中IPTベンチマーク", "統一評価指標が不足。", []),
    ("FANETと充電スケジュール", "共同最適化が限定的。", []),
]

TOPICS = {
    "T1": {"name": "飛行中・ホバリングIPT", "name_en": "In-flight / hovering IPT", "subtopics": {"T1a": "ホバリング給電", "T1b": "飛行軌道給電", "T1c": "離着陸区間給電"}},
    "T2": {"name": "コイル・磁気結合設計", "name_en": "Coil and coupling", "subtopics": {"T2a": "ミスアライメント耐性", "T2b": "3D・多コイル", "T2c": "結合・効率モデル"}},
    "T3": {"name": "パワーエレクトロニクス", "name_en": "Power electronics", "subtopics": {"T3a": "整流AC-DC", "T3b": "補償・共鳴", "T3c": "軽量インバータ"}},
    "T4": {"name": "UAV・FANET", "name_en": "UAV/FANET", "subtopics": {"T4a": "通信統合", "T4b": "スウォーム", "T4c": "ミッション設計"}},
    "T5": {"name": "RFハーベスティング", "name_en": "RF harvesting", "subtopics": {"T5a": "レクテナ", "T5b": "SWIPT", "T5c": "ビームフォーミング"}},
}

_UAV_TERMS = ("uav", "drone", "fanet", "unmanned aerial", "swarm")


def _blob(entry: dict) -> str:
    title = (entry.get("title") or "").lower()
    kws = entry.get("keywords") or {}
    parts = [title]
    for ax in "PAOM":
        parts.extend(str(k) for k in (kws.get(ax) or []))
    return " ".join(parts).lower()


def _a_axis_blob(entry: dict) -> str:
    kws = entry.get("keywords") or {}
    return " ".join(str(k) for k in (kws.get("A") or [])).lower()


def _title_blob(entry: dict) -> str:
    return (entry.get("title") or "").lower()


def _uav_context(entry: dict) -> bool:
    tl = _title_blob(entry)
    ab = _a_axis_blob(entry)
    return any(t in tl for t in _UAV_TERMS) or any(t in ab for t in _UAV_TERMS)


def assign_subtopics(entry: dict) -> list[tuple[str, str]]:
    blob = _blob(entry)
    title = _title_blob(entry)
    uav_ctx = _uav_context(entry)
    out: list[tuple[str, str]] = []

    def hit(*words: str) -> bool:
        return any(w in blob for w in words)

    if hit("in-flight", "hover", "aerial charging", "uav charging", "drone charging"):
        out.append(("T1", "T1a" if "hover" in blob else "T1b" if hit("trajectory", "flight") else "T1c"))
    if hit("coil", "coupling", "misalignment", "resonant", "magnetic"):
        out.append(("T2", "T2a" if "misalignment" in blob else "T2b" if hit("3-d", "array") else "T2c"))
    if hit("rectifier", "inverter", "converter", "compensation"):
        out.append(("T3", "T3a" if "rectifier" in blob else "T3b" if "compensation" in blob else "T3c"))
    if uav_ctx:
        ctx = title + " " + _a_axis_blob(entry)
        if any(t in ctx for t in ("uav", "drone", "fanet", "swarm", "network")):
            out.append(("T4", "T4a" if hit("fanet", "network") else "T4b" if "swarm" in ctx else "T4c"))
    if hit("rf energy", "harvesting", "rectenna", "swipt", "wireless power"):
        out.append(("T5", "T5a" if "rectenna" in blob else "T5b" if "swipt" in blob else "T5c"))
    if not out and hit("wpt", "ipt", "inductive"):
        out.append(("T1", "T1c"))
    return list(dict.fromkeys(out))
