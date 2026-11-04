"""規約集合（v0.142。docs/ruleset-foundation-v0.142.md）: 未決の場面などの扱いを決める規約の集合を識別し、対戦に渡して状態に持つための基盤。

v0.142 の規約集合は、今の挙動をそのまま固定した集合だけでした（未決の場面は今までどおり止める）。

v0.143（docs/play-policy-s2a-v0.143.md）: 利用者が採用した S2a の続行規約 5 件と、それを含む開発用の部分的な集合 ``CS-KYUURA-PLAY-S2A@1`` を加えた。今の挙動の集合
（``CS-KYUURA-CURRENT@1``。省略したときの集合）は同じ ID・版・中身のまま。続行規約は、止める理由を作る分岐の手前の照会（``continuation_for``）で引き、当てたらログ
``convention_applied``（``record_application``）を書く。5 規約の場面のほかの未決の場面は、続行側の集合でも今までどおり止める（完成したプレイ用の集合ではない）。

次のものを分けます（docs/ruleset-foundation-v0.142.md 2 章）:

- エンジンの版（``kyuura_engine.__version__``）: 処理の実装。不具合の修正・最適化はここが変わる（規約集合の版は変えない）
- 書き出しの形式の版（``serialize.FORMAT_VERSIONS``）: ``state_to_dict`` の形
- 対戦の条件のルールの組（``rules.RuleSet``）: デッキ 60 枚・サイド 6 枚などの数値。規約集合とは別のもので、規約集合はルールの組の値を持たない（二重に持たない）
- 規約集合（``ConventionSet``）: 集合 ID・版・含む規約の ID と版・内容の照合値・区分（通常・開発用・旧状態用）
- 規約（``Convention``）: 規約 ID・版・層（利用者が承認した基礎の規約・承認されていない今の挙動の記録・続行規約）・承認の状態・意味の内容

照合値は内容を識別するための SHA-256 で、署名・認証ではありません（誰が作ったかは示さない）。辞書の順序・改行・実行環境・ファイルの絶対パスに依存しない正規化した JSON から作り、
意味の内容だけを入れます（根拠の文書の場所・行番号などの説明上の参照は入れない）。同じ ID・版の内容は変えない約束を、固定した照合値（``PINNED_*``）で機械的に確かめます。

カード id・モードの名前で分岐しません。``engine.py``・``resolution/`` はこのモジュールの入口（``resolve_for_new_game``・``require_state_conventions``・``stop_without_continuation``。v0.143 から
``continuation_for``・``record_application``）だけを呼びます。
"""

from __future__ import annotations

import dataclasses
import enum
import hashlib
import json
import unicodedata
from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
from functools import lru_cache
from importlib import resources
from types import MappingProxyType
from typing import Any

from .errors import EngineError, UnsupportedError

# ---------------------------------------------------------------- 語彙

LAYER_BASELINE_USER = "baseline_user"  # 利用者が承認した指定（両モード共通の基礎集合。AGR-MODE-BASELINE-USER）
LAYER_CURRENT_BEHAVIOR = "current_behavior"  # 今の実装の挙動の記録（承認されていない仮定・簡略化を含む。採用の記録ではない）
LAYER_CONTINUATION = "continuation"  # 未決の場面を続ける規約（v0.142 は 0 件。v0.143 は S2a の 5 件。開発用の集合だけ）
LAYERS = (LAYER_BASELINE_USER, LAYER_CURRENT_BEHAVIOR, LAYER_CONTINUATION)

APPROVAL_USER_AGREED = "user_agreed"
APPROVAL_NOT_APPROVED = "not_approved"
APPROVALS = (APPROVAL_USER_AGREED, APPROVAL_NOT_APPROVED)

USAGE_STANDARD = "standard"  # 通常の対戦に使う集合
USAGE_DEVELOPMENT = "development"  # 規約がそろわない開発・検証用の集合（通常のプレイ用として完成扱いにしない）
USAGE_LEGACY = "legacy"  # 規約集合の記録がない旧状態の対応付け専用（新しい対戦には使わない）
USAGES = (USAGE_STANDARD, USAGE_DEVELOPMENT, USAGE_LEGACY)

# 集合の完全性の主張。この版の集合はどれも未決の場面で止まる（"halts_at_undecided"。v0.143 の続行側の集合も、5 規約の場面のほかでは止まる）。"play_complete"（止まらずに対戦を終えられる集合）を主張する集合は、完全性の判定が
# 未実装なので受け付けない（``completeness_problems`` が拡張点）
COMPLETENESS_HALTS = "halts_at_undecided"
COMPLETENESS_PLAY = "play_complete"
COMPLETENESS = (COMPLETENESS_HALTS, COMPLETENESS_PLAY)

INVALID_CONVENTION_SET_CODE = "INVALID_CONVENTION_SET"  # new_game に渡した規約集合の構成の誤り（対戦を始めない）
UNSUPPORTED_CONVENTION_SET_CODE = "UNSUPPORTED_CONVENTION_SET"  # 状態の規約集合を、この版が扱えない・登録の内容と合わない（推測で続けない）

# 照合値の領域の区切り（規約と集合の照合値が同じ JSON から同じ値にならないようにする）
_CONVENTION_DOMAIN = b"kyuura-convention/1\n"
_SET_DOMAIN = b"kyuura-convention-set/1\n"

# 意味の内容に入れない、登録の記録の項目（根拠の文書の場所・kyuura の記録の場所・画像の照合の記録。説明上の参照）
REFERENCE_FIELDS = frozenset({"source", "document", "kyuura_record", "print_check"})


class ConventionSetError(EngineError):
    """渡した規約集合の構成の誤り（未知・重複・競合・依存の不足・ID と版と内容の不一致・未実装・区分）。対戦を始めない。"""

    def __init__(self, problems: list[str]):
        super().__init__(INVALID_CONVENTION_SET_CODE, "; ".join(problems))
        self.problems = list(problems)


# ---------------------------------------------------------------- 正規化と照合値


def canonical(value: Any) -> Any:
    """照合値のための正規化。文字列は NFC・改行を LF に、並び（tuple・list）は list、辞書のキーは文字列だけ（順序は書き出しで並べる）、列挙は値、dataclass は項目の辞書。
    浮動小数点数・その他の型は受け付けない（実行環境で表し方が変わりうる）。"""
    if isinstance(value, bool) or value is None or isinstance(value, int):
        return value
    if isinstance(value, str):
        return unicodedata.normalize("NFC", value.replace("\r\n", "\n").replace("\r", "\n"))
    if isinstance(value, enum.Enum):
        return canonical(value.value)
    if isinstance(value, (tuple, list)):
        return [canonical(v) for v in value]
    if isinstance(value, Mapping):
        if not all(isinstance(k, str) for k in value):
            raise TypeError("照合値の辞書のキーは文字列だけ")
        return {canonical(k): canonical(v) for k, v in value.items()}
    if dataclasses.is_dataclass(value) and not isinstance(value, type):
        return canonical({f.name: getattr(value, f.name) for f in dataclasses.fields(value)})
    raise TypeError(f"照合値に入れられない型 {type(value).__name__}")


def canonical_bytes(value: Any) -> bytes:
    return json.dumps(canonical(value), ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")


def _digest(domain: bytes, value: Any) -> str:
    return "sha256:" + hashlib.sha256(domain + canonical_bytes(value)).hexdigest()


# ---------------------------------------------------------------- 規約と集合


@dataclass(frozen=True)
class Convention:
    """規約 1 つの定義。意味の内容は ``content``（直接の値）か ``source``（エンジンの登録・同梱の記録から読む内容の名前。``CONTENT_SOURCES``）のどちらか。

    - ``requires``・``conflicts``: ほかの規約の (ID, 版)。``requires`` の不足・``conflicts`` の同居は構成の誤り
    - ``scenes``: 続行規約が当たる場面（停止の方針の台帳の場面 ID。``scene_index``）。基礎・今の挙動の記録は空
    - ``references``: 根拠の文書など（照合値に入れない）"""

    id: str
    version: int
    layer: str
    approval: str
    statement: str
    content: Mapping[str, Any] | None = None
    source: str | None = None
    requires: tuple[tuple[str, int], ...] = ()
    conflicts: tuple[tuple[str, int], ...] = ()
    scenes: tuple[str, ...] = ()
    references: tuple[str, ...] = ()


@dataclass(frozen=True)
class ConventionSet:
    """規約集合の定義。``members`` は含む規約の (ID, 版)（並びの順は意味を持たない。照合値は ID の順で作る）。``description`` は照合値に入れない説明。"""

    id: str
    version: int
    usage: str
    members: tuple[tuple[str, int], ...]
    completeness: str = COMPLETENESS_HALTS
    description: str = ""


@dataclass(frozen=True)
class ConventionSetIdentity:
    """状態に持つ規約集合の識別（変えられない値だけ。呼び出し元のオブジェクト・登録表を後から変えても、この値は変わらない）。``members`` は (規約 ID, 版, 照合値) を ID の順に。"""

    set_id: str
    version: int
    digest: str
    usage: str
    completeness: str
    members: tuple[tuple[str, int, str], ...]

    @property
    def key(self) -> tuple[str, int]:
        return self.set_id, self.version

    def record(self) -> dict[str, Any]:
        """書き出し・観測の形（全員に見える。秘密の情報は入らない）。"""
        return {"id": self.set_id, "version": self.version, "digest": self.digest, "usage": self.usage, "completeness": self.completeness,
                "members": [{"id": m, "version": v, "digest": d} for m, v, d in self.members]}


@dataclass(frozen=True)
class UnrecordedConventions:
    """規約集合の記録がない状態（v0.141 までの状態の写し。``GameState.__setstate__`` が、項目がないときだけ置く）。どの版で作った状態か・どの規約で処理したかを、この値から
    推測しない（``require_state_conventions`` が旧状態として扱える条件を確かめ、旧状態用の集合に対応付けるか拒否する）。"""


UNRECORDED = UnrecordedConventions()


# ---------------------------------------------------------------- 登録（この版の規約・集合）

CURRENT_SET_ID = "CS-KYUURA-CURRENT"
LEGACY_SET_ID = "CS-KYUURA-LEGACY-UNRECORDED"

# 利用者が承認した指定（基礎集合）。規約 ID は既存の利用者指定の ID をそのまま使う（新しい ID を作らない）。内容はエンジンの登録の記録から読む（``_user_registrations``）
USER_CONVENTION_IDS = (
    "USER-BIRTHDAY-COIN-ONLY", "USER-SPOKEN-CONDITION-IGNORED", "USER-QUIZ-HEIGHT-OFFICIAL-ZUKAN", "USER-SWAP-OWNERSHIP-RECEIVER",
    "USER-BILINGUAL-NAME-JAPANESE", "USER-MIND-GAMES-OPTIONAL-BEFORE-COST", "USER-MOUNTAIN-CRUSH-MILL-UP-TO-DECK", "USER-DESTRUCTIVE-FIRE-DECLARE-ORDER-UP-TO",
    "USER-SUDDEN-DEATH-OWNERSHIP-RESET", "USER-PRIZE-ORDER-ALWAYS-CHOSEN", "USER-PRIZE-ORDER-PER-PLAYER",
)
CURRENT_BEHAVIOR_ID = "CB-IMPLEMENTATION-ASSUMPTIONS"

_USER_STATEMENT = "利用者が承認した指定（対象・範囲は登録の記録のまま。ほかのカード・場面へ広げない）。公式の裁定・kyuura の研究上の解決ではない"
_CB_STATEMENT = ("この版のエンジンが実装している、利用者の承認のない実装上の仮定・正規化・簡略化・データの訂正の記録（実装上の仮定の一覧の項目）。今の挙動の記録で、承認・採用の記録"
                 "ではない（DEC-BASELINE-NONUSER・DEC-BASELINE-CENSUS・DEC-CARD-DATA-CORRECTIONS は未決のまま）")

CONVENTIONS: Mapping[tuple[str, int], Convention] = MappingProxyType({
    (c.id, c.version): c for c in (
        *(Convention(uid, 1, LAYER_BASELINE_USER, APPROVAL_USER_AGREED, _USER_STATEMENT, source="user_registrations",
                     references=("docs/stop-policy-classification.json conventions", "docs/ruleset-mode-design.md 4.2 節")) for uid in USER_CONVENTION_IDS),
        Convention(CURRENT_BEHAVIOR_ID, 1, LAYER_CURRENT_BEHAVIOR, APPROVAL_NOT_APPROVED, _CB_STATEMENT, source="current_behavior_records",
                   references=("docs/implementation-assumptions.json items", "kyuura_engine/data/convention_records.json")),
    )
})

_CURRENT_MEMBERS = tuple((uid, 1) for uid in USER_CONVENTION_IDS) + ((CURRENT_BEHAVIOR_ID, 1),)
SETS: Mapping[tuple[str, int], ConventionSet] = MappingProxyType({
    (s.id, s.version): s for s in (
        ConventionSet(CURRENT_SET_ID, 1, USAGE_STANDARD, _CURRENT_MEMBERS,
                      description="v0.142 の時点の今の挙動を固定した集合（利用者の指定 11 と、承認のない今の挙動の記録）。未決の場面では止める。プレイ用の続行規約はない"),
        ConventionSet(LEGACY_SET_ID, 1, USAGE_LEGACY, _CURRENT_MEMBERS,
                      description="規約集合の記録がない旧状態（v0.141 までの状態の写し）を、この版のエンジンの処理で扱うための固定の集合。過去の版の挙動を再現するとは主張しない"),
    )
})
DEFAULT_SET = (CURRENT_SET_ID, 1)

# ---------------------------------------------------------------- v0.143: S2a の続行規約（docs/play-policy-s2a-v0.143.md）
#
# 利用者の採用（2026-11-04「5規約をまとめて採用し、S2a-0〜4を一つの実装タスクとして進める案を採用します。」と、その指示の具体的な仕様）。公式の裁定・エラッタ・kyuura の研究上の
# 解決ではない（研究上の未解決は未解決のまま）。今の挙動の集合（CS-KYUURA-CURRENT@1）には入れず、開発用の部分的な集合 CS-KYUURA-PLAY-S2A@1 だけに入れる。意味の内容
# （``content``）は場面ごとの処理の決め方で、照合値に入る。根拠の文書は ``references``（照合値に入れない）

S2A_SET_ID = "CS-KYUURA-PLAY-S2A"
S2A_ADOPTION = "利用者の採用（2026-11-04。S2a の 5 規約を一組として採用）。公式の裁定・エラッタ・kyuura の研究上の解決ではない"
S2A_REFERENCES = ("docs/play-policy-s2a-v0.143.md", "docs/play-policy-s2a-spec.md")

MULLIGAN_COUNT_ID = "PC-SETUP-MULLIGAN-COUNT"
PLAY_AS_POKEMON_ID = "PC-SETUP-PLAY-AS-POKEMON"
SIDE_ORDER_ID = "PC-CHECK-SIDE-ORDER"
COIN_COUNT_SHORT_ID = "PC-COIN-COUNT-SHORT"
KO_POINT_ID = "PC-CHECK-KO-POINT"

_S2A_CONVENTIONS = (
    Convention(MULLIGAN_COUNT_ID, 1, LAYER_CONTINUATION, APPROVAL_USER_AGREED,
               "準備の切り直しを回ごとに数え、片方のプレイヤーだけが切り直した回 1 回ごとに、もう一方のプレイヤーに補償 1 回（山札から 0〜2 枚を、補償を受けるプレイヤーが選ぶ）を与える。"
               "両方のプレイヤーが切り直した回は数えない。補償はサイドを置いたあと、ジャンケンの前",
               content={"adoption": S2A_ADOPTION,
                        "applies_when": "準備（最初の対戦・サドン・デスの延長戦の区間）の切り直しの回の並びに、両方の回と片方だけの回が両方ある",
                        "count": "片方だけの回の数（両方の回は数えない）", "per_compensation": "DrawMulliganCards 1 回（0〜rules.mulligan_draw_max_per_mulligan 枚。山札の枚数まで）",
                        "chooser": "補償を受けるプレイヤー", "timing": "サイドを置いたあと、ジャンケンの前（今の補償と同じ）",
                        "unchanged": ["両方の回しかない切り直し（どちらも引かない）", "片方だけの回しかない切り直し（今の補償）", "解決済みの初手・補償の処理"]},
               scenes=("UNRESOLVED_MULLIGAN_COMPENSATION#initial-setup", "UNRESOLVED_MULLIGAN_COMPENSATION#sudden-death-segment"), references=S2A_REFERENCES),
    Convention(PLAY_AS_POKEMON_ID, 1, LAYER_CONTINUATION, APPROVAL_USER_AGREED,
               "準備の切り直しの判定と最初のポケモンの配置では、ポケモンとして場に出せるトレーナー（登録の型で識別する）を、たねポケモンカードとして数えない。ほかにたねポケモンカード・"
               "ベイビィポケモンカードがない手札は切り直す。最初のポケモンに選んだら、規約による不正な操作として拒否する",
               content={"adoption": S2A_ADOPTION,
                        "identification": "効果の登録の型 PlayAsPokemon（effects.play_as_pokemon_in_hand が見る、ポケモンとして場に出せるトレーナー）。カード ID では分けない",
                        "applies_when": ["準備（最初の対戦・延長戦の区間）で、たね・ベイビィのない手札に対象のカードがある", "準備の PlaceStartingPokemon で対象のカードを選んだ"],
                        "mulligan": "たね・ベイビィのない手札として、今の切り直しと同じく切り直す（回に数える）",
                        "placement": "IllegalActionError NOT_BASIC_POKEMON（入力の状態・乱数・ログを変えない。未解決の停止とは区別する）",
                        "unchanged": ["対戦が始まってからベンチに出す処理", "ベイビィの初手の規則（GR-2000-P308-BABY-SETUP）", "たね・ベイビィもある手札（切り直さない）"]},
               scenes=("UNRESOLVED_PLAY_AS_POKEMON_SETUP#initial-setup", "UNRESOLVED_PLAY_AS_POKEMON_SETUP#sudden-death-segment",
                       "UNRESOLVED_PLAY_AS_POKEMON_SETUP#setup-placement"), references=S2A_REFERENCES),
    Convention(SIDE_ORDER_ID, 1, LAYER_CONTINUATION, APPROVAL_USER_AGREED,
               "ポケモンチェックの同じ段階で両方のプレイヤーが同じ種類のコイン（ねむりのコイン・くろこげマーカーのコイン）を投げるときは、番を終えたプレイヤーの場から先に、次に相手の場の"
               "順に投げて処理する。それぞれの場はバトル場 → ベンチの並び。ねむりのコインは 1 枚ずつ結果を反映する。順番を選ぶ決定は出さない",
               content={"adoption": S2A_ADOPTION,
                        "applies_when": ["ポケモンチェックの 3 で、両方の対戦ポケモンがねむり", "ポケモンチェックの 1 で、両方のプレイヤーの場にくろこげマーカーののったポケモンがある"],
                        "order": "番を終えたプレイヤー（ポケモンチェックの直前の番のプレイヤー）→ 相手。それぞれの場はバトル場 → ベンチ",
                        "sleep_reflection": "1 枚（1 匹）ずつ結果を反映する。コインの枚数は投げる直前の場で決める",
                        "unchanged": ["ポケモンチェックの段階の順序", "片方だけが投げる場合", "きのみの順番（BY1）", "くろこげマーカーのコインの技術的上限",
                                      "両方のきぜつ", "一般の同時効果", "サイドを取る順番（採用済みの利用者の指定）"]},
               scenes=("UNRESOLVED_POKEMON_CHECK_SLEEP_COIN_ORDER", "UNRESOLVED_POKEMON_CHECK_CHAR_COIN_ORDER"), references=S2A_REFERENCES),
    Convention(COIN_COUNT_SHORT_ID, 1, LAYER_CONTINUATION, APPROVAL_USER_AGREED,
               "共通の数量処理のチェック地点で、コインの「おもて」の数で決まった枚数 H が、その時点の対象の枚数 N より多いときは、対象 N 枚をすべて処理する（min(H, N) 枚）。H は丸めずに"
               "ログに残し、コインを途中で打ち切らない。選ぶ人・対象の判定・防護と無効化は今の処理のまま",
               content={"adoption": S2A_ADOPTION,
                        "applies_when": "チェック地点（interruption.check_quantity）で H > N（N = 0 をふくむ）。ファイヤーのドライアップ（DU1）・怪電波マシーン（TW1）の要素だけ",
                        "process": "min(H, N) 枚", "coins": "H は実際のコインの結果のまま（ナツメのESPのやり直しは最後に確定した並び）",
                        "unchanged": ["使う前・宣言の前に決まる使用条件（TW2 など）", "選んだ対象で起こる別の未決事項", "途中停止した状態の再開",
                                      "ほかのカードへの不足の処理の一般化", "怪電波マシーンを使ったら番が終わる"]},
               scenes=("UNRESOLVED_DRY_UP_WATER_ENERGY_SHORT", "UNRESOLVED_THOUGHT_WAVE_MACHINE_ENERGY_SHORT"), references=S2A_REFERENCES),
    Convention(KO_POINT_ID, 1, LAYER_CONTINUATION, APPROVAL_USER_AGREED,
               "ポケモンチェックでは、1 の「指示されたこと」（くろこげマーカーのコイン・悪エネルギーの効果・くろこげマーカーのダメージ・きのみ）と 2 の「どく」のダメージを終えてから、"
               "1 回だけきぜつを判定する。1 のあとに HP 以上のダメージになったポケモンも、その判定まで場に残り、2 のどくのダメージを受ける",
               content={"adoption": S2A_ADOPTION,
                        "applies_when": "ポケモンチェックの 1 のあとに HP 以上のポケモンがいて、1 と 2 のあいだに判定する読み方と結果が変わる（PK1）",
                        "judgement": "2 のあとに 1 回（今の処理の順のまま）",
                        "unchanged": ["両方のきぜつ", "SC1", "AL1・AL3", "PO1〜PO3", "KA1・VS1・DE1", "BY1"]},
               scenes=("UNRESOLVED_POKEMON_CHECK_MID_KNOCKOUT",), references=S2A_REFERENCES),
)
S2A_MEMBERS = tuple((c.id, c.version) for c in _S2A_CONVENTIONS)

CONVENTIONS = MappingProxyType({**CONVENTIONS, **{(c.id, c.version): c for c in _S2A_CONVENTIONS}})
SETS = MappingProxyType({
    **SETS,
    (S2A_SET_ID, 1): ConventionSet(S2A_SET_ID, 1, USAGE_DEVELOPMENT, _CURRENT_MEMBERS + S2A_MEMBERS,
                                   description=("v0.143 の開発用の部分的な集合: 今の挙動の集合の規約 12 件と、S2a の続行規約 5 件。5 規約の場面だけを続け、ほかの未決の場面では今の停止"
                                                "コードで止める（すべての未決の場面で止まらない完成したプレイ用の集合ではない）")),
})

# ---------------------------------------------------------------- v0.145: ［ポイズンミスト］とどくの量の続行規約（docs/poison-mist-play-po-v0.145.md）
#
# 利用者の採用（2026-11-05「方針を採用します。」と、その指示の採用仕様。仕様案は docs/poison-mist-play-policy-spec.md）。公式の裁定・エラッタ・kyuura の研究上の解決ではない
# （PO1〜PO3 は研究上の未解決のまま）。今の挙動の集合・S2a の集合には入れず、新しい開発用の部分的な集合 CS-KYUURA-PLAY-PO@1 だけに入れる

PO_SET_ID = "CS-KYUURA-PLAY-PO"
PO_ADOPTION = "利用者の採用（2026-11-05。PO1〜PO3 の続行規約 3 件を、仕様案の範囲で採用）。公式の裁定・エラッタ・kyuura の研究上の解決ではない"
PO_REFERENCES = ("docs/poison-mist-play-po-v0.145.md", "docs/poison-mist-play-policy-spec.md")

POISON_AMOUNT_ORDER_ID = "PC-POISON-AMOUNT-ORDER"
POISON_MIST_TARGETS_ID = "PC-POISON-MIST-TARGETS"
POISON_MIST_SOURCE_LEFT_ID = "PC-POISON-MIST-SOURCE-LEFT"

_PO_CONVENTIONS = (
    Convention(POISON_AMOUNT_ORDER_ID, 1, LAYER_CONTINUATION, APPROVAL_USER_AGREED,
               "ポケモンチェックの「どく」のダメージは、ポケモンチェックの時点で、どく状態の性質（特殊などくの決まった量、またはダメージカウンターの数にかける数）→ ［ポイズンミスト］"
               "（はたらけば量をその数にする）→ 鋼エネルギー（受けるダメージの「-10」。0 より小さくしない）の順に当てはめて決める",
               content={"adoption": PO_ADOPTION,
                        "applies_when": "どくの量を変える効果の当てはめる順番（effects._poison_orders の並べかえ）で量が変わる（PO1）",
                        "order": ["どく状態の性質（特殊などくの量・かける数）", "［ポイズンミスト］", "鋼エネルギー"],
                        "time": "ポケモンチェックの 2 の「どく」の時点（1 のあとの場）",
                        "floor": "鋼エネルギーの「-10」は 0 より小さくしない（energy_received_damage のまま）",
                        "unchanged": ["TP3（違うどく状態への上書き）", "キョウのどくの順番", "KA1（受けるダメージを変える特殊能力）", "PX1",
                                      "性質の 2 つ（特殊などくの量とかける数）のあいだの順番（今の写しでは同時に持たない）", "量が 1 つに決まる組の量・記録"]},
               scenes=("UNRESOLVED_POISON_CHANGE_ORDER",), references=PO_REFERENCES),
    Convention(POISON_MIST_TARGETS_ID, 1, LAYER_CONTINUATION, APPROVAL_USER_AGREED,
               "［ポイズンミスト］の効果は、ポケモンチェックの時点でどく状態のすべてのポケモン（お互いの場）が受ける「どく」のダメージに当てはまる。力を使った時点でどく状態だったかは問わない",
               content={"adoption": PO_ADOPTION,
                        "applies_when": "力を使う前からどく状態だったポケモン（PoisonMist.poisoned_before）に当てはめるかで量が変わる（PO2）",
                        "targets": "ポケモンチェックの時点でどく状態のポケモン（使ったあとにどく状態になった・回復した・またどく状態になったポケモンも、時点の状態で決める）",
                        "unchanged": ["どく状態になるか自体の未決の停止", "記録 poisoned_before（状態の形）", "量が 1 つに決まる組の量・記録", "2 つ以上の記録は足さない（v0.119 のまま）"]},
               scenes=("UNRESOLVED_POISON_MIST_EARLIER_POISON",), references=PO_REFERENCES),
    Convention(POISON_MIST_SOURCE_LEFT_ID, 1, LAYER_CONTINUATION, APPROVAL_USER_AGREED,
               "［ポイズンミスト］を使ったポケモン（記録の発生源の場の番号）が場をはなれたら、その発生源の記録の効果は終わる（そのあとのポケモンチェックで当てはめない）。発生源が場に"
               "いるまま特殊能力が消えた記録（#power-lost）は対象にしない",
               content={"adoption": PO_ADOPTION,
                        "applies_when": "中断のある記録の発生源の場の番号のポケモンが、ポケモンチェックの時点で場にいない（PO3 の #source-left）",
                        "left_play": "場の番号のポケモンが場にいない（きぜつ・手札・山札・トラッシュなど）。バトル場とベンチのあいだの移動・進化・退化・へんしんは場をはなれていない",
                        "per_source": "記録（発生源）ごとに判断し、場にいない発生源の記録だけを当てはめない。ほかの発生源の記録は消さない",
                        "state": "記録・中断の印は変えない（量の判断で使わないだけ。使ったプレイヤーの次の番の始めに今までどおり消える）",
                        "unchanged": ["#power-lost（かがくへんかガス・退化・へんしんなどで発生源が場にいるまま力が消えた記録。今の停止のまま）", "ほかの特殊能力・持続する効果の発生源",
                                      "効果の重複・加算・最大値（新しく決めない）", "量が 1 つに決まる組の量・記録"]},
               scenes=("UNRESOLVED_POISON_MIST_SOURCE#source-left",), references=PO_REFERENCES),
)
PO_MEMBERS = tuple((c.id, c.version) for c in _PO_CONVENTIONS)

CONVENTIONS = MappingProxyType({**CONVENTIONS, **{(c.id, c.version): c for c in _PO_CONVENTIONS}})
SETS = MappingProxyType({
    **SETS,
    (PO_SET_ID, 1): ConventionSet(PO_SET_ID, 1, USAGE_DEVELOPMENT, _CURRENT_MEMBERS + S2A_MEMBERS + PO_MEMBERS,
                                  description=("v0.145 の開発用の部分的な集合: 今の挙動の集合の規約 12 件・S2a の続行規約 5 件と、［ポイズンミスト］とどくの量の続行規約 3 件。8 規約の場面"
                                               "だけを続け、ほかの未決の場面（#power-lost をふくむ）では今の停止コードで止める（完成したプレイ用の集合ではない）")),
})

# この版のエンジンが処理を持つ続行規約（``Registry.implemented_continuations``）
IMPLEMENTED_CONTINUATIONS = frozenset(S2A_MEMBERS + PO_MEMBERS)
# 形式 34 までの書き出し（規約集合の項目がない）に書いてよい集合: 記録のない状態の意味（その版のエンジンの今の挙動）と同じ意味の集合だけ
IMPLICIT_IN_OLD_FORMATS = frozenset({(CURRENT_SET_ID, 1), (LEGACY_SET_ID, 1)})

# 同じ ID・版の内容を変えない約束（変えたら版を上げ、ここに新しい値を加える。古い値は書き換えない）。tests/test_conventions_v0_142.py が、計算した値と同じことを確かめる
PINNED_CONVENTION_DIGESTS: Mapping[tuple[str, int], str] = MappingProxyType({
    ("USER-BIRTHDAY-COIN-ONLY", 1): "sha256:b54ad58f9d604c45e7385a32323dc54ff5c3e002687ea62c18a4b60e953fbb7c",
    ("USER-SPOKEN-CONDITION-IGNORED", 1): "sha256:88778bc6f7c4b9635cb80efeacda36293923e80122490bf1af67c49a76dcf97c",
    ("USER-QUIZ-HEIGHT-OFFICIAL-ZUKAN", 1): "sha256:8e217be7ac7d45e6ee5fbc036e02ba70fbef14bb19c35edebc7dd85efbdf4073",
    ("USER-SWAP-OWNERSHIP-RECEIVER", 1): "sha256:158dc036912409eb6825d11840e02dffdd3c8d6f2bb369c888b501e7ec1aaea3",
    ("USER-BILINGUAL-NAME-JAPANESE", 1): "sha256:4a2019d0466a30bcebab4b3f4b2f444bdaf560d3fd073f08a473ba76092e599e",
    ("USER-MIND-GAMES-OPTIONAL-BEFORE-COST", 1): "sha256:a81654749122531ab0952d14468dcacba62e7b32ced88fd33fc6ac41ef841fcb",
    ("USER-MOUNTAIN-CRUSH-MILL-UP-TO-DECK", 1): "sha256:c2de0518d7fcc05924cac85874404f1ae35f462613e449085caa0b838474c14b",
    ("USER-DESTRUCTIVE-FIRE-DECLARE-ORDER-UP-TO", 1): "sha256:c7b5a46b43024a3c4d4deeec0c82dbe0353379af9471ae51896824627044e611",
    ("USER-SUDDEN-DEATH-OWNERSHIP-RESET", 1): "sha256:7b3b66feb0a5147e1a6d64d9ec5092cc1c81ff820c1d0e5e9310e62990cc97ab",
    ("USER-PRIZE-ORDER-ALWAYS-CHOSEN", 1): "sha256:1b175a1760073605da85e31de2bf2310449b862db9bc257a93ffdd8776415785",
    ("USER-PRIZE-ORDER-PER-PLAYER", 1): "sha256:4a1eed17ff7d90234ce68bb92b8b862cc0e5d32478849553453a3e26104bac60",
    ("CB-IMPLEMENTATION-ASSUMPTIONS", 1): "sha256:347aadfadcc21580ceb1fbf047d66a5d10f92be930499370ae6d3f6534991a6a",
    # v0.143: S2a の続行規約（利用者の採用。2026-11-04）
    ("PC-SETUP-MULLIGAN-COUNT", 1): "sha256:8f6191a3dab82e4da776f07e7bb0a7b4dde299118330e363f4ffe6dbeb8e8867",
    ("PC-SETUP-PLAY-AS-POKEMON", 1): "sha256:38265187c44184466d8b476092a0df05aa9967fd6f98ebf67aafc67d5535e20c",
    ("PC-CHECK-SIDE-ORDER", 1): "sha256:c8f78ccaf484c12430fdc48e57bbb1f05a0c8d49207c364e0507380054292ba4",
    ("PC-COIN-COUNT-SHORT", 1): "sha256:6a0554ff17e94934eb5f81aff1533ef5b600b4e59f69a9ca2abd24d3055492c5",
    ("PC-CHECK-KO-POINT", 1): "sha256:7a91e7fe7f72e35828edb97e2c5661f6d6186b8607584c86631164c69fa8d2ad",
    # v0.145: PO の続行規約（利用者の採用。2026-11-05）
    ("PC-POISON-AMOUNT-ORDER", 1): "sha256:daf99cffee744cb70043c21f67702ebe6bef5fde1911e3e82ffeb19d3535e5aa",
    ("PC-POISON-MIST-TARGETS", 1): "sha256:e5e48dd17d5af226ae38f3004a21ae3bf9fd2639b1454f00a1a09f30d6d021d5",
    ("PC-POISON-MIST-SOURCE-LEFT", 1): "sha256:dbf6b8e8bae49b5c884446e367abd9a861d71f701ec420cc8feedfaf8b4609e6",
})
PINNED_SET_DIGESTS: Mapping[tuple[str, int], str] = MappingProxyType({
    ("CS-KYUURA-CURRENT", 1): "sha256:9a9b95c689d86fa01a5b710984560efda3c08f4dbf1d7c6218094ac8666f3cee",
    ("CS-KYUURA-LEGACY-UNRECORDED", 1): "sha256:abf39e6d87755507a9169537608596246f4ed9a9bf0c2e8794ffa44a97742407",
    ("CS-KYUURA-PLAY-S2A", 1): "sha256:b317a3f050206577bff35ac05c87fdb4224ee28c6c0222e4e7f8460b5e9410c4",  # v0.143: 開発用の部分的な集合
    ("CS-KYUURA-PLAY-PO", 1): "sha256:06d512194feee1857319f0c765ab2162d5259e4519895ed057d176d15fc43528",  # v0.145: 開発用の部分的な集合
})


# ---------------------------------------------------------------- 内容の読み出し


def _record_content(record) -> dict[str, Any]:
    """登録の記録（frozen dataclass）の意味の内容（説明上の参照 ``REFERENCE_FIELDS`` を除く）。簡略ルールの指定の文（``instruction`` の property）は加える。"""
    data = {f.name: getattr(record, f.name) for f in dataclasses.fields(record) if f.name not in REFERENCE_FIELDS}
    instruction = getattr(type(record), "instruction", None)
    if isinstance(instruction, property):
        data["instruction"] = record.instruction
    return data


def user_registrations() -> dict[str, list[dict[str, Any]]]:
    """利用者の指定の登録（エンジンがいつも当てはめる記録）を、指定の ID ごとに集める。``{指定 ID: [{"registry", "key", "record"}...]}``（キーの順）。"""
    from . import decisions, effects, sudden_death

    out: dict[str, list[dict[str, Any]]] = {}

    def add(rule_id: str, registry: str, key: str, record) -> None:
        out.setdefault(rule_id, []).append({"registry": registry, "key": key, "record": _record_content(record)})

    for name in ("USER_SIMPLIFICATIONS", "USER_SPECIFIED_REFERENCES", "USER_SPECIFIED_RULES", "USER_SPECIFIED_NAMES"):
        for key, record in sorted(getattr(effects, name).items()):
            add(record.rule, f"effects.{name}", key, record)
    for record in decisions.USER_PRIZE_ORDER_RULES:
        add(record.id, "decisions.USER_PRIZE_ORDER_RULES", record.id, record)
    segment = sudden_death.USER_SUDDEN_DEATH_OWNERSHIP_RESET
    add(segment.id, "sudden_death.USER_SUDDEN_DEATH_OWNERSHIP_RESET", segment.id, segment)
    return out


@lru_cache(maxsize=1)
def _bundled_records() -> Mapping[str, Any]:
    """同梱の記録（``kyuura_engine/data/convention_records.json``。``scripts/build_convention_records.py`` が台帳から作る。手で直さない）。"""
    text = resources.files(__package__).joinpath("data/convention_records.json").read_text(encoding="utf-8")
    return json.loads(text)


def current_behavior_records() -> dict[str, Any]:
    return {"items": _bundled_records()["current_behavior"]["items"]}


def scene_index() -> Mapping[str, Any]:
    """停止の方針の台帳の場面（事例のあるコードは事例）と停止コードの対応（同梱の記録）。``{"scenes": [...], "codes": {停止コード: [場面 ID...]}}``。"""
    return _bundled_records()["scene_index"]


CONTENT_SOURCES: Mapping[str, Callable[[Convention], Any]] = MappingProxyType({
    "user_registrations": lambda c: {"registrations": user_registrations().get(c.id, [])},
    "current_behavior_records": lambda c: current_behavior_records(),
})


def convention_payload(convention: Convention, sources: Mapping[str, Callable[[Convention], Any]] = CONTENT_SOURCES) -> dict[str, Any]:
    """照合値に入れる規約の意味の内容（``references`` を除く）。"""
    if (convention.content is None) == (convention.source is None):
        raise ValueError(f"規約 {convention.id} は content と source のどちらか 1 つを持つ")
    content = convention.content if convention.source is None else sources[convention.source](convention)
    return {"id": convention.id, "version": convention.version, "layer": convention.layer, "approval": convention.approval, "statement": convention.statement,
            "content": content, "requires": sorted([list(r) for r in convention.requires]), "conflicts": sorted([list(r) for r in convention.conflicts]),
            "scenes": sorted(convention.scenes)}


def convention_digest(convention: Convention, sources: Mapping[str, Callable[[Convention], Any]] = CONTENT_SOURCES) -> str:
    return _digest(_CONVENTION_DOMAIN, convention_payload(convention, sources))


def set_payload(spec: ConventionSet, member_digests: Mapping[tuple[str, int], str]) -> dict[str, Any]:
    return {"id": spec.id, "version": spec.version, "usage": spec.usage, "completeness": spec.completeness,
            "members": sorted([[m, v, member_digests[(m, v)]] for m, v in spec.members])}


# ---------------------------------------------------------------- 登録表（試験では別の登録表を作れる）


@dataclass(frozen=True)
class Registry:
    """規約と集合の登録表。``implemented_continuations`` は、この版のエンジンが処理を持つ続行規約（v0.143: S2a の 5 件）。``engine_baseline`` は、エンジンがいつも当てはめる基礎の規約の ID
    （集合から外せない）。"""

    conventions: Mapping[tuple[str, int], Convention]
    sets: Mapping[tuple[str, int], ConventionSet]
    pinned_conventions: Mapping[tuple[str, int], str]
    pinned_sets: Mapping[tuple[str, int], str]
    sources: Mapping[str, Callable[[Convention], Any]] = CONTENT_SOURCES
    implemented_continuations: frozenset[tuple[str, int]] = frozenset()
    engine_baseline: Callable[[], frozenset[str]] = field(default=lambda: frozenset(user_registrations()))


DEFAULT_REGISTRY = Registry(CONVENTIONS, SETS, PINNED_CONVENTION_DIGESTS, PINNED_SET_DIGESTS, implemented_continuations=IMPLEMENTED_CONTINUATIONS)


def implemented(convention: Convention, registry: Registry) -> bool:
    """この版のエンジンが、この規約の処理を持つか。基礎の規約は登録の記録があること、今の挙動の記録は同梱の記録があること、続行規約は登録表の ``implemented_continuations``
    にあること（v0.143 の登録表は S2a の 5 件。``IMPLEMENTED_CONTINUATIONS``）。"""
    if convention.layer == LAYER_BASELINE_USER:
        return convention.source == "user_registrations" and convention.id in registry.engine_baseline()
    if convention.layer == LAYER_CURRENT_BEHAVIOR:
        return convention.source == "current_behavior_records"
    return (convention.id, convention.version) in registry.implemented_continuations


def completeness_problems(spec: ConventionSet, registry: Registry) -> list[str]:
    """集合の完全性の主張の確かめ（拡張点）。この版は「止まらずに対戦を終えられる」ことの判定を実装していないので、その主張（``COMPLETENESS_PLAY``）は受け付けない。"""
    if spec.completeness == COMPLETENESS_PLAY:
        return ["止まらずに対戦を終えられる集合（play_complete）の完全性の判定は、この版では実装していない（主張できない）"]
    return []


def _is_key(value) -> bool:
    return (isinstance(value, tuple) and len(value) == 2 and isinstance(value[0], str) and isinstance(value[1], int) and not isinstance(value[1], bool)
            and value[1] >= 1)


def validate(spec: ConventionSet, registry: Registry = DEFAULT_REGISTRY, *, for_new_game: bool = True) -> list[str]:
    """規約集合の構成の問題（なければ空）。対戦を始める前・状態を受け取ったときに確かめる（docs/ruleset-foundation-v0.142.md 5 章）。"""
    if not isinstance(spec, ConventionSet):
        return [f"規約集合は ConventionSet で渡す（{type(spec).__name__} は受け付けない）"]
    problems: list[str] = []
    if not (isinstance(spec.id, str) and spec.id and _is_key((spec.id, spec.version))):
        return ["規約集合の ID（空でない文字列）と版（1 以上の整数）がない"]
    if spec.usage not in USAGES:
        problems.append(f"規約集合の区分 {spec.usage!r} を知らない（{USAGES}）")
    if spec.completeness not in COMPLETENESS:
        problems.append(f"規約集合の完全性の主張 {spec.completeness!r} を知らない（{COMPLETENESS}）")
    if for_new_game and spec.usage == USAGE_LEGACY:
        problems.append("旧状態用の集合は、記録のない旧状態の対応付けだけに使う（新しい対戦には使わない）")
    if not (isinstance(spec.members, tuple) and all(_is_key(m) for m in spec.members)):
        return [*problems, "含む規約は (ID, 版) の並び（tuple）で渡す"]
    ids = [m for m, _ in spec.members]
    for duplicated in sorted({m for m in ids if ids.count(m) > 1}):
        problems.append(f"規約 {duplicated} が重複している（同じ ID の規約は 1 つの版だけ）")
    present = set(spec.members)
    digests: dict[tuple[str, int], str] = {}
    for key in sorted(present):
        convention = registry.conventions.get(key)
        if convention is None:
            known = sorted(v for (m, v) in registry.conventions if m == key[0])
            problems.append(f"規約 {key[0]}@{key[1]} を知らない" + (f"（知っている版は {known}）" if known else "（未知の規約 ID）"))
            continue
        if convention.layer not in LAYERS or convention.approval not in APPROVALS:
            problems.append(f"規約 {key[0]}@{key[1]} の層・承認の状態を知らない")
            continue
        try:
            digest = convention_digest(convention, registry.sources)
        except (KeyError, TypeError, ValueError) as exc:
            problems.append(f"規約 {key[0]}@{key[1]} の内容を読めない（{exc}）")
            continue
        digests[key] = digest
        pinned = registry.pinned_conventions.get(key)
        if pinned is None:
            problems.append(f"規約 {key[0]}@{key[1]} の照合値が固定されていない（内容の不変を確かめられない）")
        elif pinned != digest:
            problems.append(f"規約 {key[0]}@{key[1]} の内容が、固定した照合値と違う（同じ ID・版のまま内容を変えた。版を上げる）")
        if convention.layer == LAYER_BASELINE_USER and convention.approval != APPROVAL_USER_AGREED:
            problems.append(f"規約 {key[0]}@{key[1]} は利用者の指定の層なのに、承認の状態が {convention.approval}")
        if convention.layer == LAYER_CURRENT_BEHAVIOR and convention.approval != APPROVAL_NOT_APPROVED:
            problems.append(f"規約 {key[0]}@{key[1]} は今の挙動の記録で、承認の記録ではない（承認済みにしない）")
        if convention.layer == LAYER_CONTINUATION and spec.usage == USAGE_STANDARD and convention.approval != APPROVAL_USER_AGREED:
            problems.append(f"続行規約 {key[0]}@{key[1]} は承認されていないので、通常の集合に入れない（開発用の集合だけ）")
        if not implemented(convention, registry):
            problems.append(f"規約 {key[0]}@{key[1]} は、この版のエンジンが処理を持たない（未実装）")
        for need in convention.requires:
            if need not in present:
                problems.append(f"規約 {key[0]}@{key[1]} が必要とする {need[0]}@{need[1]} が集合にない（依存の不足）")
        for other in convention.conflicts:
            if other in present:
                problems.append(f"規約 {key[0]}@{key[1]} と {other[0]}@{other[1]} は同じ集合に入れられない（競合）")
    scenes: dict[str, list[str]] = {}
    known_scenes = {s["id"] for s in scene_index()["scenes"]}
    for key in sorted(present):
        convention = registry.conventions.get(key)
        for scene in (convention.scenes if convention is not None else ()):
            scenes.setdefault(scene, []).append(f"{key[0]}@{key[1]}")
            if scene not in known_scenes:
                problems.append(f"規約 {key[0]}@{key[1]} の場面 {scene} が、停止の方針の台帳の場面にない（v0.143。登録の不整合）")
        if convention is not None and convention.layer == LAYER_CONTINUATION and not convention.scenes:
            problems.append(f"続行規約 {key[0]}@{key[1]} に場面がない（v0.143）")
    for scene, owners in sorted(scenes.items()):
        if len(owners) > 1:
            problems.append(f"場面 {scene} に 2 つ以上の規約（{'・'.join(owners)}）が当たる（暗黙の優先順位を作らない。競合）")
    in_set = {m for (m, v) in present if (c := registry.conventions.get((m, v))) is not None and c.layer == LAYER_BASELINE_USER}
    missing_baseline = sorted(registry.engine_baseline() - in_set)
    for uid in missing_baseline:
        problems.append(f"利用者の指定 {uid} を外した集合は、この版のエンジンが実装できない（登録はいつもはたらく）")
    problems.extend(completeness_problems(spec, registry))
    registered = registry.sets.get((spec.id, spec.version))
    if registered is None:
        known = sorted(v for (s, v) in registry.sets if s == spec.id)
        problems.append(f"規約集合 {spec.id}@{spec.version} を知らない" + (f"（知っている版は {known}）" if known else "（未知の集合 ID）"))
    elif (registered.usage, registered.completeness, tuple(sorted(registered.members))) != (spec.usage, spec.completeness, tuple(sorted(spec.members))):
        problems.append(f"規約集合 {spec.id}@{spec.version} の中身が、登録した同じ ID・版の集合と違う（同じ ID・版の内容は変えない）")
    if not problems:
        digest = _digest(_SET_DOMAIN, set_payload(spec, digests))
        pinned = registry.pinned_sets.get((spec.id, spec.version))
        if pinned is None:
            problems.append(f"規約集合 {spec.id}@{spec.version} の照合値が固定されていない")
        elif pinned != digest:
            problems.append(f"規約集合 {spec.id}@{spec.version} の内容が、固定した照合値と違う（同じ ID・版のまま内容を変えた。版を上げる）")
    return problems


def identity_of(spec: ConventionSet, registry: Registry = DEFAULT_REGISTRY, *, for_new_game: bool = True) -> ConventionSetIdentity:
    """確かめた集合の識別。問題があれば ``ConventionSetError``。"""
    problems = validate(spec, registry, for_new_game=for_new_game)
    if problems:
        raise ConventionSetError(problems)
    digests = {key: convention_digest(registry.conventions[key], registry.sources) for key in spec.members}
    return ConventionSetIdentity(set_id=spec.id, version=spec.version, digest=_digest(_SET_DOMAIN, set_payload(spec, digests)), usage=spec.usage,
                                 completeness=spec.completeness, members=tuple(sorted((m, v, digests[(m, v)]) for m, v in spec.members)))


# 登録した集合の識別の写し（登録の記録のオブジェクトが同じあいだだけ使う。記録・登録表を差しかえたら作り直して比べる）
_IDENTITY_CACHE: dict[tuple, ConventionSetIdentity] = {}


def _source_marker() -> tuple:
    from . import decisions, effects, sudden_death

    return (id(CONVENTIONS), id(SETS), id(PINNED_CONVENTION_DIGESTS), id(PINNED_SET_DIGESTS), id(effects.USER_SIMPLIFICATIONS), id(effects.USER_SPECIFIED_REFERENCES),
            id(effects.USER_SPECIFIED_RULES), id(effects.USER_SPECIFIED_NAMES), id(decisions.USER_PRIZE_ORDER_RULES), id(sudden_death.USER_SUDDEN_DEATH_OWNERSHIP_RESET),
            id(_bundled_records()))


def registered_identity(key: tuple[str, int]) -> ConventionSetIdentity:
    """登録した集合（``SETS``）の識別。確かめに失敗すれば ``ConventionSetError``。"""
    marker = (key, _source_marker())
    cached = _IDENTITY_CACHE.get(marker)
    if cached is None:
        spec = DEFAULT_REGISTRY.sets.get(key)
        if spec is None:
            raise ConventionSetError([f"規約集合 {key[0]}@{key[1]} を知らない"])
        cached = identity_of(spec, DEFAULT_REGISTRY, for_new_game=False)
        _IDENTITY_CACHE.clear()
        _IDENTITY_CACHE[marker] = cached
    return cached


def default_identity() -> ConventionSetIdentity:
    """省略したときの集合（今の挙動の集合）の識別。``GameState`` を直接作ったときの既定値にも使う。"""
    return registered_identity(DEFAULT_SET)


def parse_key(text: str) -> tuple[str, int]:
    """``"ID@版"`` の文字列を (ID, 版) にする。形が違えば ``ConventionSetError``。"""
    name, sep, version = text.rpartition("@")
    if not (sep and name and version.isdigit() and version == str(int(version)) and int(version) >= 1):
        raise ConventionSetError([f"規約集合は ID@版（例 {CURRENT_SET_ID}@1）で指定する"])
    return name, int(version)


def resolve_for_new_game(conventions) -> ConventionSetIdentity:
    """``new_game`` の ``conventions`` を確かめて識別にする。省略（None）は今の挙動の集合。``ConventionSet``・``"ID@版"``・``ConventionSetIdentity`` を受け付け、どれも登録した集合と
    内容が同じときだけ。呼び出し元のオブジェクトは持たない（識別の値だけを状態に置く）。"""
    if conventions is None:
        return default_identity()
    if isinstance(conventions, str):
        spec = DEFAULT_REGISTRY.sets.get(parse_key(conventions))
        if spec is None:
            raise ConventionSetError([f"規約集合 {conventions} を知らない"])
        return identity_of(spec)
    if isinstance(conventions, ConventionSetIdentity):
        spec = DEFAULT_REGISTRY.sets.get(conventions.key) if isinstance(conventions.set_id, str) and _is_key(conventions.key) else None
        if spec is None:
            raise ConventionSetError(["規約集合の識別が、登録した集合のどれでもない"])
        identity = identity_of(spec)
        if identity != conventions:
            raise ConventionSetError([f"規約集合の識別が、登録した {spec.id}@{spec.version} の内容（照合値・規約）と違う"])
        return identity
    return identity_of(conventions)


# ---------------------------------------------------------------- 状態の規約集合


def legacy_problems(state) -> list[str]:
    """記録のない状態を旧状態として扱える条件（docs/ruleset-foundation-v0.142.md 6 章）。どの版で作ったかは推測しない。

    - 最初の区間のログの最初が ``game_created`` で、項目が v0.141 までと同じ（kind・turn・rules・seed・card_data_commit）、値が状態のルールの組・seed・写しの元と同じ
      （``new_game`` で作った対戦の状態であること。盤面を直接作った状態・ログの合わない状態は、どの処理で作ったかが分からないので扱わない）"""
    first_log = state.segments[0].log if getattr(state, "segments", ()) else state.log
    created = first_log[0] if first_log else None
    if created is None or created.get("kind") != "game_created":
        return ["規約集合の記録がなく、最初のログが対戦の作成（game_created）ではない（new_game で作った対戦の状態と確かめられない）"]
    if set(created) != {"kind", "turn", "rules", "seed", "card_data_commit"}:
        return ["規約集合の記録がなく、対戦の作成のログの項目が v0.141 までの形と違う"]
    if (created["rules"], created["seed"], created["card_data_commit"]) != (state.rules.id, state.seed, state.card_data.commit):
        return ["規約集合の記録がなく、対戦の作成のログが状態のルールの組・seed・写しの元と合わない"]
    return []


def state_conventions(state) -> tuple[ConventionSetIdentity | None, str | None]:
    """状態の規約集合の識別と、扱えないときの理由。記録のない旧状態は、条件を満たせば旧状態用の集合（``LEGACY_SET_ID``）。理由の文に状態の中の値を書かない（信頼できない）。"""
    value = getattr(state, "conventions", UNRECORDED)
    if isinstance(value, UnrecordedConventions):
        problems = legacy_problems(state)
        if problems:
            return None, problems[0]
        return registered_identity((LEGACY_SET_ID, 1)), None
    if not isinstance(value, ConventionSetIdentity):
        return None, "状態の規約集合の記録の形を知らない"
    if not (isinstance(value.set_id, str) and _is_key(value.key)) or value.key not in DEFAULT_REGISTRY.sets:
        return None, "状態の規約集合を、この版は知らない（どこで作った状態かは状態から分からない）"
    try:
        registered = registered_identity(value.key)
    except ConventionSetError:
        return None, "状態の規約集合の登録を、この版で確かめられない"
    if registered != value:
        return None, "状態の規約集合の識別（照合値・規約）が、この版の登録の内容と違う（推測で続けない）"
    return value, None


def require_state_conventions(state) -> ConventionSetIdentity:
    """コマンド・観測の前の確かめ。扱えなければ ``UnsupportedError``（``UNSUPPORTED_CONVENTION_SET``）。状態・乱数・ログを変えない。"""
    identity, problem = state_conventions(state)
    if identity is None:
        raise UnsupportedError(UNSUPPORTED_CONVENTION_SET_CODE, problem)
    return identity


# ---------------------------------------------------------------- 場面と規約の照会


@dataclass(frozen=True)
class ContinuationLookup:
    """未決の場面の続行規約の照会の結果。``convention`` が None なら続行規約はなく、呼ぶ側は今までどおり止める。``status``:

    - ``"no_continuation"``: 場面を特定でき、その場面の続行規約が集合にない
    - ``"case_not_identified"``: 停止コードに 2 つ以上の事例があり、この場所で事例を特定していない（コードだけで規約を決めない）
    - ``"unknown_scene"``: 停止の方針の台帳の場面にない停止（台帳の作り直しが要る）"""

    code: str
    scene: str | None
    candidates: tuple[str, ...]
    status: str
    convention: tuple[str, int] | None = None


def scenes_for_code(code: str) -> tuple[str, ...]:
    return tuple(scene_index()["codes"].get(code, ()))


def continuation_lookup(identity: ConventionSetIdentity, code: str, case: str | None = None) -> ContinuationLookup:
    """未決の場面（停止コード、事例が分かればその事例）の続行規約を、集合から引く。基礎の規約（利用者の指定）の照会とは別のもの（基礎の規約は、エンジンの登録がいつも当てはめる）。"""
    candidates = scenes_for_code(code)
    if case is not None:
        scene = f"{code}#{case}"
        if scene not in candidates:
            return ContinuationLookup(code, None, candidates, "unknown_scene")
    elif len(candidates) == 1:
        scene = candidates[0]
    elif not candidates:
        return ContinuationLookup(code, None, (), "unknown_scene")
    else:
        return ContinuationLookup(code, None, candidates, "case_not_identified")
    for member, version, _ in identity.members:
        convention = DEFAULT_REGISTRY.conventions.get((member, version))
        if convention is not None and convention.layer == LAYER_CONTINUATION and scene in convention.scenes:
            return ContinuationLookup(code, scene, candidates, "convention", (member, version))
    return ContinuationLookup(code, scene, candidates, "no_continuation")


def stop_without_continuation(state, code: str, case: str | None = None) -> ContinuationLookup:
    """止める箇所の照会（v0.142）。続行規約がないことを確かめて返す（呼ぶ側はそのまま止める）。

    v0.143: 続行規約のある場面は、止める理由を作る分岐の手前（``continuation_for``）で続けるので、止める直前にここで規約が見つかればエンジンの不具合（続ける分岐を通らずに
    止めようとした）。停止の例外を捕まえて無視する仕組みではない（止める前に引くだけ）。"""
    identity, problem = state_conventions(state)
    if identity is None:
        raise UnsupportedError(UNSUPPORTED_CONVENTION_SET_CODE, problem)
    lookup = continuation_lookup(identity, code, case)
    if lookup.convention is not None:
        raise RuntimeError(f"続行規約 {lookup.convention[0]}@{lookup.convention[1]} のある場面 {lookup.scene} で止めようとした（続ける分岐を通っていない。エンジンの不具合）")
    return lookup


def continuation_for(state, code: str, case: str | None = None) -> ContinuationLookup | None:
    """v0.143: 止める理由を作る分岐の手前の照会。状態の規約集合に、この場面（停止コード、事例が分かればその事例）の続行規約があり、この版のエンジンが処理を持てば、その照会の結果
    （``convention`` あり）。なければ None（呼ぶ側は今までどおり止める）。停止コードに 2 つ以上の事例があって事例を渡さなければ、コードだけで規約を決めない（None）。

    規約の名前・カード ID で分岐する呼び方はしない（呼ぶ側は停止コードと事例だけを渡し、規約の意味は呼ぶ側の共通の処理が持つ）。状態の規約集合を扱えなければ
    ``UnsupportedError``（``UNSUPPORTED_CONVENTION_SET``）。状態を変えない。"""
    identity, problem = state_conventions(state)
    if identity is None:
        raise UnsupportedError(UNSUPPORTED_CONVENTION_SET_CODE, problem)
    lookup = continuation_lookup(identity, code, case)
    if lookup.convention is None:
        return None
    if lookup.convention not in DEFAULT_REGISTRY.implemented_continuations:
        raise RuntimeError(f"状態の規約集合の続行規約 {lookup.convention[0]}@{lookup.convention[1]} の処理が、この版にない（集合の確かめを通らないはず。エンジンの不具合）")
    return lookup


# 規約を当てた記録（ログ ``convention_applied``）に書ける項目（全員に見える値だけ。手札・山札などの秘密の情報は書かない）
APPLIED_FIELDS = frozenset({"players", "player", "rounds_both", "rounds_single", "order", "pokemon_ids", "element", "heads", "available", "processed", "source",
                            "target_owner", "target",
                            "pokemon_id", "amount", "poison_mists", "ended_mists"})  # v0.145: どくの量の規約（ポケモンの場の番号・受けるダメージ・［ポイズンミスト］の記録の発生源。公開）


def record_application(state, lookup: ContinuationLookup, **detail) -> None:
    """v0.143: 続行規約が実際に処理を決めたときのログ ``convention_applied``（規約 ID・版・場面・停止コードと、追跡に要る公開の値）。先読み・答えの確かめ・拒否した操作は状態の
    複製の上なので、このログは残らない（受け付けた処理の状態だけに残る）。"""
    if lookup is None or lookup.convention is None:
        raise RuntimeError("続行規約のない照会の結果を、規約を当てた記録にしようとした（エンジンの不具合）")
    unknown = sorted(set(detail) - APPLIED_FIELDS)
    if unknown:
        raise RuntimeError(f"規約を当てた記録に、決めていない項目 {unknown} を書こうとした（エンジンの不具合）")
    convention, version = lookup.convention
    state.add_event("convention_applied", convention=convention, version=version, scene=lookup.scene, code=lookup.code, **detail)
