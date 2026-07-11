"""知识库管理路由。

解析层职责：把上传的文件解析成 List[ChunkDraft]（结构化切片 + 元数据），
返回给 knowledge_service 入库。文本类返回带分隔的整文 + source 元数据，
由 Ingestor 二次切分；表格类直接逐行产出独立 chunk，每条带 sheet/row。
"""
from __future__ import annotations

import asyncio
import codecs
import csv
import io
from dataclasses import dataclass, field
from typing import Any

from fastapi import APIRouter, Depends, UploadFile, File, Form, HTTPException, WebSocket, WebSocketDisconnect

from app.services.knowledge_service import knowledge_service
from app.storage.sqlite.repositories.knowledge_repo import knowledge_repo
from ..schemas.common import ApiResponse
from ..deps import get_current_user

router = APIRouter(prefix="/api/knowledge", tags=["知识库"])

# 单文件最大 50MB，防止 raw = await file.read() 把内存撑爆
MAX_UPLOAD_BYTES = 50 * 1024 * 1024

# ── 进度管理器（内存） ────────────────────────────────────────
_progress: dict[str, dict[str, Any]] = {}
_ws_clients: dict[str, list[WebSocket]] = {}


async def _broadcast_progress(doc_id: str, phase: str, current: int, total: int, message: str):
    """更新进度并推送给所有在听的 WebSocket 客户端。"""
    pct = round(current / total * 100, 1) if total > 0 else 0
    payload = {
        "doc_id": doc_id,
        "phase": phase,
        "current": current,
        "total": total,
        "message": message,
        "pct": pct,
    }
    _progress[doc_id] = payload
    dead: list[WebSocket] = []
    for ws in _ws_clients.get(doc_id, []):
        try:
            await ws.send_json(payload)
        except Exception:
            dead.append(ws)
    for ws in dead:
        _ws_clients.get(doc_id, []).remove(ws)


async def _process_doc(doc_id: str, title: str, drafts: list, file_type: str,
                       source: str, uploaded_by: str, chunk_size: int, overlap: int):
    """后台处理：向量化 + 入库，同时推送进度。"""
    async def _cb(phase, cur, tot, msg):
        await _broadcast_progress(doc_id, phase, cur, tot, msg)

    await knowledge_service.upload_drafts(
        title=title, drafts=drafts, file_type=file_type,
        source=source, uploaded_by=uploaded_by,
        chunk_size=chunk_size, overlap=overlap,
        progress_callback=_cb,
    )


@dataclass
class ChunkDraft:
    """解析器产出的最小切片单元。"""
    content: str
    source: str = ""
    sheet: str | None = None
    row: int | None = None
    heading_path: str | None = None   # 例如 "Sheet1 > 退费政策 > 时效"
    extra: dict[str, Any] = field(default_factory=dict)


def _decode_text(raw: bytes) -> str:
    """智能识别文本编码（utf-8 / utf-8-sig / gbk / gb18030）。"""
    if not raw:
        return ""
    if raw[:3] == b"\xef\xbb\xbf":
        return raw[3:].decode("utf-8", errors="ignore")
    try:
        return raw.decode("utf-8")
    except UnicodeDecodeError:
        pass
    for enc in ("gbk", "gb18030"):
        try:
            return raw.decode(enc)
        except UnicodeDecodeError:
            continue
    return raw.decode("utf-8", errors="ignore")


def _parse_xlsx(raw: bytes, source: str) -> list[ChunkDraft]:
    """从 .xlsx / .xlsm 按行产出 ChunkDraft。处理合并单元格表头。"""
    from openpyxl import load_workbook
    from openpyxl.utils import range_boundaries
    wb = load_workbook(io.BytesIO(raw), read_only=False, data_only=True)
    drafts: list[ChunkDraft] = []

    for sheet in wb.worksheets:
        # 解析合并单元格，把左上角的值回填到合并区域所有 cell
        merged_values: dict[tuple[int, int], Any] = {}
        if hasattr(sheet, "merged_cells") and sheet.merged_cells.ranges:
            for mr in sheet.merged_cells.ranges:
                min_col, min_row, max_col, max_row = range_boundaries(str(mr))
                top_val = sheet.cell(row=min_row, column=min_col).value
                for r in range(min_row, max_row + 1):
                    for c in range(min_col, max_col + 1):
                        merged_values[(r, c)] = top_val

        rows_iter = sheet.iter_rows(values_only=False)
        try:
            header_row = next(rows_iter)
        except StopIteration:
            continue
        # 表头：合并单元格优先，否则取 cell.value
        headers: list[str] = []
        for cell in header_row:
            v = merged_values.get((cell.row, cell.column), cell.value)
            headers.append(str(v).strip() if v is not None else f"col{cell.column}")

        for row in rows_iter:
            if all((c.value is None or (isinstance(c.value, str) and not c.value.strip()))
                   and (c.row, c.column) not in merged_values for c in row):
                continue
            cells = []
            for cell in row:
                v = merged_values.get((cell.row, cell.column), cell.value)
                if v is None:
                    continue
                s = str(v).strip()
                if not s:
                    continue
                idx = cell.column - 1
                h = headers[idx] if idx < len(headers) else f"col{cell.column}"
                cells.append(f"{h}: {s}")
            if cells:
                drafts.append(ChunkDraft(
                    content=" | ".join(cells),
                    source=source,
                    sheet=sheet.title,
                    row=row[0].row,
                    heading_path=sheet.title,
                ))
    wb.close()
    return drafts


def _parse_xls(raw: bytes, source: str) -> list[ChunkDraft]:
    """从老格式 .xls 按行解析（要求 xlrd<2.0.0）。"""
    try:
        import xlrd
    except ImportError:
        raise HTTPException(status_code=400, detail=".xls 暂不支持，请另存为 .xlsx 后再上传")
    if hasattr(xlrd, "__version__") and not xlrd.__version__.startswith("1."):
        raise HTTPException(status_code=400, detail=".xls 需要 xlrd<2.0.0，请联系管理员")
    book = xlrd.open_workbook(file_contents=raw)
    drafts: list[ChunkDraft] = []
    for sheet in book.sheets():
        if sheet.nrows == 0:
            continue
        headers = [str(sheet.cell_value(0, c)).strip() or f"col{c}" for c in range(sheet.ncols)]
        for r in range(1, sheet.nrows):
            row = sheet.row_values(r)
            if all(c == "" or c is None for c in row):
                continue
            cells = []
            for h, v in zip(headers, row):
                if v == "" or v is None:
                    continue
                cells.append(f"{h}: {v}")
            if cells:
                drafts.append(ChunkDraft(
                    content=" | ".join(cells),
                    source=source,
                    sheet=sheet.name,
                    row=r + 1,
                    heading_path=sheet.name,
                ))
    return drafts


def _parse_csv(raw: bytes, source: str) -> list[ChunkDraft]:
    """CSV 按行解析，每行一个 chunk。"""
    text = _decode_text(raw)
    reader = csv.reader(io.StringIO(text))
    try:
        headers = next(reader)
    except StopIteration:
        return []
    headers = [h.strip() or f"col{i}" for i, h in enumerate(headers)]
    drafts: list[ChunkDraft] = []
    for r_idx, row in enumerate(reader, start=2):  # 数据从第 2 行起
        if not row or all(not c.strip() for c in row):
            continue
        cells = []
        for h, v in zip(headers, row):
            if not v or not v.strip():
                continue
            cells.append(f"{h}: {v.strip()}")
        if cells:
            drafts.append(ChunkDraft(
                content=" | ".join(cells),
                source=source,
                sheet=None,
                row=r_idx,
                heading_path=source,
            ))
    return drafts


def _parse_plain(raw: bytes, source: str) -> list[ChunkDraft]:
    """txt/md/json/log 整文返回，由 Ingestor 二次切分。"""
    text = _decode_text(raw)
    if not text.strip():
        return []
    return [ChunkDraft(content=text, source=source, heading_path=source)]


def _extract_chunks(raw: bytes, ext: str, source: str) -> list[ChunkDraft]:
    """根据扩展名分发到不同解析器，统一返回 ChunkDraft 列表。"""
    ext = (ext or "").lower().lstrip(".")
    if ext in ("xlsx", "xlsm"):
        return _parse_xlsx(raw, source)
    if ext == "xls":
        return _parse_xls(raw, source)
    if ext == "csv":
        return _parse_csv(raw, source)
    # txt / md / json / log
    return _parse_plain(raw, source)


def _ext_of(filename: str | None) -> str:
    if not filename or "." not in filename:
        return "txt"
    return filename.rsplit(".", 1)[-1].lower()


@router.get("", response_model=ApiResponse)
async def list_docs(user: dict = Depends(get_current_user)):
    return ApiResponse(data=await knowledge_service.list_docs())


@router.websocket("/ws/{doc_id}")
async def ws_progress(websocket: WebSocket, doc_id: str):
    """WebSocket 进度推送：前端连接后接收实时向量化进度。"""
    await websocket.accept()
    _ws_clients.setdefault(doc_id, []).append(websocket)
    # 如果已有进度，立即发送当前状态
    if doc_id in _progress:
        await websocket.send_json(_progress[doc_id])
    try:
        while True:
            await websocket.receive_text()  # 保持连接，接收心跳
    except (WebSocketDisconnect, Exception):
        pass
    finally:
        _ws_clients.get(doc_id, []).remove(websocket)


@router.get("/config", response_model=ApiResponse)
async def get_config(user: dict = Depends(get_current_user)):
    return ApiResponse(data=await knowledge_repo.get_config())


@router.post("/config", response_model=ApiResponse)
async def save_config(data: dict[str, Any], user: dict = Depends(get_current_user)):
    await knowledge_repo.save_config(
        chunk_size=int(data.get("chunk_size", 400)),
        overlap=int(data.get("overlap", 80)),
    )
    return ApiResponse(message="配置已保存")


@router.post("/upload", response_model=ApiResponse)
async def upload(file: UploadFile = File(...),
                 title: str = Form(None),
                 chunk_size: int = Form(400),
                 overlap: int = Form(80),
                 user: dict = Depends(get_current_user)):
    raw = await file.read()
    if not raw:
        raise HTTPException(status_code=400, detail="文件为空")
    if len(raw) > MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=413, detail="文件过大，最大支持 50MB")

    ext = _ext_of(file.filename)
    if ext not in ("xlsx", "xlsm", "xls", "csv", "txt", "md", "json", "log"):
        raise HTTPException(
            status_code=400,
            detail=f"暂不支持 .{ext} 格式（仅支持 xlsx / xls / csv / txt / md / json）",
        )

    try:
        drafts = _extract_chunks(raw, ext, source=file.filename or "")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"文件解析失败：{e}")

    if not drafts:
        raise HTTPException(status_code=400, detail="文件解析后无可用内容")

    title = title or file.filename or "未命名"
    # 先创建记录（状态 processing），然后后台异步处理
    import uuid as _uuid
    doc_id = f"doc_{_uuid.uuid4().hex[:16]}"
    await knowledge_repo.create(doc_id, title, file.filename, ext, user["username"])

    asyncio.create_task(_process_doc(
        doc_id=doc_id, title=title, drafts=drafts, file_type=ext,
        source=file.filename or "", uploaded_by=user["username"],
        chunk_size=chunk_size, overlap=overlap,
    ))
    return ApiResponse(data={"doc_id": doc_id, "status": "processing"})


@router.delete("/{doc_id}", response_model=ApiResponse)
async def delete_doc(doc_id: str, user: dict = Depends(get_current_user)):
    await knowledge_service.delete(doc_id, deleted_by=user["username"])
    return ApiResponse(message="已删除")
