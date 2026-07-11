"""把 config/prompts/*.md 种子提示词导入 DB prompt_versions 表。"""
from __future__ import annotations

import asyncio
from pathlib import Path

from config.settings import PROMPTS_SEED_DIR
from app.prompts.service import prompt_service
from app.storage.sqlite.repositories.prompt_repo import prompt_repo
from app.logger import setup_logging, get_logger


async def main() -> None:
    setup_logging()
    log = get_logger("seed_prompts")

    for md in sorted(PROMPTS_SEED_DIR.glob("*.md")):
        agent_name = md.stem
        content = md.read_text(encoding="utf-8")
        existing = await prompt_repo.get_active(agent_name)
        if existing:
            log.info(f"跳过 {agent_name}（已有启用版本 v{existing.version_no}）")
            continue
        vid = await prompt_service.save_version(
            agent_name=agent_name, content=content,
            change_note="seed 初始化导入", created_by="system",
        )
        log.info(f"导入 {agent_name} -> v{vid}")


if __name__ == "__main__":
    asyncio.run(main())
