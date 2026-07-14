# models/ 目录

存放本地 embedding / rerank 模型（fastembed 缓存）。

## 当前模型

| 子目录 | 模型 | 用途 | 维度/参数 |
|---|---|---|---|
| `qdrant-bge-small-zh-v1.5/` | **BAAI/bge-small-zh-v1.5**（Qdrant 优化版 ONNX） | Embedding：文档向量化 + query 向量化 | 512 维 |
| `reranker_cache/` | **BAAI/bge-reranker-base** | Rerank：向量召回后精排 | Cross-Encoder |

## 实际目录结构

```
models/
├── README.md
├── .gitignore
├── qdrant-bge-small-zh-v1.5/                # fastembed embedding 缓存根
│   └── fast-bge-small-zh-v1.5/             # ← fastembed 实际加载的子目录
│       ├── model_optimized.onnx            # 主模型（~95 MB，ONNX 格式）
│       ├── config.json
│       ├── tokenizer.json
│       ├── tokenizer_config.json
│       ├── special_tokens_map.json
│       ├── vocab.txt
│       └── ort_config.json
└── reranker_cache/                          # fastembed CrossEncoder 缓存根
    └── models--BAAI--bge-reranker-base/     # HF 标准缓存结构
        ├── refs/main
        ├── files_metadata.json
        ├── blobs/                           # 实际权重（gitignore）
        └── snapshots/2cfc18c9.../
            ├── onnx/model.onnx              # 主模型（~1.06 GB，ONNX）
            ├── config.json
            ├── tokenizer.json
            ├── tokenizer_config.json
            ├── special_tokens_map.json
            └── sentencepiece.bpe.model
```

## 加载方式（完全离线）

[app/llm/embedding.py](../app/llm/embedding.py) 和 [app/llm/reranker.py](../app/llm/reranker.py) 都设了：

```python
os.environ.setdefault("HF_HUB_OFFLINE", "1")
os.environ.setdefault("TRANSFORMERS_OFFLINE", "1")
# reranker 还显式传 local_files_only=True
```

首次启动会去 HF 下载，之后即使离线也能加载。

## 验证

```bash
# 1) embedding 维度（应输出 512、ok=True）
.\env\Scripts\python.exe -c "import asyncio; from app.llm.embedding import warmup; print(asyncio.run(warmup()))"

# 2) embedding 调用
.\env\Scripts\python.exe -c "import asyncio; from app.llm.embedding import embed_texts; v=asyncio.run(embed_texts(['你好','hello'])); print(len(v), len(v[0]))"

# 3) reranker 调用
.\env\Scripts\python.exe -c "import asyncio; from app.llm.reranker import _load_model; m=_load_model(); print(list(m.rerank(query='问候', documents=['你好','hello world'])))"
```

## 重新下载（如文件损坏）

删除对应子目录后重启后端即可，fastembed 会重新从 HF 拉取：

```powershell
Remove-Item -Recurse -Force models\qdrant-bge-small-zh-v1.5
Remove-Item -Recurse -Force models\reranker_cache
```

## 切到其他本地模型

修改 `.env`：

```text
EMBEDDING_MODEL_NAME=<hf 仓库名>      # fastembed 0.7.2 仅支持 BAAI/... 命名
EMBEDDING_LOCAL_PATH=<本地缓存路径>
EMBEDDING_DIM=<模型输出维度>
```

支持的 fastembed 模型列表：https://qdrant.github.io/fastembed/examples/Supported_Models/
