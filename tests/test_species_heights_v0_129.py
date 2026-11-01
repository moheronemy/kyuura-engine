"""v0.129 の移行: 公式図鑑の種族の身長の参照値の写し（docs/blaines-quiz-heights-v0.129.md 2 章）。

- 写し（kyuura_engine/data/species_heights.json）が kyuura の固定したコミットから生成したものと同じで、値が kyuura のデータと 1 件ずつ同じ（予定外の変更がない）
- 読み込みの検査（番号の一意性・範囲・欠け・原表記と整数 cm・出典）が、壊した写しを拒否する（0cm・推測で補わない）
- カードとの対応は図鑑番号だけ（所有者名つきカード・ポリゴン2・図鑑番号のないカード）。名前は公式の表記のまま
- 人向けの答えの換算（単位を明示した値だけ。0.4m と 40cm は同じ）
"""

from __future__ import annotations

import copy
import dataclasses
import json
import pathlib
import subprocess
import sys
import unicodedata
import unittest

from kyuura_engine.cards import load_card_pool
from kyuura_engine.heights import (
    HEIGHT_MULTIPLE_DEX,
    HEIGHT_NOT_AVAILABLE,
    HEIGHT_WITHOUT_DEX,
    HEIGHTS_PATH,
    card_height,
    height_answer_cm,
    load_species_heights,
    parse_heights,
    raw_height_cm,
)

ROOT = pathlib.Path(__file__).resolve().parent.parent
KYUURA = ROOT.parent / "kyuura"
HEIGHTS_COMMIT = "9242b9be89be0f747279f39c11875d1ed61763ec"
REPORTED_COMMIT = "59a99fcb9dc414ecbc7e4f5929bc0e34a6776ff6"
CARD_DATA_COMMIT = "71d1728938fb4c8fefde9b82779cdef74beb612d"


def needs_kyuura(test):
    return unittest.skipUnless((KYUURA / ".git").exists(), "../kyuura がない")(test)


def copied() -> dict:
    return json.loads(HEIGHTS_PATH.read_text(encoding="utf-8"))


class CopyTest(unittest.TestCase):
    @needs_kyuura
    def test_extract_check(self):
        result = subprocess.run([sys.executable, str(ROOT / "scripts" / "extract_species_heights.py"), "--kyuura", str(KYUURA), "--check"],
                                capture_output=True, text=True, encoding="utf-8", check=False)
        self.assertEqual(result.returncode, 0, result.stderr)

    @needs_kyuura
    def test_every_value_is_the_kyuura_value(self):
        """全データの差分: 251 件の名前・原表記・cm・出典・URL・取得日・ハッシュが kyuura の値と同じで、写しにない値・予定外の欄がない。"""
        raw = subprocess.run(["git", "-C", str(KYUURA), "show", f"{HEIGHTS_COMMIT}:data/species_heights.json"], capture_output=True, check=True).stdout
        source = json.loads(raw.decode("utf-8"))
        data = copied()
        self.assertEqual(len(source["species"]), 251)
        self.assertEqual([e["dex"] for e in data["species"]], list(range(1, 252)))
        self.assertEqual(data["unavailable"], [])
        for theirs, ours in zip(source["species"], data["species"], strict=True):
            observation = theirs["observations"][0]
            self.assertEqual(ours, {
                "dex": theirs["dex"], "name_ja": theirs["name_ja"], "height_raw": theirs["height"]["raw"], "height_cm": theirs["height"]["cm"],
                "source": theirs["height"]["source"], "url": observation["url"], "retrieved_on": observation["retrieved_on"],
                "extract_sha256": observation["extract_sha256"], "response_sha256": observation["response_sha256"], "response_bytes": observation["response_bytes"]})
        self.assertEqual(data["sources"]["SRC-ZUKAN-JP"]["access_log"], source["sources"]["SRC-ZUKAN-JP"]["access_log"])
        self.assertEqual(data["scope"]["form_policy"], source["scope"]["form_policy"])

    @needs_kyuura
    def test_pinned_commit(self):
        source = copied()["source"]
        self.assertEqual((source["commit"], source["reported_commit"], source["path"]), (HEIGHTS_COMMIT, REPORTED_COMMIT, "data/species_heights.json"))
        tree = lambda c: subprocess.run(["git", "-C", str(KYUURA), "rev-parse", f"{c}^{{tree}}"], capture_output=True, text=True, check=True).stdout.strip()
        self.assertEqual(tree(HEIGHTS_COMMIT), tree(REPORTED_COMMIT))  # マージの木は報告の最後のコミットと同じ
        self.assertEqual(source["tree"], tree(HEIGHTS_COMMIT))
        # カードのデータは写しの元（71d1728）と同じブロブ（図鑑番号の対応がずれない）。カードの写しの元・研究の基準は上げていない
        blob = lambda c, p: subprocess.run(["git", "-C", str(KYUURA), "rev-parse", f"{c}:{p}"], capture_output=True, text=True, check=True).stdout.strip()
        self.assertEqual(blob(HEIGHTS_COMMIT, "data/cards.json"), blob(CARD_DATA_COMMIT, "data/cards.json"))
        self.assertEqual(source["card_data"], {"path": "data/cards.json", "git_blob": blob(CARD_DATA_COMMIT, "data/cards.json"), "same_as_commit": CARD_DATA_COMMIT})
        sys.path.insert(0, str(ROOT / "scripts"))
        import extract_kyuura_cards
        self.assertEqual(extract_kyuura_cards.KYUURA_COMMIT, CARD_DATA_COMMIT)

    def test_extract_problems_are_reported(self):
        """抽出の検査（kyuura のデータの形）: 番号の重なり・範囲の外・欠け・通常でない姿・原表記と cm の違い・登録していない出典・抜き出しのハッシュ。"""
        sys.path.insert(0, str(ROOT / "scripts"))
        import extract_species_heights as X

        def entry(dex, raw="0.7m", cm=70, name="フシギダネ"):
            extract = {"no": dex, "sub": 0, "name": name, "form_name": "", "takasa": raw}
            return {"dex": dex, "name_ja": name, "form": {"kind": "default", "source_form_id": 0, "form_name": None},
                    "height": {"raw": raw, "cm": cm, "source": "SRC-ZUKAN-JP"}, "status": "confirmed", "status_reason": None,
                    "observations": [{"source": "SRC-ZUKAN-JP", "url": f"https://zukan.pokemon.co.jp/detail/{dex:04d}", "retrieved_on": "2026-10-31", "name_ja": name,
                                      "source_form_id": 0, "form_name": None, "raw_height": raw, "cm": cm, "extract": extract,
                                      "extract_sha256": X.canonical_sha256(extract), "response_sha256": "0" * 64, "response_bytes": 1}]}

        def data(entries):
            return {"schema_version": 1, "scope": {"dex_first": 1, "dex_last": 251, "form_policy": ""},
                    "sources": {"SRC-ZUKAN-JP": {"official": True, "detail_url": "https://zukan.pokemon.co.jp/detail/{dex:04d}", "height_unit": "m"}},
                    "species": entries}

        good = [entry(d) for d in range(1, 252)]
        self.assertEqual(X.species_problems(data(good)), [])
        cases = [
            ("重なる", good[:5] + [entry(5)] + good[5:]),
            ("範囲の外", good + [entry(252)]),
            ("欠けた", good[:9] + good[10:]),
            ("原表記", good[:2] + [entry(3, "0.7m", 71)] + good[3:]),
            ("原表記", good[:2] + [entry(3, "0.755m", 75)] + good[3:]),  # 整数 cm にならない（丸めない）
            ("原表記", good[:2] + [entry(3, "70", 70)] + good[3:]),  # 単位がない
        ]
        for label, entries in cases:
            self.assertTrue(any(label in p for p in X.species_problems(data(entries))), label)
        odd = copy.deepcopy(good)
        odd[0]["form"]["source_form_id"] = 1
        self.assertTrue(any("通常の姿" in p for p in X.species_problems(data(odd))))
        odd = copy.deepcopy(good)
        odd[0]["observations"][0]["extract"]["takasa"] = "0.8m"
        self.assertTrue(any("sha256" in p for p in X.species_problems(data(odd))))
        unofficial = data(good)
        unofficial["sources"]["SRC-OTHER"] = {"official": False}
        self.assertTrue(any("出典" in p for p in X.species_problems(unofficial)))
        unverified = copy.deepcopy(good)
        unverified[0].update({"status": "unverified", "height": None, "name_ja": None})
        self.assertEqual(X.species_problems(data(unverified)), [])  # 確定していない種族は値を持たないだけ（0cm にしない）
        unverified[0]["height"] = {"raw": "0m", "cm": 0, "source": "SRC-ZUKAN-JP"}
        self.assertTrue(X.species_problems(data(unverified)))


class LoaderTest(unittest.TestCase):
    def test_loaded_values(self):
        heights = load_species_heights()
        self.assertEqual(len(heights.by_dex), 251)
        self.assertEqual(dict(heights.unavailable), {})
        smallest = min(h.height_cm for h in heights.by_dex.values())
        largest = max(h.height_cm for h in heights.by_dex.values())
        self.assertEqual((smallest, largest), (20, 920))
        self.assertEqual(sorted(h.name_ja for h in heights.by_dex.values() if h.height_cm == 20), ["ディグダ", "ネイティ"])
        self.assertEqual([h.name_ja for h in heights.by_dex.values() if h.height_cm == 920], ["ハガネール"])
        self.assertEqual(heights.by_dex[233].name_ja, "ポリゴン２")  # 公式の表記のまま（全角数字。正規化しない）
        self.assertNotEqual(heights.by_dex[233].name_ja, unicodedata.normalize("NFKC", heights.by_dex[233].name_ja))
        self.assertTrue(all(raw_height_cm(h.height_raw) == h.height_cm for h in heights.by_dex.values()))

    def test_broken_copies_are_refused(self):
        good = copied()
        self.assertEqual(len(parse_heights(good).by_dex), 251)

        def broken(change):
            data = copy.deepcopy(good)
            change(data)
            with self.assertRaises(ValueError):
                parse_heights(data)

        broken(lambda d: d["species"].append(dict(d["species"][0])))  # 重なる番号
        broken(lambda d: d["species"].pop(9))  # 欠けた番号（補わない）
        broken(lambda d: d["species"][0].update(dex=252))  # 範囲の外
        broken(lambda d: d["species"][0].update(dex=True))  # 整数でない
        broken(lambda d: d["species"][0].update(height_cm=0))  # 0cm にしない
        broken(lambda d: d["species"][0].update(height_cm=None))
        broken(lambda d: d["species"][0].update(height_cm=71))  # 原表記と合わない
        broken(lambda d: d["species"][0].update(height_raw="70"))  # 単位のない原表記
        broken(lambda d: d["species"][0].update(source="SRC-OTHER"))  # 登録していない出典
        broken(lambda d: d["species"][0].update(url="https://example.invalid/0001"))
        broken(lambda d: d["species"][0].update(response_sha256=None))
        broken(lambda d: d["sources"]["SRC-ZUKAN-JP"].update(official=False))
        broken(lambda d: d["unavailable"].append({"dex": 1, "status": "unverified", "status_reason": None}))  # 値のある番号と重なる

        def moved(d):  # 1 件を値なしに移す: 範囲を覆うので受け付け、その番号は値を持たない（0cm にしない）
            d["species"] = d["species"][1:]
            d["unavailable"] = [{"dex": 1, "status": "unverified", "status_reason": "not_collected"}]
            d["counts"].update(confirmed=250, unavailable=1)

        data = copy.deepcopy(good)
        moved(data)
        heights = parse_heights(data)
        self.assertNotIn(1, heights.by_dex)
        self.assertEqual(card_height(load_card_pool().get("PMCG1-001"), heights), (None, HEIGHT_NOT_AVAILABLE))  # フシギダネ（No.1）

    def test_cards_are_matched_by_dex_only(self):
        pool = load_card_pool()
        self.assertEqual(card_height(pool.get("PMCG1-052"))[0].height_cm, 20)  # ディグダ
        self.assertEqual(card_height(pool.get("PMCG6-066"))[0].dex, 137)  # ナツメのポリゴン（所有者名つき。名前ではなく図鑑番号）
        polygon2 = pool.get("neo3-051")
        self.assertEqual((polygon2.name_ja, polygon2.dex), ("ポリゴン2", (233,)))
        self.assertEqual(card_height(polygon2)[0].name_ja, "ポリゴン２")  # カード名と公式の表記が違っても図鑑番号で結ぶ
        self.assertEqual(card_height(pool.get("ES1-033")), (None, HEIGHT_WITHOUT_DEX))  # ポリゴン（拡張シート）。名前が同じでも図鑑番号がなければ補わない
        self.assertEqual(card_height(pool.get("PMCG1-097")), (None, HEIGHT_WITHOUT_DEX))  # エネルギー
        self.assertEqual(card_height(dataclasses.replace(polygon2, dex=(137, 233))), (None, HEIGHT_MULTIPLE_DEX))  # 2 つ以上の番号から選ばない
        renamed = dataclasses.replace(pool.get("ES1-033"), name_ja="ポリゴン２")
        self.assertEqual(card_height(renamed), (None, HEIGHT_WITHOUT_DEX))  # 公式の表記と同じ名前でも名前から引かない

    def test_dex_counts_in_the_copy(self):
        pokemon = [d for d in load_card_pool().definitions.values() if d.category == "pokemon"]
        self.assertEqual(len(pokemon), 1064)
        self.assertEqual(sum(1 for d in pokemon if not d.dex), 225)
        self.assertEqual(sum(1 for d in pokemon if len(d.dex) == 1), 839)
        self.assertTrue(all(card_height(d)[0] is not None for d in pokemon if d.dex))  # 図鑑番号のあるカードはどれも 1〜251 の値に結ぶ

    def test_name_check_uses_matching_normalization_only(self):
        """照合の確かめ: 公式の名前（NFKC でそろえた）が、同じ図鑑番号のカードのどれかの名前に含まれる。答えの判定・記録する名前には使わない。"""
        heights = load_species_heights()
        names: dict[int, set[str]] = {}
        for d in load_card_pool().definitions.values():
            if d.category == "pokemon" and len(d.dex) == 1:
                names.setdefault(d.dex[0], set()).add(d.name_ja)
        for dex, cards in names.items():
            species = unicodedata.normalize("NFKC", heights.by_dex[dex].name_ja)
            self.assertTrue(any(species in unicodedata.normalize("NFKC", n) for n in cards), (dex, heights.by_dex[dex].name_ja, cards))


class AnswerFormTest(unittest.TestCase):
    def test_units(self):
        for text in ("0.4m", "0.4 m", "40cm", "40 cm", "0.40m", "40.0cm", "０.４ｍ", "４０ｃｍ"):
            self.assertEqual(height_answer_cm(text), 40, text)
        self.assertEqual(height_answer_cm("9.2m"), 920)
        self.assertEqual(height_answer_cm("0.2m"), 20)
        self.assertEqual(height_answer_cm("1.1m"), 110)  # 浮動小数点（1.1 * 100 = 110.00000000000001）で丸めが入らない
        self.assertEqual(height_answer_cm("0.29m"), 29)

    def test_bad_forms(self):
        for text in ("40", "0.4", "", "m", "0.405m", "0m", "0cm", "-1m", "1e2cm", ".4m", "4.m", "40mm", "0.4M", "40 cm 1", "40cm40cm"):
            with self.assertRaises(ValueError, msg=repr(text)):
                height_answer_cm(text)
        for value in (None, 40, 0.4):
            with self.assertRaises(TypeError, msg=repr(value)):
                height_answer_cm(value)


if __name__ == "__main__":
    unittest.main()
