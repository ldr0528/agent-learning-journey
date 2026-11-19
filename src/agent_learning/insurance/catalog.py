"""医疗险教学产品目录：按产品版本隔离事实，保留条件和条款定位。"""

from copy import deepcopy
from datetime import date
import hashlib
import json
import math
from pathlib import Path
import re
from urllib.parse import urlsplit

from ..tools.retrieval import tokenize


DIMENSIONS = {
    "coverage": "保障范围", "deductible": "免赔额", "reimbursement": "赔付比例",
    "hospital": "医院范围", "waiting_period": "等待期", "renewal": "续保安排",
    "exclusions": "责任除外", "premium": "保费", "underwriting": "健康告知与核保",
}
DEFAULT_PATH = Path(__file__).resolve().parents[1] / "data" / "insurance_demo.json"
OFFICIAL_PATH = DEFAULT_PATH.with_name("insurance_official.json")
_ID = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]{0,127}")
_EVIDENCE_ID = re.compile(r"[A-Za-z][A-Za-z0-9_-]{0,127}")
_ALIASES = {
    "coverage": "保障 责任 住院 门诊 门急诊 特殊门诊 手术",
    "deductible": "免赔 自付 起付 门槛 deductible",
    "reimbursement": "赔付 报销 比例 百分比 reimbursement",
    "hospital": "医院 公立 私立 普通部 特需 国际部 hospital",
    "waiting_period": "等待期 等待 疾病 意外 waiting period",
    "renewal": "续保 保证 年限 费率 renewal",
    "exclusions": "除外 免责 不保 排除 exclusions",
    "premium": "保费 价格 报价 多少钱 预算 premium price",
    "underwriting": "健康 告知 核保 体检 既往症 能买 投保 underwriting",
}


def _text(value, label):
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{label} 必须是非空字符串。")


def _identifier(value, label, pattern=_ID):
    if not isinstance(value, str) or not pattern.fullmatch(value):
        raise ValueError(f"{label} 不是有效标识。")


def _date(value, label, *, nullable=False):
    if value is None and nullable:
        return
    if not isinstance(value, str) or not re.fullmatch(r"\d{4}-\d{2}-\d{2}", value):
        raise ValueError(f"{label} 必须是 YYYY-MM-DD 日期。")
    try:
        date.fromisoformat(value)
    except ValueError as error:
        raise ValueError(f"{label} 不是有效日期。") from error


def _validate_source(source, data_kind):
    if not isinstance(source, dict):
        raise ValueError("source 必须是对象。")
    for key in ("title", "locator"):
        _text(source.get(key), f"source.{key}")
    _date(source.get("checked_at"), "source.checked_at")
    if "effective_date" not in source:
        raise ValueError("source 必须注明 effective_date；未知时使用 null。")
    _date(source["effective_date"], "source.effective_date", nullable=True)
    url = source.get("url")
    if not isinstance(url, str):
        raise ValueError("source.url 必须是字符串。")
    if not url:
        if data_kind != "synthetic":
            raise ValueError("官方资料必须提供 http(s) 来源链接。")
        return
    try:
        parsed = urlsplit(url)
        valid = (parsed.scheme in {"http", "https"} and bool(parsed.hostname)
                 and parsed.username is None and parsed.password is None
                 and not re.search(r"\s", url))
        parsed.port  # 同时检查端口是否有效。
    except ValueError as error:
        raise ValueError("source.url 不是有效的 http(s) 链接。") from error
    if not valid:
        raise ValueError("source.url 只接受无凭据的 http(s) 链接；自拟资料可为空。")


def _validate(payload):
    if not isinstance(payload, dict) or type(payload.get("schema_version")) is not int or payload["schema_version"] != 1:
        raise ValueError("目录必须使用 schema_version=1。")
    products = payload.get("products")
    if not isinstance(products, list) or not products:
        raise ValueError("products 必须是非空列表。")
    identities, evidence_ids = set(), set()
    for product in products:
        if not isinstance(product, dict):
            raise ValueError("产品记录必须是对象。")
        _identifier(product.get("product_id"), "product_id")
        _identifier(product.get("version"), "version")
        _text(product.get("name"), "name")
        identity = (product["product_id"], product["version"])
        if identity in identities:
            raise ValueError("产品与版本组合不能重复。")
        identities.add(identity)
        if product.get("data_kind") not in ("synthetic", "official_excerpt"):
            raise ValueError("data_kind 必须为 synthetic 或 official_excerpt。")
        _validate_source(product.get("source"), product["data_kind"])
        facts = product.get("facts")
        if not isinstance(facts, list) or not facts:
            raise ValueError("facts 必须是非空列表。")
        dimensions = set()
        for fact in facts:
            if not isinstance(fact, dict):
                raise ValueError("事实记录必须是对象。")
            _identifier(fact.get("evidence_id"), "evidence_id", _EVIDENCE_ID)
            if fact["evidence_id"] in evidence_ids:
                raise ValueError("evidence_id 必须在整个目录中唯一。")
            evidence_ids.add(fact["evidence_id"])
            dimension = fact.get("dimension")
            if not isinstance(dimension, str) or dimension not in DIMENSIONS:
                raise ValueError("事实 dimension 不在支持的九个维度中。")
            dimensions.add(dimension)
            if fact.get("status") not in ("known", "unknown", "conflict"):
                raise ValueError("事实 status 必须为 known、unknown 或 conflict。")
            _text(fact.get("text"), "fact.text")
            _text(fact.get("locator"), "fact.locator")
            conditions = fact.get("conditions")
            if not isinstance(conditions, list):
                raise ValueError("conditions 必须是字符串列表。")
            for condition in conditions:
                _text(condition, "condition")
        if dimensions != set(DIMENSIONS):
            missing = ", ".join(sorted(set(DIMENSIONS) - dimensions))
            raise ValueError(f"每个产品版本必须覆盖九个维度；缺少：{missing}。")
    return products


class Catalog:
    """独立产品版本目录。不存在或跨产品的查询均明确报错，不降级到其他版本。"""

    def __init__(self, path=None):
        self.path = Path(path) if path is not None else DEFAULT_PATH
        try:
            payload = json.loads(self.path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as error:
            raise ValueError("产品目录不是有效 JSON。") from error
        products = _validate(payload)
        self._products = {(p["product_id"], p["version"]): deepcopy(p) for p in products}
        canonical = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        self.fingerprint = hashlib.sha256(canonical.encode("utf-8")).hexdigest()

    def _product(self, product_id, version):
        _identifier(product_id, "product_id")
        _identifier(version, "version")
        try:
            return self._products[(product_id, version)]
        except KeyError as error:
            raise ValueError(f"目录中没有产品版本：{product_id} / {version}。") from error

    @staticmethod
    def _fact(product, fact):
        return deepcopy({**fact, "product_id": product["product_id"], "version": product["version"],
                         "product_name": product["name"], "data_kind": product["data_kind"],
                         "source": product["source"]})

    def list_products(self):
        return [deepcopy({key: value for key, value in product.items() if key != "facts"})
                for product in self._products.values()]

    def get_product(self, product_id, version):
        product = self._product(product_id, version)
        result = deepcopy(product)
        result["facts"] = [self._fact(product, fact) for fact in product["facts"]]
        return result

    def read(self, product_id, version, evidence_id):
        product = self._product(product_id, version)
        _identifier(evidence_id, "evidence_id", _EVIDENCE_ID)
        for fact in product["facts"]:
            if fact["evidence_id"] == evidence_id:
                return self._fact(product, fact)
        raise ValueError("该证据不属于选定的产品版本。")

    def facts(self, product_id, version, dimension):
        product = self._product(product_id, version)
        if not isinstance(dimension, str) or dimension not in DIMENSIONS:
            raise ValueError("dimension 不在支持的九个维度中。")
        return [self._fact(product, fact) for fact in product["facts"] if fact["dimension"] == dimension]

    def search(self, product_id, version, query, limit=3):
        """在选定版本内按字面词项排序；未知事实也可命中，不能当作肯定保障。"""
        product = self._product(product_id, version)
        _text(query, "query")
        if type(limit) is not int or limit < 1:
            raise ValueError("limit 必须是正整数。")
        terms = set(tokenize(query))
        records = []
        for fact in product["facts"]:
            dimension = fact["dimension"]
            text = " ".join([dimension, DIMENSIONS[dimension], _ALIASES[dimension],
                             fact["text"], *fact["conditions"]])
            records.append((fact, set(tokenize(text))))
        scored = []
        for fact, tokens in records:
            matched = terms & tokens
            if not matched:
                continue
            score = sum(math.log(1 + len(records) / sum(term in others for _, others in records))
                        for term in matched)
            # 明确维度名称优先，避免其在其他条款的交叉引用挤掉本维度。
            label = DIMENSIONS[fact["dimension"]]
            if fact["dimension"] in query.casefold() or label in query:
                score += 2.0
            scored.append((score, fact))
        scored.sort(key=lambda item: (-item[0], item[1]["evidence_id"]))
        return [self._fact(product, fact) for _, fact in scored[:limit]]
