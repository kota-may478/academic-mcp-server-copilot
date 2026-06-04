"""Topic assignment for operational modal analysis (OMA) / in-flight structural identification surveys."""
from __future__ import annotations

SEED_SUMMARIES = {
    "DOI:10.1115/1.1410370": (
        "確率的手法による運用モード解析（OMA）のレビュー。"
        "飛行・運用データからモードパラメータを同定する理論的基盤文献。"
    ),
    "DOI:10.1016/J.ENG.2018.11.030": (
        "コンピュータビジョンによる土木インフラ計測のレビュー。"
        "光学非接触計測と構造モニタリングの交差領域の背景として参照。"
    ),
    "DOI:10.1007/S11831-012-9069-X": (
        "運用・実験モード解析向けシステム同定手法の比較レビュー。"
        "OMAアルゴリズム選択の中核文献。"
    ),
    "DOI:10.1371/journal.pone.0113571": (
        "（境界シード）OMAとは無関係。Step 1 シード免疫により strong に保持。"
    ),
}

TOPIC_SUMMARIES = {
    "T1": "FDD・SSI・NExT等のOMA/システム同定アルゴリズムとモードパラメータ推定の理論・実装。",
    "T2": "飛行試験・ホバリング・回転運用中の運用モード同定と閉ループ・運用条件下の同定。",
    "T3": "地上GVT/EMA・インパクト・シェイカ・プロペラ励振試験など地上・準飛行ベンチマーク。",
    "T4": "UAV・マルチロータ・ヘリコプタ・固定翼など航空機構造の振動・モード同定。",
    "T5": "モーションキャプチャ・DIC・写真測量・レーザー等の光学・非接触変位計測。",
    "T6": "橋梁・建築・風洞モデル等の土木・実験構造におけるOMA/SHM。",
}

RESEARCH_GAPS = [
    (
        "飛行中UAV機体×外部光学MCS×OMA",
        "ホバリング中マルチロータの振動分布可視化はあるが、モード同定まで到達した飛行中光学OMAは未整備。",
        [],
    ),
    (
        "ティルトウィング・空力連成下の飛行中OMA",
        "プロペラ後流が翼に作用する構成での飛行中閉ループモード同定の体系的研究が少ない。",
        [],
    ),
    (
        "GVTと飛行中OMAの差分定量化",
        "地上構造モードと運用中モードの差を空力・制御影響として切り出す標準手順が不足。",
        [],
    ),
    (
        "剛体運動除去と低周波OMA",
        "外部計測での剛体・弾性分離とサンプリングレート制約下の低次モード同定指針が未統一。",
        [],
    ),
    (
        "搭載加速度計との比較ベンチマーク",
        "非接触OMAと搭載センサOMAの精度・帯域・付加質量影響の系統比較が限定的。",
        [],
    ),
    (
        "プロペラBPFと構造モードの分離",
        "既知調和励振と構造モードの周波数重複時の分離・再現性評価が不足。",
        [],
    ),
    (
        "中型UAV向け計測プロトコル",
        "マーカー配置・記録時間・統計収束の実務ガイドラインが機体クラス別に未整備。",
        [],
    ),
    (
        "UAV以外プラットフォームへの転用",
        "回転翼・固定翼で確立された飛行中光学OMAのUAVフレームへの一般化が不十分。",
        [],
    ),
]

TOPICS = {
    "T1": {
        "name": "OMA理論・同定アルゴリズム",
        "name_en": "OMA theory and identification algorithms",
        "subtopics": {
            "T1a": "FDD・周波数領域分解",
            "T1b": "SSI・確率サブスペース",
            "T1c": "NExT・時間領域／MAC・安定化図",
        },
    },
    "T2": {
        "name": "飛行中・運用中モーダル同定",
        "name_en": "In-flight / operational modal identification",
        "subtopics": {
            "T2a": "飛行試験・フライトテスト",
            "T2b": "ホバリング・巡航・運用データ",
            "T2c": "回転中・運転中構造（ロータ等）",
        },
    },
    "T3": {
        "name": "地上GVT・EMA・励振試験",
        "name_en": "Ground GVT / EMA / excitation testing",
        "subtopics": {
            "T3a": "インパクト・シェイカ加振",
            "T3b": "プロペラ励振・PVT",
            "T3c": "FEモデル更新・検証",
        },
    },
    "T4": {
        "name": "UAV・航空機構造",
        "name_en": "UAV and aircraft structures",
        "subtopics": {
            "T4a": "マルチロータ・ドローン機体",
            "T4b": "固定翼・ヘリコプタ・ロータ",
            "T4c": "機体フレーム・アーム・翼",
        },
    },
    "T5": {
        "name": "光学・非接触計測",
        "name_en": "Optical / non-contact measurement",
        "subtopics": {
            "T5a": "モーションキャプチャ・OptiTrack",
            "T5b": "DIC・画像相関",
            "T5c": "写真測量・レーザー・その他光学",
        },
    },
    "T6": {
        "name": "土木・実験構造・SHM",
        "name_en": "Civil / laboratory structures and SHM",
        "subtopics": {
            "T6a": "橋梁・建築・インフラ",
            "T6b": "風洞・縮小モデル",
            "T6c": "長期モニタリング・損傷検知",
        },
    },
}

_OMA_CORE = (
    "operational modal", "modal analysis", "modal identification", "modal parameter",
    "experimental modal", "ground vibration test", "gvt", "oma", "fdd",
    "stochastic subspace", "ssi", "frequency domain decomposition",
    "next-", "next ", "mac", "mode shape", "natural frequency", "damping ratio",
)
_IPT_EXCLUDE = (
    "wireless power", "wpt", "ipt", "inductive charging", "rectenna", "swipt",
    "magnetic coupling", "misalignment coil", "compensation network ss",
)
_UAV_TERMS = (
    "uav", "drone", "quadcopter", "multicopter", "multirotor", "unmanned aerial",
    "aircraft", "helicopter", "rotor", "rotorcraft", "fixed-wing", "vtol", "tilt",
)
_OPTICAL_TERMS = (
    "motion capture", "optitrack", "motive", "digital image correlation", "image correlation",
    "photogrammetry", "stereophotogrammetry", "high-speed camera", "laser doppler",
    "non-contact", "vision-based", "computer vision",
)
_CIVIL_TERMS = (
    "bridge", "building", "civil", "infrastructure", "wind tunnel", "laboratory model",
    "shm", "structural health",
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

    if hit(*_IPT_EXCLUDE) and not hit(*_OMA_CORE):
        return out

    if not hit(*_OMA_CORE) and not (
        hit("vibration", "structural dynamics", "aeroelastic", "flutter")
        and hit("modal", "mode", "identification", "frequency")
    ):
        return out

    if hit("fdd", "frequency domain decomposition", "svd", "singular value decomposition"):
        out.append(("T1", "T1a"))
    elif hit("stochastic subspace", "ssi", "covariance driven", "data-driven modal"):
        out.append(("T1", "T1b"))
    elif hit("next", "ibrahim", "mac", "stabilization diagram", "mode assurance"):
        out.append(("T1", "T1c"))
    elif hit("operational modal", "modal analysis", "modal identification", "system identification"):
        out.append(("T1", "T1c"))

    if hit(
        "in-flight", "in flight", "flight test", "flying", "hover", "hovering",
        "operational modal", "in-service", "during operation", "while rotating",
    ):
        out.append(
            (
                "T2",
                "T2a"
                if hit("flight test", "flight-test", "flight experiment")
                else "T2c"
                if hit("rotor", "rotating", "rpm", "blade")
                else "T2b",
            )
        )

    if hit(
        "ground vibration", "gvt", "experimental modal", "impact hammer", "shaker",
        "hammer test", "propeller-driven", "pvt", "modal test",
    ):
        out.append(
            (
                "T3",
                "T3b" if hit("propeller", "pvt") else "T3c" if hit("finite element", "fem", "model updating") else "T3a",
            )
        )

    if hit(*_UAV_TERMS):
        out.append(
            (
                "T4",
                "T4a"
                if hit("multicopter", "multirotor", "quadcopter", "drone", "hexa", "octo")
                else "T4b"
                if hit("helicopter", "rotor", "fixed-wing", "aircraft", "vtol", "tilt")
                else "T4c",
            )
        )

    if hit(*_OPTICAL_TERMS):
        out.append(
            (
                "T5",
                "T5a"
                if hit("motion capture", "optitrack", "motive")
                else "T5b"
                if hit("digital image", "image correlation", "dic")
                else "T5c",
            )
        )

    if hit(*_CIVIL_TERMS) or hit("bridge", "building", "wind tunnel"):
        out.append(("T6", "T6a" if hit("bridge", "building", "civil") else "T6b" if "wind tunnel" in blob else "T6c"))

    if not out:
        out.append(("T1", "T1c"))

    return out
