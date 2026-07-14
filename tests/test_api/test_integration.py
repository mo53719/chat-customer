"""集成测试：测试 API 接口层（需要后端服务运行中）。"""
import pytest
import httpx

BASE_URL = "http://127.0.0.1:8001"


class TestHealth:
    def test_root_returns_ok(self):
        r = httpx.get(f"{BASE_URL}/")
        assert r.status_code == 200
        data = r.json()
        assert data["status"] == "ok"
        assert data["service"] == "chat_customer"

    def test_health_endpoint(self):
        r = httpx.get(f"{BASE_URL}/health")
        assert r.status_code == 200
        assert r.json()["status"] == "healthy"

    def test_docs_available(self):
        r = httpx.get(f"{BASE_URL}/docs")
        assert r.status_code == 200

    def test_openapi_json(self):
        r = httpx.get(f"{BASE_URL}/openapi.json")
        assert r.status_code == 200
        data = r.json()
        assert "paths" in data
        assert "/health" in data["paths"]


class TestAuth:
    @pytest.fixture(scope="class")
    def test_credentials(self):
        return {"username": "test_user_api", "password": "test123456"}

    def test_register_new_user(self, test_credentials):
        r = httpx.post(f"{BASE_URL}/api/auth/register", json={
            "username": test_credentials["username"],
            "password": test_credentials["password"],
            "role": "user",
        })
        assert r.status_code in (200, 400)

    def test_login_returns_token(self, test_credentials):
        r = httpx.post(f"{BASE_URL}/api/auth/login", json={
            "username": test_credentials["username"],
            "password": test_credentials["password"],
        })
        assert r.status_code == 200
        data = r.json()
        assert "access_token" in data["data"]
        assert data["data"]["username"] == test_credentials["username"]

    def test_login_wrong_password(self):
        r = httpx.post(f"{BASE_URL}/api/auth/login", json={
            "username": "test_user_api",
            "password": "wrong_password_xyz",
        })
        assert r.status_code == 401

    def test_login_nonexistent_user(self):
        r = httpx.post(f"{BASE_URL}/api/auth/login", json={
            "username": "nonexistent_user_xyz_123",
            "password": "test123",
        })
        assert r.status_code == 401


class TestAuthenticatedEndpoints:
    @pytest.fixture(scope="class")
    def auth_headers(self):
        """获取认证 token。"""
        r = httpx.post(f"{BASE_URL}/api/auth/login", json={
            "username": "test_user_api",
            "password": "test123456",
        })
        if r.status_code != 200:
            httpx.post(f"{BASE_URL}/api/auth/register", json={
                "username": "test_user_api",
                "password": "test123456",
                "role": "user",
            })
            r = httpx.post(f"{BASE_URL}/api/auth/login", json={
                "username": "test_user_api",
                "password": "test123456",
            })
        token = r.json()["data"]["access_token"]
        return {"Authorization": f"Bearer {token}"}

    def test_auth_required_without_token(self):
        r = httpx.get(f"{BASE_URL}/api/stats/overview")
        assert r.status_code == 401

    def test_auth_required_with_token(self, auth_headers):
        r = httpx.get(f"{BASE_URL}/api/stats/overview", headers=auth_headers)
        assert r.status_code == 200
        assert "data" in r.json()

    def test_stats_dashboard(self, auth_headers):
        r = httpx.get(f"{BASE_URL}/api/stats/dashboard", headers=auth_headers)
        assert r.status_code == 200

    def test_sessions_list(self, auth_headers):
        r = httpx.get(f"{BASE_URL}/api/sessions", headers=auth_headers)
        assert r.status_code == 200

    def test_products_list(self, auth_headers):
        r = httpx.get(f"{BASE_URL}/api/products", headers=auth_headers)
        assert r.status_code == 200

    def test_orders_list(self, auth_headers):
        r = httpx.get(f"{BASE_URL}/api/orders", headers=auth_headers)
        assert r.status_code == 200

    def test_knowledge_list(self, auth_headers):
        r = httpx.get(f"{BASE_URL}/api/knowledge", headers=auth_headers)
        assert r.status_code == 200

    def test_prompts_list(self, auth_headers):
        r = httpx.get(f"{BASE_URL}/api/prompts/agents", headers=auth_headers)
        assert r.status_code == 200

    def test_badcase_list(self, auth_headers):
        r = httpx.get(f"{BASE_URL}/api/badcase/list", headers=auth_headers)
        assert r.status_code == 200

    def test_channels_list(self, auth_headers):
        r = httpx.get(f"{BASE_URL}/api/channels", headers=auth_headers)
        assert r.status_code == 200

    def test_agent_models_list(self, auth_headers):
        r = httpx.get(f"{BASE_URL}/api/agent-models/list", headers=auth_headers)
        assert r.status_code == 200

    def test_recycle_list(self, auth_headers):
        """回收站需要 admin 权限，普通用户 403。"""
        r = httpx.get(f"{BASE_URL}/api/recycle", headers=auth_headers)
        assert r.status_code == 403

    def test_logs_search(self, auth_headers):
        r = httpx.get(f"{BASE_URL}/api/logs/search", headers=auth_headers)
        assert r.status_code == 200

    def test_feedback_list(self, auth_headers):
        r = httpx.get(f"{BASE_URL}/api/feedback", headers=auth_headers)
        assert r.status_code == 200

    def test_ops_overview(self, auth_headers):
        """运维接口需要 admin 权限，普通用户 403。"""
        r = httpx.get(f"{BASE_URL}/api/ops/system-status", headers=auth_headers)
        assert r.status_code == 403


class TestApiSchemas:
    """测试 API 请求体校验。"""

    def test_login_missing_fields(self):
        r = httpx.post(f"{BASE_URL}/api/auth/login", json={})
        assert r.status_code == 422

    def test_register_missing_password(self):
        r = httpx.post(f"{BASE_URL}/api/auth/register", json={
            "username": "test",
        })
        assert r.status_code == 422

    def test_register_invalid_role(self):
        r = httpx.post(f"{BASE_URL}/api/auth/register", json={
            "username": "test2",
            "password": "test123",
            "role": "superadmin",
        })
        # 可能是 422（Pydantic 校验）或 500（枚举在 DB 层校验）
        assert r.status_code in (422, 500)

    def test_invalid_json_body(self):
        r = httpx.post(f"{BASE_URL}/api/auth/login",
                       content="not json",
                       headers={"Content-Type": "application/json"})
        assert r.status_code == 422