"""
topics_dwpt_ev.py — Domain topics for Dynamic Wireless Power Transfer for Electric Vehicles survey.
"""
from __future__ import annotations

SEED_SUMMARIES: dict[str, str] = {
    "DOI:10.1109/access.2021.3116678": "電気自動車向け誘導式無線給電（IPT）の充電システムを包括的にレビュー。コイル設計・補償トポロジー・制御手法・安全規格を網羅し、今後の課題を整理している。",
    "DOI:10.1016/J.JESTCH.2018.06.015": "静的・動的両方の電気自動車用無線充電システムを体系的に比較レビュー。各方式の原理・コイル・回路・制御・規格を俯瞰し、実用化に向けた課題を整理している。",
    "DOI:10.1109/access.2023.3300475": "電気自動車向け無線給電技術の最新動向を包括的にレビュー。コイル設計・トポロジー・制御・EMF安全・V2G統合など多面的に現状と将来展望を整理している。",
}

TOPIC_SUMMARIES: dict[str, str] = {
    "T1": "コイル設計と磁気結合はDWPTシステムの送受電効率とミスアライメント耐性を直接左右する基盤技術であり、DD型・DDQ型・バイポーラ型などの形状最適化とフェライトコア・シールド設計が研究の中心である。",
    "T2": "補償回路とパワーエレクトロニクスはSSトポロジーからLCC-LCC構成まで多様な方式が提案され、ZVS/ZCS軟スイッチングや高周波インバータ設計が効率・熱管理の観点から精力的に研究されている。",
    "T3": "制御アルゴリズムは走行中のギャップ変動・ミスアライメント・負荷変動に対してリアルタイムで効率を維持する鍵であり、MPC・スライディングモード・インピーダンス追従・相互インダクタンス推定などが活発に研究されている。",
    "T4": "動的WPTシステム構成はセグメント型路面コイルアレイから連続型レール方式まで多様な路面実装形態が提案されており、走行中給電インフラの実用化に向けてコスト・施工性・電力継続性のトレードオフが議論されている。",
    "T5": "電磁安全性と国際規格（SAE J2954・IEC 61980・ISO 15118など）はEV向けWPTの市場展開において不可欠な要件であり、異物検知・人体暴露低減・相互運用性の確保が研究・標準化の両面で進められている。",
}

RESEARCH_GAPS: list[tuple[str, str, list[str]]] = [
    ("走行中ミスアライメント耐性の統一評価指標", "動的ミスアライメント下での効率劣化を比較できる標準ベンチマークが存在しない。", []),
    ("大規模路面コイルアレイの電磁干渉", "複数セグメントが同時励磁される際の相互干渉とEMF管理手法が未確立である。", []),
    ("V2G統合と双方向DWPT制御", "走行中の双方向電力潮流制御とグリッド安定化手法の研究が限定的である。", []),
    ("実車プロトタイプによる長期耐久試験", "実道路条件での長期実証データが不足しており、耐久性・保守性の評価が難しい。", []),
    ("コスト最適化と経済性分析", "路面埋設コイルを含む全体インフラコストの定量的な経済性分析が少ない。", []),
]

TOPICS: dict[str, dict] = {
    "T1": {
        "name": "コイル設計と磁気結合",
        "name_en": "Coil Design and Magnetic Coupling",
        "subtopics": {
            "T1a": "コイル形状設計（DD・DDQ・バイポーラ・ソレノイド）",
            "T1b": "フェライト・シールド材料と構造",
            "T1c": "ミスアライメント耐性と結合モデル",
        },
    },
    "T2": {
        "name": "補償回路とパワーエレクトロニクス",
        "name_en": "Compensation Circuits and Power Electronics",
        "subtopics": {
            "T2a": "補償トポロジー（SS・SP・LCC・LLC等）",
            "T2b": "インバータ設計とZVS/ZCS軟スイッチング",
            "T2c": "整流・DC-DC変換回路",
        },
    },
    "T3": {
        "name": "制御アルゴリズムと効率最適化",
        "name_en": "Control Algorithms and Efficiency Optimization",
        "subtopics": {
            "T3a": "周波数制御・インピーダンス追従制御",
            "T3b": "相互インダクタンス推定・モデル予測制御",
            "T3c": "最大効率追従（MEPT）・適応制御",
        },
    },
    "T4": {
        "name": "動的WPTシステム構成",
        "name_en": "Dynamic WPT System Architecture",
        "subtopics": {
            "T4a": "走行中給電（DWPT）の路面コイルアレイ設計",
            "T4b": "準動的・セグメント型充電システム",
            "T4c": "インフラ統合と電力供給系設計",
        },
    },
    "T5": {
        "name": "電磁安全性と規格",
        "name_en": "Electromagnetic Safety and Standards",
        "subtopics": {
            "T5a": "EMF暴露評価とシールド設計",
            "T5b": "異物・生体検知（FOD・LOD）",
            "T5c": "国際規格（SAE J2954・IEC 61980・ISO 15118）と相互運用性",
        },
    },
    "T6": {
        "name": "EV統合・V2G・蓄電システム",
        "name_en": "EV Integration, V2G, and Energy Storage",
        "subtopics": {
            "T6a": "V2G双方向電力潮流と系統連系",
            "T6b": "バッテリー管理とオンボード搭載設計",
            "T6c": "走行時消費電力モデルと充電戦略",
        },
    },
    "T7": {
        "name": "解析・シミュレーション手法",
        "name_en": "Analysis and Simulation Methods",
        "subtopics": {
            "T7a": "有限要素解析（FEA/FEM）と電磁場シミュレーション",
            "T7b": "等価回路モデルとMATLAB/Simulinkシミュレーション",
            "T7c": "最適化手法（パラメータ最適化・感度解析）",
        },
    },
    "T8": {
        "name": "実証実験・プロトタイプ開発",
        "name_en": "Experimental Validation and Prototypes",
        "subtopics": {
            "T8a": "実験台・小型プロトタイプによる検証",
            "T8b": "実車・路面埋設コイルの実証試験",
            "T8c": "システム性能評価（効率・電力・熱）",
        },
    },
}


def _blob(entry: dict) -> str:
    title = (entry.get("title") or "").lower()
    kws = entry.get("keywords") or {}
    abstract = (entry.get("abstract") or "").lower()[:600]
    parts = [title, abstract]
    for ax in "PAOM":
        parts.extend(str(k).lower() for k in (kws.get(ax) or []))
    return " ".join(parts)


def assign_subtopics(entry: dict) -> list[tuple[str, str]]:
    blob = _blob(entry)
    out: list[tuple[str, str]] = []

    def hit(*words: str) -> bool:
        return any(w in blob for w in words)

    # T1: Coil design
    if hit("coil", "coupling", "ferrite", "litz wire", "misalignment", "mutual inductance", "coupling coefficient", "shielding plate"):
        if hit("dd coil", "ddq", "bipolar coil", "solenoid coil", "circular coil", "rectangular coil", "helical coil"):
            out.append(("T1", "T1a"))
        elif hit("ferrite core", "ferrite plate", "aluminum shielding", "nano-crystalline", "permalloy", "shielding material"):
            out.append(("T1", "T1b"))
        else:
            out.append(("T1", "T1c"))

    # T2: Compensation + power electronics
    if hit("compensation", "topology", "inverter", "rectifier", "converter", "zvs", "zcs", "lcc", "llc resonan", "series-series"):
        if hit("series-series", "ss compensation", "series-parallel", "lcc compensation", "llc resonan", "lc compensation", "compensation network", "compensation topology"):
            out.append(("T2", "T2a"))
        elif hit("inverter", "zvs", "zcs", "soft switching", "class e", "h-bridge", "full bridge", "half bridge", "switching frequency"):
            out.append(("T2", "T2b"))
        else:
            out.append(("T2", "T2c"))

    # T3: Control
    if hit("control", "controller", "frequency control", "impedance match", "adaptive", "model predictive", "pid", "sliding mode", "efficiency track", "mutual inductance estimation", "mept"):
        if hit("frequency control", "impedance match", "frequency tuning", "variable frequency", "frequency track"):
            out.append(("T3", "T3a"))
        elif hit("model predictive", "mutual inductance estimation", "parameter identification", "sliding mode", "mpc"):
            out.append(("T3", "T3b"))
        else:
            out.append(("T3", "T3c"))

    # T4: Dynamic WPT architecture
    if hit("dynamic", "dwpt", "on-road", "in-motion", "moving vehicle", "roadway", "charging lane", "coil array", "segmented track", "quasi-dynamic", "online electric vehicle"):
        if hit("coil array", "segmented", "track coil", "roadway coil", "embedded coil", "primary coil array", "charging lane coil"):
            out.append(("T4", "T4a"))
        elif hit("quasi-dynamic", "semi-dynamic", "intermittent", "segmented charging"):
            out.append(("T4", "T4b"))
        else:
            out.append(("T4", "T4c"))

    # T5: EMF safety + standards
    if hit("emf", "electromagnetic safety", "foreign object", "fod", "living object", "lod", "sae j2954", "iec 61980", "iso 15118", "emf exposure", "icnirp", "interoperab"):
        if hit("emf exposure", "magnetic flux density", "icnirp", "sar", "human body", "health effect"):
            out.append(("T5", "T5a"))
        elif hit("foreign object detection", "fod", "living object detection", "lod"):
            out.append(("T5", "T5b"))
        else:
            out.append(("T5", "T5c"))

    # T6: EV integration + V2G
    if hit("v2g", "vehicle to grid", "bidirectional", "battery management", "bms", "state of charge", "soc", "charging strateg", "power management", "onboard charger"):
        if hit("v2g", "vehicle to grid", "grid integration", "bidirectional power", "grid stability"):
            out.append(("T6", "T6a"))
        elif hit("battery management", "bms", "state of charge", "soc", "lithium battery"):
            out.append(("T6", "T6b"))
        else:
            out.append(("T6", "T6c"))

    # T7: Simulation
    if hit("finite element", "fea", "fem", "ansys", "comsol", "equivalent circuit model", "matlab", "simulink", "circuit simulation", "optimization"):
        if hit("finite element", "fea", "fem", "ansys maxwell", "comsol", "electromagnetic field simulation"):
            out.append(("T7", "T7a"))
        elif hit("matlab", "simulink", "equivalent circuit", "circuit model", "pspice"):
            out.append(("T7", "T7b"))
        else:
            out.append(("T7", "T7c"))

    # T8: Experimental validation
    if hit("experiment", "prototype", "test bench", "measurement", "validation", "demonstration", "proof of concept", "fabricated"):
        if hit("prototype", "test bench", "laboratory test", "bench test", "small-scale", "lab"):
            out.append(("T8", "T8a"))
        elif hit("vehicle test", "road test", "field test", "full-scale", "in-vehicle", "pilot project"):
            out.append(("T8", "T8b"))
        else:
            out.append(("T8", "T8c"))

    # Fallback
    if not out and hit("wpt", "ipt", "wireless power transfer", "inductive power transfer", "wireless charging", "inductive charging"):
        out.append(("T2", "T2a"))

    return list(dict.fromkeys(out))
