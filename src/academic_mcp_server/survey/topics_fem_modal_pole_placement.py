"""Topic assignment for FEM modal analysis + reduced-order model + selective pole placement surveys."""
from __future__ import annotations

SEED_SUMMARIES: dict[str, str] = {
    "DOI:10.1007/978-94-015-8508-8": (
        "構造動力学における有限要素モデル更新の古典書。"
        "FEMモーダルモデルと実測の整合・次数削減の基盤文献。"
    ),
    "DOI:10.1016/J.YMSSP.2010.10.012": (
        "FEMモデル更新の感度法チュートリアル。"
        "モーダルパラメータと物理パラメータの同定・更新手順を整理。"
    ),
    "DOI:10.1023/A:1004398914135": (
        "能動構造の振動制御入門（Preumont）。"
        "モーダルモデル・状態空間・極配置を含む柔構造制御の総合テキスト。"
    ),
}

TOPIC_SUMMARIES = {
    "T1": "FEM・コンポーネントモード合成（CMS）・実験モード解析に基づく構造モーダルモデル構築。",
    "T2": "モーダル打ち切り・モデル次数削減・低次／支配モードを用いたROM構築。",
    "T3": "極配置・固有値割当・状態フィードバック設計（連続・離散系）。",
    "T4": "限定・選択的極配置、独立モーダル空間制御、スピルオーバー抑制。",
    "T5": "柔構造・ロボット・工作機械等へのモーダルベース制御の応用。",
    "T6": "FEMモデル更新・検証・実機との整合（モデル信頼性）。",
}

RESEARCH_GAPS = [
    (
        "低次ROM極のみを対象とする極配置の設計指針",
        "打ち切り次数と配置可能極の対応関係を明示した標準手順が不足。",
        [],
    ),
    (
        "FEMモーダルモデルからの制御器次元の系統的決定",
        "センサ／アクチュエータ配置とROM次数の同時設計事例が限定的。",
        [],
    ),
    (
        "未制御高次モード・スピルオーバー評価",
        "限定極配置後の残差モード安定性の定量ベンチマークが未整備。",
        [],
    ),
    (
        "産業機械・精密ステージへの実装",
        "工作機械多軸系でのFEM-ROM極配置の実機検証が少ない。",
        [],
    ),
]

TOPICS = {
    "T1": {
        "name": "FEM・CMS・モーダルモデル構築",
        "name_en": "FEM / CMS / modal model building",
        "subtopics": {
            "T1a": "有限要素モーダル解析",
            "T1b": "Craig-Bampton / 固定界面CMS",
            "T1c": "実験モード解析・GVTとの統合",
        },
    },
    "T2": {
        "name": "モデル次数削減・モーダル打ち切り",
        "name_en": "Model order reduction / modal truncation",
        "subtopics": {
            "T2a": "支配モード・低次ROM",
            "T2b": "バランシング・Krylov等のMOR",
            "T2c": "離散化・サンプリングとモード選択",
        },
    },
    "T3": {
        "name": "極配置・固有値割当",
        "name_en": "Pole placement / eigenvalue assignment",
        "subtopics": {
            "T3a": "状態フィードバック・LQR系",
            "T3b": "出力フィードバック・オブザーバ",
            "T3c": "MIMO・分散極配置",
        },
    },
    "T4": {
        "name": "限定・選択的極配置とスピルオーバー",
        "name_en": "Selective pole placement and spillover",
        "subtopics": {
            "T4a": "独立モーダル空間・部分極配置",
            "T4b": "残差モード・未制御モード",
            "T4c": "ロバスト・不確かさを考慮した配置",
        },
    },
    "T5": {
        "name": "応用（柔構造・ロボット・工作機械）",
        "name_en": "Applications",
        "subtopics": {
            "T5a": "柔軟マニピュレータ・リンク",
            "T5b": "工作機械・精密ステージ",
            "T5c": "航空・大型柔構造",
        },
    },
    "T6": {
        "name": "モデル更新・検証",
        "name_en": "Model updating and validation",
        "subtopics": {
            "T6a": "FEM更新・パラメータ同定",
            "T6b": "制御実験との比較検証",
            "T6c": "MAC・周波数整合",
        },
    },
}

_FEM_MODAL = (
    "finite element", "fem", "finite-element", "component mode", "craig-bampton",
    "cms", "modal analysis", "modal model", "normal mode", "eigenmode",
    "structural dynamics", "vibration mode",
)
_ROM = (
    "reduced-order", "reduced order", "model order reduction", "modal truncation",
    "low-order", "dominant mode", "truncated modal", "rom",
)
_POLE = (
    "pole placement", "pole-placement", "eigenvalue assignment", "eigenstructure",
    "state feedback", "controller design", "assignable pole",
)
_SELECTIVE = (
    "selective", "partial pole", "independent modal", "spillover", "residual mode",
    "uncontrolled mode", "limited pole", "modal selective",
)
_IPT_EXCLUDE = (
    "wireless power", "wpt", "ipt", "inductive charging", "rectenna",
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

    def hit(*words: str) -> bool:
        return any(w in blob for w in words)

    if hit(*_IPT_EXCLUDE) and not hit(*_POLE, *_FEM_MODAL):
        return []

    core = hit(*_FEM_MODAL) or hit(*_ROM)
    control = hit(*_POLE)
    if not (core and control) and not (
        hit("flexible", "vibration control", "structural control")
        and hit("modal", "pole", "eigenvalue", "feedback")
    ):
        return []

    out: list[tuple[str, str]] = []

    if hit("craig-bampton", "component mode", "cms", "interface mode"):
        out.append(("T1", "T1b"))
    elif hit("experimental modal", "ground vibration", "gvt", "ema"):
        out.append(("T1", "T1c"))
    elif hit(*_FEM_MODAL):
        out.append(("T1", "T1a"))

    if hit("balancing", "krylov", "gramian", "moment matching"):
        out.append(("T2", "T2b"))
    elif hit("truncat", "dominant mode", "low-order", "reduced-order", "model order"):
        out.append(("T2", "T2a"))
    elif hit(*_ROM):
        out.append(("T2", "T2c"))

    if hit("output feedback", "observer", "lqg", "kalman"):
        out.append(("T3", "T3b"))
    elif hit("mimo", "multi-input", "decentralized"):
        out.append(("T3", "T3c"))
    elif hit(*_POLE):
        out.append(("T3", "T3a"))

    if hit(*_SELECTIVE):
        out.append(
            (
                "T4",
                "T4a"
                if hit("independent modal", "partial pole", "selective")
                else "T4b"
                if hit("spillover", "residual", "uncontrolled")
                else "T4c",
            )
        )

    if hit("machine tool", "cnc", "precision stage", "ball screw", "manufacturing"):
        out.append(("T5", "T5b"))
    elif hit("manipulator", "robot", "flexible link", "flexible arm"):
        out.append(("T5", "T5a"))
    elif hit("aircraft", "wing", "spacecraft", "solar panel", "large structure"):
        out.append(("T5", "T5c"))

    if hit("model updating", "model update", "mac", "correlation", "validation"):
        out.append(
            (
                "T6",
                "T6a" if hit("updat", "identification", "fem") else "T6b" if hit("experiment", "test") else "T6c",
            )
        )

    if not out:
        out.append(("T3", "T3a"))

    return out
