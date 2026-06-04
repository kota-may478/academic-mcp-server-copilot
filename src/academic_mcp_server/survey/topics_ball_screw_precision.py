"""Topic assignment for high-precision ball screw stage control surveys."""
from __future__ import annotations

SEED_SUMMARIES = {
    "DOI:10.1016/j.cirp.2011.05.010": (
        "工作機械送り系（フィードドライブ）のモデリング・制御・診断を包括レビュー。"
        "ボールねじ駆動の高精度制御の背景文献として中核的。"
    ),
    "DOI:10.1016/j.ijmachtools.2023.104021": (
        "ボールねじ送り系の静・動特性解析とモデリングを体系的に整理した最新レビュー。"
    ),
    "DOI:10.1007/s00170-020-05041-2": (
        "送り系の振動解析と制御に関するサーベイ。ボールねじステージの高精度制御文脈に直結。"
    ),
}

TOPIC_SUMMARIES = {
    "T1": "ボールねじ駆動系の多自由度・軸方向/ねじり/横振動モデルと剛性・バックラッシュ。",
    "T2": "高精度位置決め・追従・輪郭誤差・サブミクロン/nm級精度の達成手法。",
    "T3": "振動抑制・チャタ・共鳴・モード制御・能動/受動ダンピング。",
    "T4": "外乱オブザーバ・ADRC・熱誤差・摩擦・プリロード変動の補償。",
    "T5": "ILC・MPC・ロバスト/適応/スライディング等の先進制御設計。",
    "T6": "工作機械送り系・ツイン駆動ガントリ・半導体ステージ等の応用実装。",
}

RESEARCH_GAPS = [
    ("統一ベンチマーク不足", "ボールねじ高精度制御の標準評価条件・指標が分散。", []),
    ("熱-構造-制御一体設計", "熱変位と制御器の協調設計の実機検証が限定的。", []),
    ("デジタルツイン・データ駆動", "デジタルツイン統合による精度維持の体系化が未整備。", []),
    ("長寿命・摩耗下の精度維持", "プリロード劣化・摩耗を考慮した制御設計が不足。", []),
]

TOPICS = {
    "T1": {
        "name": "ボールねじ駆動系モデリング",
        "name_en": "Ball screw drive modeling",
        "subtopics": {
            "T1a": "軸方向・ねじり・横振動結合",
            "T1b": "バックラッシュ・プリロード・摩擦",
            "T1c": "剛性・接触・界面モデル",
        },
    },
    "T2": {
        "name": "高精度位置決め・追従",
        "name_en": "High-precision positioning and tracking",
        "subtopics": {
            "T2a": "ナノ/サブミクロン位置決め",
            "T2b": "輪郭・軌道追従誤差",
            "T2c": "高速・高帯域追従",
        },
    },
    "T3": {
        "name": "振動抑制・チャタ",
        "name_en": "Vibration and chatter suppression",
        "subtopics": {
            "T3a": "共鳴・モード制御",
            "T3b": "能動ダンピング・入力整形",
            "T3c": "チャタ検出・抑制",
        },
    },
    "T4": {
        "name": "外乱・熱・摩擦補償",
        "name_en": "Disturbance / thermal / friction compensation",
        "subtopics": {
            "T4a": "外乱オブザーバ・ADRC",
            "T4b": "熱誤差補償",
            "T4c": "摩擦・ロストモーション補償",
        },
    },
    "T5": {
        "name": "先進制御設計",
        "name_en": "Advanced control design",
        "subtopics": {
            "T5a": "ILC・反復学習",
            "T5b": "MPC・ロバスト制御",
            "T5c": "適応・スライディング・ファジー",
        },
    },
    "T6": {
        "name": "工作機械・産業応用",
        "name_en": "Machine tool and industrial applications",
        "subtopics": {
            "T6a": "送り系・CNC",
            "T6b": "ツイン駆動・ガントリ",
            "T6c": "半導体・精密ステージ",
        },
    },
}

_BS_TERMS = (
    "ball screw", "ball-screw", "ballscrew", "lead screw", "feed drive", "feed-drive",
)
_PREC_TERMS = (
    "high precision", "high-precision", "precision control", "positioning accuracy",
    "ultra-precision", "nanometer", "sub-micron", "tracking error", "contour error",
)
_CTRL_TERMS = (
    "control", "servo", "compensation", "observer", "pid", "adrc", "ilc", "mpc",
    "sliding mode", "pole placement", "vibration suppression",
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

    if not hit(*_BS_TERMS):
        return out

    if hit("model", "dynamic", "stiffness", "backlash", "preload", "coupling", "hybrid model"):
        out.append(("T1", "T1a" if hit("torsional", "lateral", "axial", "coupled") else "T1b" if hit("backlash", "preload", "friction") else "T1c"))

    if hit(*_PREC_TERMS) or hit("tracking", "positioning", "contour", "accuracy", "bandwidth"):
        out.append(("T2", "T2a" if hit("nano", "sub-micron", "ultra-precision") else "T2b" if hit("contour", "path") else "T2c"))

    if hit("vibration", "chatter", "resonance", "damping", "modal"):
        out.append(("T3", "T3c" if "chatter" in blob else "T3b" if hit("active", "shaping", "input shaping") else "T3a"))

    if hit("thermal", "friction", "disturbance", "observer", "adrc", "lost motion"):
        out.append(("T4", "T4b" if "thermal" in blob else "T4c" if hit("friction", "lost motion") else "T4a"))

    if hit("ilc", "iterative learning", "mpc", "model predictive", "sliding", "adaptive", "robust", "fuzzy", "h-infinity", "pole placement"):
        out.append(("T5", "T5a" if hit("ilc", "iterative learning") else "T5b" if hit("mpc", "robust", "h-infinity") else "T5c"))

    if hit("machine tool", "cnc", "gantry", "dual-drive", "semiconductor", "wafer", "milling", "turning"):
        out.append(("T6", "T6b" if hit("gantry", "dual") else "T6c" if hit("semiconductor", "wafer") else "T6a"))

    if not out and hit(*_CTRL_TERMS):
        out.append(("T2", "T2c"))

    return out or [("T6", "T6a")]
