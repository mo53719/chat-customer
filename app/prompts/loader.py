"""提示词加载器：优先读 DB 启用版本，回退 seed 文件。"""
from __future__ import annotations

from config.settings import PROMPTS_SEED_DIR
from app.logger import get_logger
from app.storage.sqlite.repositories.prompt_repo import prompt_repo

_log = get_logger("prompts.loader")

# 简单内存缓存（agent_name -> (version_no, content)），避免每次会话都查库
_cache: dict[str, tuple[int, str]] = {}


def _candidate_names(agent_name: str) -> list[str]:
    """兼容 rag / rag_agent 两种命名。"""
    names = [agent_name]
    if agent_name.endswith("_agent"):
        names.append(agent_name[:-6])
    else:
        names.append(f"{agent_name}_agent")
    # 去重并保持顺序
    return list(dict.fromkeys(n for n in names if n))


def _cache_prompt(names: list[str], version_no: int, content: str) -> None:
    for name in names:
        _cache[name] = (version_no, content)


async def load_prompt(agent_name: str) -> str:
    """加载指定 Agent 的启用版本提示词。

    1. 先查 DB 启用版本（带缓存）
    2. DB 无则回退读 seed 文件
    3. seed 文件也无则返回空串
    """
    names = _candidate_names(agent_name)

    # 命中缓存
    for name in names:
        cached = _cache.get(name)
        if cached:
            if name != agent_name:
                _cache[agent_name] = cached
            return cached[1]

    # 读 DB
    for name in names:
        try:
            v = await prompt_repo.get_active(name)
            if v and v.content:
                _cache_prompt(names, v.version_no, v.content)
                _log.debug(f"加载提示词 {name} v{v.version_no} (DB)")
                return v.content
        except Exception as e:
            _log.warning(f"读取 DB 提示词失败：{e}")

    # 回退 seed
    for name in names:
        seed_file = PROMPTS_SEED_DIR / f"{name}.md"
        if seed_file.exists():
            content = seed_file.read_text(encoding="utf-8")
            _cache_prompt(names, 0, content)
            _log.debug(f"加载提示词 {name} (seed 文件)")
            return content

    _log.warning(f"提示词 {agent_name} 未找到（候选={names}，DB 与 seed 均无）")
    return ""


def invalidate_cache(agent_name: str | None = None) -> None:
    """清除缓存（保存新版本后调用）。"""
    if agent_name:
        for name in _candidate_names(agent_name):
            _cache.pop(name, None)
    else:
        _cache.clear()
