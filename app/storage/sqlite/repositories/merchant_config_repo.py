"""商家设置仓储。"""
from __future__ import annotations

from ..connection import SqliteConnection
from ..models import MerchantConfigDTO


class MerchantConfigRepo:
    """商家设置仓储，单例模式（只有一条配置记录）。"""

    @staticmethod
    async def get() -> MerchantConfigDTO:
        """获取商家配置（不存在则返回默认值）。"""
        row = await SqliteConnection.fetchone(
            "SELECT * FROM merchant_config WHERE id=1"
        )
        if not row:
            return MerchantConfigDTO()
        return MerchantConfigDTO(**{k: row[k] for k in MerchantConfigDTO.__annotations__ if k in row})

    @staticmethod
    async def save(shop_name: str | None = None,
                   shop_logo: str | None = None,
                   service_hours: str | None = None,
                   auto_reply: str | None = None,
                   auto_reply_enabled: int | None = None,
                   support_contact: str | None = None) -> None:
        """保存商家配置（upsert）。"""
        sets: list[str] = []
        params: list = []
        if shop_name is not None:
            sets.append("shop_name=?")
            params.append(shop_name)
        if shop_logo is not None:
            sets.append("shop_logo=?")
            params.append(shop_logo)
        if service_hours is not None:
            sets.append("service_hours=?")
            params.append(service_hours)
        if auto_reply is not None:
            sets.append("auto_reply=?")
            params.append(auto_reply)
        if auto_reply_enabled is not None:
            sets.append("auto_reply_enabled=?")
            params.append(auto_reply_enabled)
        if support_contact is not None:
            sets.append("support_contact=?")
            params.append(support_contact)

        sets.append("updated_at=datetime('now')")

        existing = await SqliteConnection.fetchone("SELECT id FROM merchant_config WHERE id=1")
        if existing:
            await SqliteConnection.write_with_lock(
                "merchant_config",
                f"UPDATE merchant_config SET {', '.join(sets)} WHERE id=1",
                tuple(params),
            )
        else:
            cols = [s.replace("=?", "") for s in sets if s != "updated_at=datetime('now')"]
            placeholders = ", ".join(["?" for _ in cols])
            await SqliteConnection.write_with_lock(
                "merchant_config",
                f"INSERT INTO merchant_config ({', '.join(cols)}) VALUES ({placeholders})",
                tuple(params),
            )


merchant_config_repo = MerchantConfigRepo()