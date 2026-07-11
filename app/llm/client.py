"""统一 LLM 调用客户端：OpenAI 兼容协议。

所有 Agent 只能通过此模块调 LLM，禁止直接 new client。
支持按 agent_name 切换模型/API 地址/温度等参数。
"""
from __future__ import annotations

import json
import time
from typing import Any, AsyncIterator

from openai import AsyncOpenAI

from config.settings import settings
from app.logger import get_logger
from app.logger.tracer import TraceContext

from .circuit_breaker import llm_circuit
from .retry import with_retry
from .formatter import repair_output

_log = get_logger("llm.client")


class LLMError(Exception):
    """LLM 调用异常。"""


class LLMResponse:
    def __init__(self, content: str, tool_calls: list[dict] | None = None,
                 prompt_tokens: int = 0, completion_tokens: int = 0,
                 model: str = "", raw: Any = None):
        self.content = content
        self.tool_calls = tool_calls or []
        self.prompt_tokens = prompt_tokens
        self.completion_tokens = completion_tokens
        self.model = model
        self.raw = raw


class LLMClient:
    def __init__(self):
        self._clients: dict[str, AsyncOpenAI] = {}

    def _get_client(self, base_url: str | None = None, api_key: str | None = None) -> AsyncOpenAI:
        """按 (base_url, api_key) 获取或创建客户端。"""
        key = f"{base_url or settings.LLM_BASE_URL}:{api_key or settings.LLM_API_KEY or 'empty'}"
        if key not in self._clients:
            self._clients[key] = AsyncOpenAI(
                base_url=base_url or settings.LLM_BASE_URL,
                api_key=api_key or settings.LLM_API_KEY or "empty",
                timeout=settings.LLM_TIMEOUT,
            )
        return self._clients[key]

    async def _resolve_config(self, agent_name: str | None) -> dict[str, Any]:
        """解析 Agent 级别的模型配置，未配置的字段返回 None 表示使用全局默认。"""
        if not agent_name:
            return {}
        try:
            from app.storage.sqlite.repositories.agent_model_repo import agent_model_repo
            cfg = await agent_model_repo.get_config(agent_name)
            return cfg or {}
        except Exception as e:
            _log.debug(f"获取 Agent 模型配置失败: {agent_name} - {e}")
            return {}

    async def chat(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]] | None = None,
        temperature: float | None = None,
        max_tokens: int | None = None,
        agent_name: str | None = None,
        session_id: str | None = None,
    ) -> LLMResponse:
        """同步对话。受熔断 + 重试保护。"""
        if not llm_circuit.allow():
            raise LLMError("熔断器开启，拒绝请求")

        # 解析 Agent 模型配置
        agent_cfg = await self._resolve_config(agent_name)
        model = agent_cfg.get("model") or settings.LLM_MODEL
        base_url = agent_cfg.get("base_url") or None
        api_key = agent_cfg.get("api_key") or None
        temp = temperature if temperature is not None else (
            agent_cfg.get("temperature") if agent_cfg.get("temperature") is not None else settings.LLM_TEMPERATURE
        )
        tok = max_tokens or (
            agent_cfg.get("max_tokens") if agent_cfg.get("max_tokens") is not None else settings.LLM_MAX_TOKENS
        )

        client = self._get_client(base_url, api_key)

        async def _call() -> Any:
            nonlocal client
            # 如果 base_url/api_key 变了，重新获取客户端
            client = self._get_client(base_url, api_key)
            return await client.chat.completions.create(
                model=model,
                messages=messages,
                tools=tools,
                temperature=temp,
                max_tokens=tok,
            )

        try:
            resp = await with_retry(_call)
        except Exception as e:
            llm_circuit.record_failure()
            _log.error(f"LLM 调用失败 (agent={agent_name}, model={model})：{e}")
            raise LLMError(str(e)) from e

        llm_circuit.record_success()
        choice = resp.choices[0]
        msg = choice.message
        content = repair_output(msg.content or "")
        tool_calls: list[dict] = []
        if msg.tool_calls:
            for tc in msg.tool_calls:
                tool_calls.append({
                    "id": tc.id,
                    "type": "function",
                    "function": {
                        "name": tc.function.name,
                        "arguments": tc.function.arguments if isinstance(tc.function.arguments, str)
                                    else json.dumps(tc.function.arguments, ensure_ascii=False),
                    },
                })

        usage = resp.usage
        prompt_t = usage.prompt_tokens if usage else 0
        completion_t = usage.completion_tokens if usage else 0

        # 落库 token 用量
        try:
            from app.storage.sqlite.repositories.log_repo import log_repo
            await log_repo.insert_token_usage(
                trace_id=TraceContext.current(), session_id=session_id,
                agent_name=agent_name, model=model,
                prompt_tokens=prompt_t, completion_tokens=completion_t,
            )
        except Exception as e:
            _log.debug(f"记录 token 用量失败：{e}")

        return LLMResponse(
            content=content, tool_calls=tool_calls,
            prompt_tokens=prompt_t, completion_tokens=completion_t,
            model=model, raw=resp,
        )

    async def chat_stream(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]] | None = None,
        temperature: float | None = None,
        agent_name: str | None = None,
        session_id: str | None = None,
    ) -> AsyncIterator[str]:
        """流式对话，yield content delta。"""
        if not llm_circuit.allow():
            raise LLMError("熔断器开启，拒绝请求")

        # 解析 Agent 模型配置
        agent_cfg = await self._resolve_config(agent_name)
        model = agent_cfg.get("model") or settings.LLM_MODEL
        base_url = agent_cfg.get("base_url") or None
        api_key = agent_cfg.get("api_key") or None
        temp = temperature if temperature is not None else (
            agent_cfg.get("temperature") if agent_cfg.get("temperature") is not None else settings.LLM_TEMPERATURE
        )
        tok = max_tokens or (
            agent_cfg.get("max_tokens") if agent_cfg.get("max_tokens") is not None else settings.LLM_MAX_TOKENS
        )

        client = self._get_client(base_url, api_key)

        async def _call():
            nonlocal client
            client = self._get_client(base_url, api_key)
            return await client.chat.completions.create(
                model=model,
                messages=messages,
                tools=tools,
                temperature=temp,
                max_tokens=tok,
                stream=True,
            )

        try:
            stream = await with_retry(_call)
        except Exception as e:
            llm_circuit.record_failure()
            raise LLMError(str(e)) from e

        llm_circuit.record_success()
        async for chunk in stream:
            try:
                delta = chunk.choices[0].delta
                if delta and delta.content:
                    yield delta.content
            except Exception:
                continue


llm_client = LLMClient()


async def chat(messages: list[dict], **kwargs) -> LLMResponse:
    return await llm_client.chat(messages, **kwargs)


async def chat_stream(messages: list[dict], **kwargs) -> AsyncIterator[str]:
    async for x in llm_client.chat_stream(messages, **kwargs):
        yield x