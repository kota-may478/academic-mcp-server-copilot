"""
topics_human_state_aware.py — Topic/subtopic assignment for the
"Human State-Aware Robotics" survey.

Updated for the relaxed strong criteria (2026-05-29):
  ~735 strong papers covering physiological sensing, cognitive/affective state,
  intention/activity recognition, compliant control, and social robotics.

Seeds (step1_seed):
  R001 DOI:10.1016/j.robot.2013.05.007   Human-aware robot navigation: A survey
  R002 DOI:10.1142/S0219843608001303     Human-Robot Collaboration: a Survey
  R003 DOI:10.1007/s12369-014-0251-1     From Proxemics Theory to Socially-Aware Navigation

Original non-seed strong papers:
  R004 DOI:10.1109/LRA.2022.3143574      Human-State-Aware Controller (Tethered Aerial)
  R005 DOI:10.1109/LCSYS.2025.3579414   Human-State-Aware Non-Linear Control Framework
  R006 DOI:10.1016/j.cmpb.2013.02.003   Using "human state aware" robots (coop. scenario)
"""
from __future__ import annotations
import re

SEED_SUMMARIES = {
    "DOI:10.1016/j.robot.2013.05.007": (
        "人間対応型ロボットナビゲーションの体系的サーベイ。安全性・快適性・社会的受容性の観点から"
        "既存手法を分類し、Human State-Aware Roboticsの空間的・社会的基盤を提供する。"
    ),
    "DOI:10.1142/S0219843608001303": (
        "Human-Robot Collaboration (HRC) の包括的サーベイ。意図推定・共同行動・機械学習を横断整理し、"
        "人間状態推定を取り込んだ協働ロボットの理論的基盤を定める。"
    ),
    "DOI:10.1007/s12369-014-0251-1": (
        "近接学理論からソーシャル対応型ナビゲーションへの橋渡し。パーソナルスペース・社会的慣習を"
        "ロボット行動設計に落とし込み、Human State-Aware Navigationの社会的側面を論じる。"
    ),
}

TOPIC_SUMMARIES = {
    "T1": (
        "人間生理・脳神経状態の推定：EEG・EMG・心拍・皮膚電気等の生体信号からロボット制御に"
        "活用可能な人間の生理状態を推定・活用する研究群。"
    ),
    "T2": (
        "認知・感情・心理状態の推定と適応：認知負荷・ワークロード・感情・ストレス・疲労等の"
        "内部心理状態をロボットインタラクションに組み込む研究群。"
    ),
    "T3": (
        "意図・行動認識とHRC：人間の動作意図・行動パターンを認識し、物理的協働や"
        "タスク分担へ活用するロボットシステムの研究群。"
    ),
    "T4": (
        "人間状態適応型制御：推定された人間状態に基づきロボットの制御パラメータ・"
        "自律性・力を動的に適応させるフレームワークの研究群。"
    ),
    "T5": (
        "ソーシャル・近接ロボティクスとナビゲーション：近接学・感情・受容性・信頼を考慮した"
        "社会適合的なロボット行動設計と移動制御の研究群。"
    ),
}

RESEARCH_GAPS = [
    ("多次元状態の統合フレームワーク不在",
     "生理・認知・感情・運動状態を単一の制御フレームワークで統合的に扱う研究が少ない。",
     []),
    ("生理信号と物理制御の統合",
     "EEG・EMGによる疲労/認知状態推定を物理的接触制御（インピーダンス等）に直接組み込む研究が希少。",
     []),
    ("ベンチマーク・評価基準の不統一",
     "状態推定精度・制御適応品質・人間体験を統合的に評価する標準ベンチマークが存在しない。",
     []),
    ("汎用プラットフォームへの展開",
     "産業用協働ロボット・サービスロボット・自律走行車への人間状態認識の実装標準化が遅れている。",
     []),
    ("倫理・プライバシー・規制フレームワーク未整備",
     "連続的な生体データ取得を伴うロボットの個人情報保護・倫理審査の枠組みが確立されていない。",
     []),
    ("人間信頼・受容性とのトレードオフ",
     "高精度状態推定に必要なセンシング密度が人間の信頼・受容性を損なう可能性の系統的評価が不足。",
     []),
    ("長期・動的シナリオへの適応",
     "単一タスク・短時間実験が主流であり、長期使用・状態変化への継続的適応評価が不足。",
     []),
    ("文化・個人差への対応",
     "感情表現・疲労閾値・パーソナルスペースの文化差・個人差を考慮したロボット設計研究が少ない。",
     []),
]

TOPICS = {
    "T1": {
        "name": "人間生理・脳神経状態の推定",
        "name_en": "Physiological and Neural State Estimation",
        "subtopics": {
            "T1a": "脳波（EEG）を用いた状態推定・BCI",
            "T1b": "筋電図（EMG）を用いた動作・疲労推定",
            "T1c": "多重生理信号融合（心拍・皮膚電気・呼吸等）",
        },
    },
    "T2": {
        "name": "認知・感情・心理状態の推定と適応",
        "name_en": "Cognitive, Affective, and Psychological State Estimation",
        "subtopics": {
            "T2a": "認知負荷・ワークロード推定",
            "T2b": "感情認識とロボット行動適応",
            "T2c": "ストレス・疲労・痛みの検出",
        },
    },
    "T3": {
        "name": "意図・行動認識とHRC",
        "name_en": "Intention and Activity Recognition for HRC",
        "subtopics": {
            "T3a": "人間意図認識（物理的協調・制御）",
            "T3b": "人間行動認識（協調作業・支援）",
            "T3c": "信頼・受容性推定とHRC適応",
        },
    },
    "T4": {
        "name": "人間状態適応型制御",
        "name_en": "Human State-Adaptive Control",
        "subtopics": {
            "T4a": "アドミタンス・インピーダンス・コンプライアント制御",
            "T4b": "自律性レベル・役割分担の動的調整",
            "T4c": "空中ロボット・物理ガイダンス制御",
        },
    },
    "T5": {
        "name": "ソーシャル・近接ロボティクスとナビゲーション",
        "name_en": "Social, Proxemic Robotics, and Navigation",
        "subtopics": {
            "T5a": "近接学・パーソナルスペース・社会ナビゲーション",
            "T5b": "感情的受容性・信頼形成の設計",
            "T5c": "感情対応型・社会対応型ロボット設計",
        },
    },
}


# ── Helpers ────────────────────────────────────────────────────────────────────

def _blob(entry: dict) -> str:
    title    = (entry.get("title")    or "").lower()
    abstract = (entry.get("abstract") or "").lower()
    kws = entry.get("keywords") or {}
    parts = [title, abstract]
    for ax in "PAOM":
        parts.extend(str(k).lower() for k in (kws.get(ax) or []))
    return " ".join(parts)


def _doi_upper(entry: dict) -> str:
    return entry.get("candidate_key", "").upper()


def _has(blob: str, *terms) -> bool:
    return any(t in blob for t in terms)


def _re(blob: str, pattern: str) -> bool:
    return bool(re.search(pattern, blob))


def assign_subtopics(entry: dict) -> list[tuple[str, str]]:
    """Return list of (topic_id, subtopic_id) tuples for this entry."""
    blob = _blob(entry)
    doi  = _doi_upper(entry)
    result: list[tuple[str, str]] = []

    # ─── T1: Physiological & Neural State Estimation ──────────────────────────
    # T1a: EEG-based
    if _has(blob, "eeg") and _has(blob, "robot", "bci", "exoskeleton", "hri", "hrc",
                                   "collaboration", "rehabilitation"):
        result.append(("T1", "T1a"))

    # T1b: EMG-based
    if _has(blob, "emg") and _has(blob, "robot", "exoskeleton", "hri", "hrc",
                                   "collaboration", "rehabilitation"):
        result.append(("T1", "T1b"))

    # T1c: multi-physiological signals (heart rate, galvanic skin, respiration, etc.)
    physio_signals = ("heart rate", "galvanic skin", "skin conductance", "respiration",
                      "gsr ", "ecg ", "hrv ", "ppg ", "bvp ")
    if (_has(blob, *physio_signals) or
            (_re(blob, r"\bphysiological\b|\bpsychophysiological\b") and
             not _has(blob, "emg", "eeg"))):
        if _has(blob, "robot", "hri", "hrc", "collaboration"):
            result.append(("T1", "T1c"))

    # ─── T2: Cognitive, Affective, Psychological State ────────────────────────
    # T2a: cognitive load / workload
    if _has(blob, "cognitive load", "workload", "mental workload", "cognitive fatigue",
            "mental fatigue", "cognitive effort"):
        if _has(blob, "robot", "hri", "hrc", "automation", "operator"):
            result.append(("T2", "T2a"))

    # T2b: emotion recognition for robot adaptation
    if _re(blob, r"emotion recognition|emotion detection|emotion classification|affective recognition"):
        if _has(blob, "robot", "hri", "hrc", "interaction", "navigation"):
            result.append(("T2", "T2b"))
    if _has(blob, "affective computing") and _has(blob, "robot", "hri", "hrc"):
        result.append(("T2", "T2b"))

    # T2c: stress, fatigue, pain detection
    if _has(blob, "stress detection", "stress recognition", "stress estimation"):
        if _has(blob, "robot", "hri", "hrc"):
            result.append(("T2", "T2c"))
    if _has(blob, "fatigue") and _has(blob, "robot", "hri", "hrc", "exoskeleton",
                                       "collaboration", "manufacturing"):
        result.append(("T2", "T2c"))
    if _has(blob, "pain detection", "pain recognition", "pain estimation"):
        if _has(blob, "robot", "rehabilitation"):
            result.append(("T2", "T2c"))

    # ─── T3: Intention / Activity Recognition for HRC ─────────────────────────
    # T3a: intention recognition (physical interaction / control)
    if _has(blob, "human intention", "intention recognition", "intent estimation",
            "intention prediction", "intent prediction"):
        if _has(blob, "robot", "collaboration", "physical", "control", "planning"):
            result.append(("T3", "T3a"))

    # T3b: activity recognition (collaborative tasks)
    if _re(blob, r"activity recognition|action recognition|gesture recognition"):
        if _has(blob, "robot", "hri", "hrc", "collaboration", "assistance", "control"):
            result.append(("T3", "T3b"))

    # T3c: trust / acceptance estimation for HRC
    if _has(blob, "trust") and _has(blob, "robot", "hri", "hrc", "collaboration"):
        if _has(blob, "physiological", "psychophysiological", "estimation", "prediction",
                "model", "measurement", "measure"):
            result.append(("T3", "T3c"))
    if _has(blob, "acceptance") and _has(blob, "robot", "hri"):
        if _has(blob, "measurement", "estimation", "factor", "model"):
            result.append(("T3", "T3c"))

    # ─── T4: Human State-Adaptive Control ────────────────────────────────────
    # T4a: admittance / impedance / compliant control
    phys_ctrl_terms = ("admittance", "impedance control", "compliance control",
                       "force control", "physical hri", "physical human-robot",
                       "haptic", "torque control")
    if _has(blob, *phys_ctrl_terms):
        result.append(("T4", "T4a"))
    # Also assign T4a for exoskeleton / rehabilitation with state feedback
    if _has(blob, "exoskeleton", "rehabilitation", "orthosis"):
        if _has(blob, "control", "assist", "adapt"):
            result.append(("T4", "T4a"))

    # T4b: autonomy level / role allocation adaptation
    if _has(blob, "level of automation", "autonomy level", "variable autonomy",
            "adaptive automation", "human-in-the-loop", "adjustable autonomy",
            "shared autonomy", "supervisory control"):
        if _has(blob, "robot", "hri", "hrc", "operator"):
            result.append(("T4", "T4b"))
    if _has(blob, "task allocation", "role allocation", "workload management"):
        if _has(blob, "robot", "human"):
            result.append(("T4", "T4b"))

    # T4c: aerial robot / physical guidance (original cluster)
    if _has(blob, "aerial robot", "tethered", "uav", "drone") and _has(
            blob, "human", "physical interaction", "guidance", "transport"):
        result.append(("T4", "T4c"))
    # Original seed DOIs
    if doi in ("DOI:10.1109/LRA.2022.3143574", "DOI:10.1109/LCSYS.2025.3579414"):
        result.append(("T4", "T4c"))

    # ─── T5: Social, Proxemic Robotics, Navigation ────────────────────────────
    # T5a: proxemics, personal space, social navigation
    prox_terms = ("proxemics", "personal space", "social navigation", "social robot nav",
                  "socially aware nav", "socially-aware nav", "human-aware nav",
                  "pedestrian", "crowd")
    if _has(blob, *prox_terms) or doi in (
            "DOI:10.1016/J.ROBOT.2013.05.007",
            "DOI:10.1007/S12369-014-0251-1",
    ):
        result.append(("T5", "T5a"))

    # T5b: emotional acceptability, trust design, user experience
    if _has(blob, "user experience", "user acceptance", "likert", "questionnaire",
            "ux ", "user study"):
        if _has(blob, "robot", "hri"):
            result.append(("T5", "T5b"))
    if _has(blob, "social acceptance", "robot acceptance"):
        result.append(("T5", "T5b"))
    if doi == "DOI:10.1142/S0219843608001303":
        result.append(("T5", "T5b"))

    # T5c: emotion-aware / social robot design
    social_design = ("social robot", "socially expressive", "emotion expressio",
                     "affective robot", "empathic robot", "companion robot",
                     "care robot", "therapy robot", "entertainment robot")
    if _has(blob, *social_design):
        result.append(("T5", "T5c"))
    if _has(blob, "facial expression") and _has(blob, "robot"):
        result.append(("T5", "T5c"))

    # ─── Fallback: ensure strong papers get at least one topic ────────────────
    if not result:
        # Generic assignment based on dominant keywords
        if _has(blob, "eeg", "emg", "physiological"):
            result.append(("T1", "T1c"))
        elif _has(blob, "emotion", "affective", "sentiment"):
            result.append(("T2", "T2b"))
        elif _has(blob, "intention", "activity recognition", "action recognition"):
            result.append(("T3", "T3b"))
        elif _has(blob, "control", "controller", "adaptive"):
            result.append(("T4", "T4b"))
        else:
            result.append(("T5", "T5c"))

    # ─── Deduplicate while preserving order ───────────────────────────────────
    seen: set[tuple[str, str]] = set()
    unique = []
    for pair in result:
        if pair not in seen:
            seen.add(pair)
            unique.append(pair)
    return unique
