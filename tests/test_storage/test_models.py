import pytest

from app.storage.sqlite.models import (
    ProductDTO, UserDTO, KnowledgeMetaDTO, ProductCategoryDTO,
    OrderItemDTO, AfterSalesDTO, OrderDTO, SessionDTO, MessageDTO,
    PromptVersionDTO, FeedbackDTO, FeedbackAnalysisDTO, ExampleDTO,
    DeletedRecordDTO, BadcaseDTO,
)


class TestProductDTO:
    def test_defaults(self):
        p = ProductDTO()
        assert p.sku == ""
        assert p.price == 0.0
        assert p.stock == 0
        assert p.status == "on_sale"

    def test_to_dict(self):
        p = ProductDTO(sku="SKU001", name="测试商品", price=99.9)
        d = p.to_dict()
        assert d["sku"] == "SKU001"
        assert d["name"] == "测试商品"
        assert d["price"] == 99.9

    def test_to_dict_with_none_fields(self):
        p = ProductDTO()
        d = p.to_dict()
        assert d["sku"] == ""
        assert d["brand"] is None


class TestUserDTO:
    def test_defaults(self):
        u = UserDTO()
        assert u.role == "user"
        assert u.status == "active"

    def test_to_dict(self):
        u = UserDTO(username="admin", role="admin")
        d = u.to_dict()
        assert d["username"] == "admin"
        assert d["role"] == "admin"


class TestKnowledgeMetaDTO:
    def test_defaults(self):
        k = KnowledgeMetaDTO()
        assert k.status == "processing"
        assert k.is_current == 1
        assert k.chunk_count == 0

    def test_to_dict(self):
        k = KnowledgeMetaDTO(doc_id="doc-1", title="手册", chunk_count=5)
        d = k.to_dict()
        assert d["doc_id"] == "doc-1"
        assert d["title"] == "手册"
        assert d["chunk_count"] == 5


class TestOrderItemDTO:
    def test_defaults(self):
        oi = OrderItemDTO()
        assert oi.quantity == 1
        assert oi.subtotal == 0.0


class TestAfterSalesDTO:
    def test_defaults(self):
        a = AfterSalesDTO()
        assert a.type == "return"
        assert a.status == "pending"


class TestOrderDTO:
    def test_defaults(self):
        o = OrderDTO()
        assert o.status == "pending"


class TestSessionDTO:
    def test_defaults(self):
        s = SessionDTO()
        assert s.status == "active"
        assert s.channel == "web"
        assert s.visit_count == 1


class TestMessageDTO:
    def test_defaults(self):
        m = MessageDTO()
        assert m.role == "user"
        assert m.token_input == 0
        assert m.token_output == 0


class TestPromptVersionDTO:
    def test_defaults(self):
        p = PromptVersionDTO()
        assert p.is_active == 0
        assert p.auto_generated == 0


class TestFeedbackDTO:
    def test_defaults(self):
        f = FeedbackDTO()
        assert f.rating == ""


class TestFeedbackAnalysisDTO:
    def test_defaults(self):
        fa = FeedbackAnalysisDTO()
        assert fa.id is None


class TestExampleDTO:
    def test_defaults(self):
        e = ExampleDTO()
        assert e.tag == "good"


class TestDeletedRecordDTO:
    def test_defaults(self):
        dr = DeletedRecordDTO()
        assert dr.record_id == 0


class TestBadcaseDTO:
    def test_defaults(self):
        b = BadcaseDTO()
        assert b.status == "new"
        assert b.user_input == ""