"""
Topics module for: Decoupling Control of Industrial Machines survey.
Taxonomy derived from 607-paper strong corpus keyword analysis.
"""
from __future__ import annotations

SEED_SUMMARIES = {
    "DOI:10.1007/S12555-018-0367-4": (
        "産業用MIMOシステムにおける非干渉化制御の手法・設計・応用を包括的にレビューした論文。"
        "相対ゲイン配列・対角優位・フィードフォワード補償など基本概念を体系的に整理する。"
    ),
    "DOI:10.3390/app13148037": (
        "製造業における産業用ロボット制御の動向・課題・機会を広範にサーベイした論文。"
        "強化学習・協働ロボット・デジタルツイン等の最新トレンドを概観する。"
    ),
    "DOI:10.3390/robotics13030042": (
        "ロボットマニピュレータの高度制御戦略と最先端トレンドをIn-Depthで概説したレビュー論文。"
        "計算トルク・スライディングモード・適応制御など多様な手法を網羅する。"
    ),
}

TOPIC_SUMMARIES = {
    "T1": "シリアル/剛体マニピュレータにおける非干渉化制御の設計と実装。",
    "T2": "並列ロボット・パラレルメカニズムにおける非干渉化制御の特有課題。",
    "T3": "CNC工作機械・精密送り系・ナノ位置決めでの非干渉化と輪郭誤差補償。",
    "T4": "誘導電動機・PMSMのトルク-磁束非干渉化（FOC系）とベクトル制御。",
    "T5": "油圧駆動マニピュレータ・歩行ロボットにおける非干渉化制御。",
    "T6": "移動ロボット・外骨格・宇宙ロボット等の特殊ロボットへの非干渉化制御の適用。",
    "T7": "外乱オブザーバ・拡張状態オブザーバ・ADRCを中核とした非干渉化制御手法。",
    "T8": "ニューラルネットワーク・強化学習・データ駆動型手法による非干渉化制御。",
    "T9": "モデル予測制御・反復学習制御・ロバスト制御による非干渉化の汎用的枠組み。",
}

RESEARCH_GAPS = [
    ("データ駆動型非干渉化のベンチマーク不足", "統一評価指標・標準ベンチマークがない。", []),
    ("デジタルツイン統合", "実機とデジタルツインの連携による非干渉化制御設計が未開拓。", []),
    ("産業実装・標準化の欠如", "PLCやROS2への実装標準がなく普及障壁となっている。", []),
    ("協働ロボット・ヒューマンロボットインタラクション", "人との力学的干渉に対する非干渉化理論が不十分。", []),
    ("マルチロボット協調作業での非干渉化", "複数ロボット間の力学的干渉補償の理論的枠組みが乏しい。", []),
    ("半導体製造・精密位置決め分野での先進技術", "ナノ精度要求下での非干渉化手法の検証事例が少ない。", []),
    ("再構成可能生産ラインへの適用", "モジュラー機械への非干渉化制御の適応的再設計が未整備。", []),
    ("エネルギー効率を考慮した非干渉化設計", "非干渉化制御とエネルギー最小化の同時最適化研究が不足。", []),
]

TOPICS = {
    "T1": {
        "name": "シリアルマニピュレータの非干渉化制御",
        "name_en": "Serial Manipulator Decoupling Control",
        "subtopics": {
            "T1a": "計算トルク・逆ダイナミクス法",
            "T1b": "スライディングモード・ロバスト制御",
            "T1c": "適応制御・自己調整",
            "T1d": "力制御・インピーダンス制御",
        },
    },
    "T2": {
        "name": "並列ロボット・パラレルメカニズムの非干渉化制御",
        "name_en": "Parallel Robot Decoupling Control",
        "subtopics": {
            "T2a": "デルタロボット・スチュワートプラットフォーム",
            "T2b": "多自由度並列機構の動力学モデル",
            "T2c": "並列機構の精密位置決め",
        },
    },
    "T3": {
        "name": "工作機械・CNC・精密位置決めの非干渉化制御",
        "name_en": "Machine Tool / CNC / Precision Positioning Decoupling Control",
        "subtopics": {
            "T3a": "輪郭誤差・クロスカップリング補償",
            "T3b": "マルチ軸非干渉化・ツイン駆動",
            "T3c": "ナノ位置決め・精密ステージ",
        },
    },
    "T4": {
        "name": "電動機・サーボドライブの非干渉化制御",
        "name_en": "Motor / Servo Drive Decoupling Control",
        "subtopics": {
            "T4a": "誘導電動機トルク-磁束非干渉化",
            "T4b": "PMSMのd-q軸非干渉化",
            "T4c": "スピンドル・サーボシステム",
        },
    },
    "T5": {
        "name": "油圧駆動ロボット・歩行機械の非干渉化制御",
        "name_en": "Hydraulic Robot / Legged Machine Decoupling Control",
        "subtopics": {
            "T5a": "油圧マニピュレータ関節非干渉化",
            "T5b": "4足・2足歩行ロボット油圧系",
        },
    },
    "T6": {
        "name": "移動ロボット・特殊ロボットの非干渉化制御",
        "name_en": "Mobile / Special Robot Decoupling Control",
        "subtopics": {
            "T6a": "移動マニピュレータ・車輪型ロボット",
            "T6b": "外骨格・リハビリロボット",
            "T6c": "宇宙ロボット・水中ロボット",
        },
    },
    "T7": {
        "name": "外乱オブザーバ・拡張状態オブザーバによる非干渉化",
        "name_en": "DOB / ESO / ADRC-Based Decoupling",
        "subtopics": {
            "T7a": "外乱オブザーバ（DOB）",
            "T7b": "拡張状態オブザーバ・ADRC",
            "T7c": "等価入力外乱（EID）",
        },
    },
    "T8": {
        "name": "データ駆動・学習型非干渉化制御",
        "name_en": "Data-Driven / Learning-Based Decoupling Control",
        "subtopics": {
            "T8a": "ニューラルネットワーク逆システム法",
            "T8b": "強化学習・深層強化学習",
            "T8c": "データ駆動フィードフォワード",
        },
    },
    "T9": {
        "name": "モデル予測・ロバスト・繰り返し学習制御による非干渉化",
        "name_en": "MPC / Robust / ILC-Based Decoupling",
        "subtopics": {
            "T9a": "モデル予測制御（MPC）",
            "T9b": "ロバスト制御・H∞法",
            "T9c": "反復学習制御（ILC）",
        },
    },
}


def _blob(entry: dict) -> str:
    title = (entry.get("title") or "").lower()
    kws = entry.get("keywords") or {}
    parts = [title]
    for ax in "PAOM":
        parts.extend(str(k) for k in (kws.get(ax) or []))
    ab = (entry.get("abstract") or "").lower()[:400]
    parts.append(ab)
    return " ".join(parts)


def _hit(blob: str, *words: str) -> bool:
    return any(w in blob for w in words)


def assign_subtopics(entry: dict) -> list[tuple[str, str]]:
    blob = _blob(entry)
    out: list[tuple[str, str]] = []

    # ---------- T1: Serial Manipulator ----------
    serial_ctx = _hit(blob, "manipulator", "robot arm", "robotic arm", "serial robot",
                       "link robot", "joint robot", "rigid robot")
    parallel_ctx = _hit(blob, "parallel robot", "parallel manipulator", "delta robot",
                        "stewart", "hexapod", "parallel mechanism")
    hydraulic_ctx = _hit(blob, "hydraulic", "hydro")
    mobile_ctx = _hit(blob, "mobile robot", "wheeled", "differential drive",
                       "autonomous mobile", "wheeled robot")
    legged_ctx = _hit(blob, "quadruped", "biped", "legged robot", "hexapod robot",
                       "walking robot")
    exo_ctx = _hit(blob, "exoskeleton", "rehabilitation", "prosthetic", "lower limb")
    space_ctx = _hit(blob, "space robot", "satellite", "orbital", "space manipulator",
                      "underwater robot", "surgical robot", "aerial manipulator")
    motor_ctx = _hit(blob, "induction motor", "pmsm", "synchronous motor",
                      "permanent magnet", "motor drive", "motor control", "vector control")
    cnc_ctx = _hit(blob, "machine tool", "cnc", "milling", "machining center",
                    "feed drive", "spindle", "contouring", "contour error")
    nano_ctx = _hit(blob, "nanopositioning", "nano-positioning", "piezo", "xy stage",
                     "precision stage", "wafer stage", "lithography")
    gantry_ctx = _hit(blob, "gantry", "twin-drive", "dual-drive", "overhead crane")

    # T1: serial manipulator (non-parallel, non-hydraulic-dominant)
    if serial_ctx and not parallel_ctx:
        if _hit(blob, "computed torque", "inverse dynamics", "jacobian", "inertia"):
            out.append(("T1", "T1a"))
        elif _hit(blob, "sliding mode", "smc", "super twisting", "terminal sliding"):
            out.append(("T1", "T1b"))
        elif _hit(blob, "adaptive", "self-tuning", "mrac", "model reference"):
            out.append(("T1", "T1c"))
        elif _hit(blob, "force control", "impedance", "admittance", "contact force"):
            out.append(("T1", "T1d"))
        else:
            out.append(("T1", "T1a"))  # default for serial manipulators

    # T1d: force/impedance specifically
    if _hit(blob, "force control", "impedance control", "admittance") and (serial_ctx or parallel_ctx):
        if ("T1", "T1d") not in out:
            out.append(("T1", "T1d"))

    # T2: parallel robot
    if parallel_ctx:
        if _hit(blob, "delta", "stewart", "hexapod", "3-rsr", "3-rrr"):
            out.append(("T2", "T2a"))
        elif _hit(blob, "dynamic", "dynamic model", "dynamic decoupling"):
            out.append(("T2", "T2b"))
        else:
            out.append(("T2", "T2c"))

    # T3: CNC / machine tool
    if cnc_ctx or nano_ctx or gantry_ctx:
        if _hit(blob, "contour", "contouring", "cross-coupling", "cross coupling",
                "contour error"):
            out.append(("T3", "T3a"))
        elif _hit(blob, "twin-drive", "dual-drive", "gantry", "synchronous",
                  "multi-axis", "axis decoupling"):
            out.append(("T3", "T3b"))
        elif nano_ctx or _hit(blob, "nanopositioning", "piezo", "precision stage", "wafer"):
            out.append(("T3", "T3c"))
        else:
            out.append(("T3", "T3b"))

    # T4: motor drives
    if motor_ctx:
        if _hit(blob, "induction motor", "im ", "asynchronous"):
            out.append(("T4", "T4a"))
        elif _hit(blob, "pmsm", "permanent magnet synchronous", "pm motor"):
            out.append(("T4", "T4b"))
        elif _hit(blob, "spindle", "servo system", "servo motor"):
            out.append(("T4", "T4c"))
        else:
            out.append(("T4", "T4a"))

    # T5: hydraulic / legged
    if hydraulic_ctx or legged_ctx:
        if legged_ctx or _hit(blob, "leg", "quadruped", "biped"):
            out.append(("T5", "T5b"))
        else:
            out.append(("T5", "T5a"))

    # T6: mobile / special robots
    if mobile_ctx:
        out.append(("T6", "T6a"))
    if exo_ctx:
        out.append(("T6", "T6b"))
    if space_ctx:
        out.append(("T6", "T6c"))

    # T7: DOB / ESO / ADRC
    if _hit(blob, "disturbance observer", "dob", "extended state observer", "eso",
             "active disturbance rejection", "adrc", "ladrc",
             "equivalent input disturbance", "eid"):
        if _hit(blob, "equivalent input disturbance", "eid"):
            out.append(("T7", "T7c"))
        elif _hit(blob, "extended state observer", "eso", "adrc", "ladrc",
                  "active disturbance rejection"):
            out.append(("T7", "T7b"))
        else:
            out.append(("T7", "T7a"))

    # T8: data-driven / learning
    if _hit(blob, "neural network", "deep learning", "reinforcement learning",
             "lstm", "data-driven", "data driven", "machine learning"):
        if _hit(blob, "reinforcement learning", "deep reinforcement", "ddpg", "dqn"):
            out.append(("T8", "T8b"))
        elif _hit(blob, "inverse system", "neural network inverse"):
            out.append(("T8", "T8a"))
        else:
            out.append(("T8", "T8c"))

    # T9: MPC / H-inf / ILC
    if _hit(blob, "model predictive", "mpc", "nmpc"):
        out.append(("T9", "T9a"))
    if _hit(blob, "h-infinity", "h infinity", "h∞", "hinf", "mu synthesis", "robust control"):
        out.append(("T9", "T9b"))
    if _hit(blob, "iterative learning", "ilc", "repetitive control"):
        out.append(("T9", "T9c"))

    # Fallback: if nothing assigned but clearly decoupling + robot/machine
    if not out:
        if serial_ctx:
            out.append(("T1", "T1a"))
        elif parallel_ctx:
            out.append(("T2", "T2b"))
        elif motor_ctx:
            out.append(("T4", "T4a"))
        elif cnc_ctx:
            out.append(("T3", "T3b"))

    return list(dict.fromkeys(out))
