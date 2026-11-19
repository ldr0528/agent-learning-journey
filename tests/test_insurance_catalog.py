"""产品版本隔离、证据定位及目录数据约束；不调用模型或网络。"""

from copy import deepcopy
import json
from pathlib import Path
import tempfile
import unittest
from urllib.parse import urlsplit

from agent_learning.insurance.catalog import Catalog, DEFAULT_PATH, DIMENSIONS, OFFICIAL_PATH


class InsuranceCatalogTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.path = Path(self.directory.name) / "catalog.json"
        self.payload = json.loads(DEFAULT_PATH.read_text(encoding="utf-8"))

    def catalog(self, payload=None, *, indent=None):
        self.path.write_text(json.dumps(self.payload if payload is None else payload,
                                       ensure_ascii=False, indent=indent), encoding="utf-8")
        return Catalog(self.path)

    def test_default_catalog_has_three_complete_synthetic_products(self):
        catalog = Catalog()
        products = catalog.list_products()
        self.assertEqual(len(products), 3)
        self.assertEqual(len(DIMENSIONS), 9)
        for metadata in products:
            self.assertNotIn("facts", metadata)
            self.assertEqual(metadata["data_kind"], "synthetic")
            self.assertEqual(metadata["source"]["url"], "")
            product = catalog.get_product(metadata["product_id"], metadata["version"])
            self.assertEqual({fact["dimension"] for fact in product["facts"]}, set(DIMENSIONS))
            self.assertTrue(all(fact["status"] == "unknown" for fact in catalog.facts(
                metadata["product_id"], metadata["version"], "premium")))

    def test_product_isolation_applies_before_search_and_read(self):
        catalog = Catalog()
        other = catalog.facts("demo_outpatient", "demo-v1", "coverage")[0]
        with self.assertRaisesRegex(ValueError, "不属于"):
            catalog.read("demo_hospital", "demo-v1", other["evidence_id"])
        self.assertEqual(catalog.search("demo_hospital", "demo-v1", "牙齿矫正"), [])
        found = catalog.search("demo_outpatient", "demo-v1", "牙齿矫正")
        self.assertTrue(found)
        self.assertTrue(all(f["product_id"] == "demo_outpatient" for f in found))

    def test_multiple_versions_are_exact_and_do_not_fall_back(self):
        alternate = deepcopy(self.payload["products"][0])
        alternate["version"] = "demo-v2"
        for fact in alternate["facts"]:
            fact["evidence_id"] = fact["evidence_id"].replace("-V1-", "-V2-")
        waiting = next(f for f in alternate["facts"] if f["dimension"] == "waiting_period")
        waiting["text"] = "本测试版本的疾病等待期为45日。"
        self.payload["products"].append(alternate)
        catalog = self.catalog()
        self.assertIn("45日", catalog.facts("demo_hospital", "demo-v2", "waiting_period")[0]["text"])
        self.assertIn("30日", catalog.facts("demo_hospital", "demo-v1", "waiting_period")[0]["text"])
        with self.assertRaises(ValueError):
            catalog.read("demo_hospital", "demo-v1", waiting["evidence_id"])
        with self.assertRaisesRegex(ValueError, "没有产品版本"):
            catalog.get_product("demo_hospital", "latest")
        with self.assertRaises(ValueError):
            catalog.get_product("missing", "demo-v1")

    def test_all_fact_methods_preserve_scope_and_locator(self):
        catalog = Catalog()
        fact = catalog.facts("demo_renewal", "demo-v1", "renewal")[0]
        for result in (fact, catalog.read("demo_renewal", "demo-v1", fact["evidence_id"]),
                       catalog.search("demo_renewal", "demo-v1", "续保安排", limit=1)[0]):
            self.assertEqual(result["product_id"], "demo_renewal")
            self.assertEqual(result["version"], "demo-v1")
            self.assertEqual(result["product_name"], "教学医疗计划C：长期续保安排")
            self.assertEqual(result["data_kind"], "synthetic")
            self.assertEqual(result["locator"], "第6条 续保安排")
            self.assertIn("不等于保费固定", " ".join(result["conditions"]))
            self.assertIn("自拟", result["source"]["title"])

    def test_returned_values_are_deep_copies(self):
        catalog = Catalog()
        product = catalog.get_product("demo_hospital", "demo-v1")
        evidence_id = product["facts"][0]["evidence_id"]
        original = catalog.read("demo_hospital", "demo-v1", evidence_id)
        views = [catalog.list_products()[0], product,
                 catalog.read("demo_hospital", "demo-v1", evidence_id),
                 catalog.facts("demo_hospital", "demo-v1", "coverage")[0],
                 catalog.search("demo_hospital", "demo-v1", "保障范围", limit=1)[0]]
        for view in views:
            view["source"]["title"] = "被外部修改"
            if "conditions" in view:
                view["conditions"].append("被外部修改")
        product["facts"][0]["text"] = "被外部修改"
        product["facts"][0]["source"]["locator"] = "被外部修改"
        self.assertEqual(catalog.read("demo_hospital", "demo-v1", evidence_id), original)

    def test_search_returns_only_matches_and_preserves_unknown(self):
        catalog = Catalog()
        # 无共同词项的查询为空；字面检索不把通用词重合解释成语义可回答。
        self.assertEqual(catalog.search("demo_hospital", "demo-v1", "火星日出"), [])
        self.assertEqual(catalog.search("demo_hospital", "demo-v1", "???"), [])
        found = catalog.search("demo_hospital", "demo-v1", "保费多少钱", limit=1)
        self.assertEqual(found[0]["dimension"], "premium")
        self.assertEqual(found[0]["status"], "unknown")
        self.assertEqual(found, catalog.search("demo_hospital", "demo-v1", "保费多少钱", limit=1))
        for query, limit in ((" ", 3), (None, 3), ("保费", 0), ("保费", True), ("保费", 1.5)):
            with self.subTest(query=query, limit=limit), self.assertRaises(ValueError):
                catalog.search("demo_hospital", "demo-v1", query, limit=limit)
        with self.assertRaises(ValueError):
            catalog.facts("demo_hospital", "demo-v1", "invalid")

    def test_conflict_is_returned_without_silently_resolving_conditions(self):
        fact = self.payload["products"][0]["facts"][0]
        fact["status"] = "conflict"
        fact["text"] = "保障资料对普通门诊责任存在不同说明。"
        fact["conditions"] = ["资料甲写明包含；资料乙写明不包含，适用版本待核实。"]
        result = self.catalog().facts("demo_hospital", "demo-v1", "coverage")[0]
        self.assertEqual(result["status"], "conflict")
        self.assertEqual(result["conditions"], fact["conditions"])

    def test_invalid_schema_and_duplicate_identities_are_rejected(self):
        candidates = []
        for version in (True, 2, "1"):
            bad = deepcopy(self.payload)
            bad["schema_version"] = version
            candidates.append(bad)
        bad = deepcopy(self.payload)
        bad["products"] = []
        candidates.append(bad)
        bad = deepcopy(self.payload)
        bad["products"].append(deepcopy(bad["products"][0]))
        candidates.append(bad)
        bad = deepcopy(self.payload)
        bad["products"][1]["facts"][0]["evidence_id"] = bad["products"][0]["facts"][0]["evidence_id"]
        candidates.append(bad)
        for payload in candidates:
            with self.subTest(payload=payload.get("schema_version")), self.assertRaises(ValueError):
                self.catalog(payload)

    def test_missing_dimensions_and_invalid_fact_fields_are_rejected(self):
        bad = deepcopy(self.payload)
        bad["products"][0]["facts"].pop()
        with self.assertRaisesRegex(ValueError, "九个维度"):
            self.catalog(bad)
        for key, value in (("dimension", "health"), ("status", "yes"), ("text", ""),
                           ("conditions", "string"), ("conditions", [""]), ("conditions", [1]),
                           ("locator", ""), ("evidence_id", "../secret")):
            bad = deepcopy(self.payload)
            bad["products"][0]["facts"][0][key] = value
            with self.subTest(key=key, value=value), self.assertRaises(ValueError):
                self.catalog(bad)

    def test_source_provenance_and_dates_are_validated(self):
        for key, value in (("url", "file:///private/policy.pdf"), ("url", "javascript:alert(1)"),
                           ("url", "https://"), ("url", "https://user:secret@example.com/a"),
                           ("checked_at", "2026-02-30"), ("effective_date", "2026/01/01"),
                           ("title", ""), ("locator", None)):
            bad = deepcopy(self.payload)
            bad["products"][0]["source"][key] = value
            with self.subTest(key=key, value=value), self.assertRaises(ValueError):
                self.catalog(bad)
        bad = deepcopy(self.payload)
        bad["products"][0]["data_kind"] = "official_excerpt"
        with self.assertRaisesRegex(ValueError, "官方资料"):
            self.catalog(bad)
        bad = deepcopy(self.payload)
        bad["products"][0]["version"] = ""
        with self.assertRaises(ValueError):
            self.catalog(bad)

    def test_official_snapshots_keep_missing_data_and_short_attributed_facts(self):
        catalog = Catalog(OFFICIAL_PATH)
        products = catalog.list_products()
        self.assertEqual(len(products), 3)
        hosts = {urlsplit(p["source"]["url"]).hostname for p in products}
        self.assertEqual(hosts, {"life.pingan.com", "www.cpic.com.cn", "m.zhongan.com"})
        for product in products:
            self.assertEqual(product["data_kind"], "official_excerpt")
            self.assertTrue(product["version"].startswith("snapshot-"))
            self.assertIsNone(product["source"]["effective_date"])
            self.assertIn("非合同生效版本", product["source"]["locator"])
            facts = catalog.get_product(product["product_id"], product["version"])["facts"]
            self.assertEqual(sum(fact["status"] == "known" for fact in facts), 3)
            self.assertLessEqual(sum(len(fact["text"]) + sum(map(len, fact["conditions"])) for fact in facts), 200)
            for dimension in ("premium", "underwriting"):
                self.assertEqual(catalog.facts(product["product_id"], product["version"], dimension)[0]["status"], "unknown")

    def test_fingerprint_ignores_formatting_but_tracks_fact_changes(self):
        first = self.catalog(indent=2)
        second = self.catalog(indent=None)
        self.assertEqual(first.fingerprint, second.fingerprint)
        self.assertRegex(first.fingerprint, r"^[0-9a-f]{64}$")
        self.payload["products"][0]["facts"][0]["conditions"].append("新增范围限制")
        self.assertNotEqual(self.catalog().fingerprint, first.fingerprint)


if __name__ == "__main__":
    unittest.main()
