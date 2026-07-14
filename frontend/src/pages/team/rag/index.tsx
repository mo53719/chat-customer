import { useEffect, useState, useRef } from "react";
import {
  Card, Table, Upload, Button, message, Space, Tag, Modal,
  InputNumber, Progress, Typography, Descriptions, Divider, Drawer, Tooltip,
} from "antd";
import { UploadOutlined, SettingOutlined, EyeOutlined, HistoryOutlined } from "@ant-design/icons";
import { knowledgeApi } from "../../../api";

const { Text } = Typography;

const PHASE_LABELS: Record<string, string> = {
  splitting: "文本切分",
  embedding: "向量化",
  upserting: "入库",
  done: "完成",
  error: "失败",
};

export default function KnowledgePage() {
  const [rows, setRows] = useState<any[]>([]);
  const [uploadModal, setUploadModal] = useState(false);
  const [configModal, setConfigModal] = useState(false);
  const [chunkSize, setChunkSize] = useState(400);
  const [overlap, setOverlap] = useState(80);
  const [uploading, setUploading] = useState(false);
  const [progress, setProgress] = useState<any>(null);
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const wsRef = useRef<WebSocket | null>(null);

  // ── 切片查看 ──────────────────────────────────────────────
  const [chunkDrawer, setChunkDrawer] = useState(false);
  const [chunks, setChunks] = useState<any[]>([]);
  const [chunkDocTitle, setChunkDocTitle] = useState("");

  // ── 去重弹窗 ──────────────────────────────────────────────
  const [dupModal, setDupModal] = useState(false);
  const [dupInfo, setDupInfo] = useState<any>(null);
  const [dupFile, setDupFile] = useState<File | null>(null);

  // ── 版本历史 ──────────────────────────────────────────────
  const [verModal, setVerModal] = useState(false);
  const [versions, setVersions] = useState<any[]>([]);
  const [verDocId, setVerDocId] = useState("");

  // ── 加载 ──────────────────────────────────────────────────
  const loadDocs = async () => {
    try {
      const r: any = await knowledgeApi.list();
      setRows(r.data || []);
    } catch (e: any) { message.error(e.message); }
  };

  const loadConfig = async () => {
    try {
      const r: any = await knowledgeApi.config();
      if (r.data) {
        setChunkSize(r.data.chunk_size || 400);
        setOverlap(r.data.overlap || 80);
      }
    } catch (e: any) { /* 首次无配置忽略 */ }
  };

  useEffect(() => { loadDocs(); loadConfig(); }, []);

  useEffect(() => {
    return () => { wsRef.current?.close(); };
  }, []);

  // ── 上传 ──────────────────────────────────────────────────
  const doUpload = async (action: string = "new") => {
    const file = selectedFile || dupFile;
    if (!file) return;
    setUploading(true);
    setUploadModal(false);
    setDupModal(false);
    setProgress(null);

    try {
      const r: any = await knowledgeApi.upload(
        file, file.name, chunkSize, overlap, action,
        dupInfo?.existing_doc?.doc_id,
      );
      const data = r.data || r;
      if (data?.status === "duplicate") {
        // 去重弹窗
        setDupInfo(data);
        setDupFile(file);
        setDupModal(true);
        setUploading(false);
        return;
      }
      const docId = data?.doc_id;
      if (!docId) throw new Error("未获取到文档 ID");

      const proto = window.location.protocol === "https:" ? "wss" : "ws";
      const ws = new WebSocket(`${proto}://${window.location.host}/api/knowledge/ws/${docId}`);
      wsRef.current = ws;

      ws.onmessage = (e) => {
        const p = JSON.parse(e.data);
        setProgress(p);
        if (p.phase === "done" || p.phase === "error") {
          ws.close();
          wsRef.current = null;
          setUploading(false);
          setSelectedFile(null);
          setDupFile(null);
          loadDocs();
        }
      };
      ws.onerror = () => {
        message.error("WebSocket 连接失败，请刷新页面后查看状态");
        setUploading(false);
        loadDocs();
      };
    } catch (e: any) {
      message.error(e.message || "上传失败");
      setUploading(false);
    }
  };

  // ── 查看切片 ──────────────────────────────────────────────
  const openChunks = async (docId: string, title: string) => {
    setChunkDocTitle(title);
    setChunkDrawer(true);
    setChunks([]);
    try {
      const r: any = await knowledgeApi.chunks(docId);
      setChunks(r.data?.chunks || []);
    } catch (e: any) {
      message.error("获取切片失败：" + e.message);
    }
  };

  // ── 版本历史 ──────────────────────────────────────────────
  const openVersions = async (docId: string) => {
    setVerDocId(docId);
    setVerModal(true);
    setVersions([]);
    try {
      const r: any = await knowledgeApi.versions(docId);
      setVersions(r.data?.versions || []);
    } catch (e: any) {
      message.error("获取版本历史失败：" + e.message);
    }
  };

  // ── 配置保存 ──────────────────────────────────────────────
  const saveConfig = async () => {
    try {
      await knowledgeApi.saveConfig(chunkSize, overlap);
      message.success("默认配置已保存");
      setConfigModal(false);
    } catch (e: any) { message.error(e.message); }
  };

  // ── 删除 ──────────────────────────────────────────────────
  const confirmRemove = (docId: string, title: string) => {
    Modal.confirm({
      title: "确认删除该文档？",
      content: (
        <div>
          <div>文档：<b>{title}</b></div>
          <div style={{ color: "#8c8c8c", fontSize: 12, marginTop: 4 }}>
            将从 Qdrant 中移除全部向量切片，并写入回收站。
          </div>
        </div>
      ),
      okText: "删除",
      okButtonProps: { danger: true },
      cancelText: "取消",
      onOk: async () => {
        try {
          await knowledgeApi.remove(docId);
          message.success("已删除");
          loadDocs();
        } catch (e: any) {
          message.error("删除失败：" + (e.message || "未知错误"));
        }
      },
    });
  };

  return (
    <div>
      {/* ── 进度卡片 ────────────────────────────────────────── */}
      {(uploading || progress) && (
        <Card
          title={
            <Space>
              <span>向量化进度</span>
              {progress?.phase && (
                <Tag color={progress.phase === "error" ? "red" : progress.phase === "done" ? "green" : "blue"}>
                  {PHASE_LABELS[progress.phase] || progress.phase}
                </Tag>
              )}
            </Space>
          }
          style={{ marginBottom: 16 }}
        >
          <Progress
            percent={progress?.pct ?? 0}
            status={progress?.phase === "error" ? "exception" : progress?.phase === "done" ? "success" : "active"}
            format={(pct) => {
              if (progress?.phase === "error") return "失败";
              if (progress?.phase === "done") return "完成";
              return `${pct}%`;
            }}
          />
          {progress?.message && (
            <Text type="secondary" style={{ display: "block", marginTop: 8 }}>
              {progress.message}
            </Text>
          )}
        </Card>
      )}

      {/* ── 主卡片 ──────────────────────────────────────────── */}
      <Card
        title="知识库管理"
        extra={
          <Space>
            <Button
              icon={<SettingOutlined />}
              onClick={() => {
                loadConfig();
                setConfigModal(true);
              }}
            >
              默认切分配置
            </Button>
            <Button
              type="primary"
              icon={<UploadOutlined />}
              loading={uploading}
              onClick={() => setUploadModal(true)}
            >
              上传文档
            </Button>
          </Space>
        }
      >
        <Table
          rowKey="doc_id"
          dataSource={rows}
          columns={[
            { title: "标题", dataIndex: "title", ellipsis: true },
            { title: "来源", dataIndex: "source", ellipsis: true },
            { title: "类型", dataIndex: "file_type", width: 70 },
            { title: "切片数", dataIndex: "chunk_count", width: 80 },
            { title: "字数", dataIndex: "char_count", width: 80 },
            { title: "页数", dataIndex: "total_pages", width: 60 },
            {
              title: "状态", dataIndex: "status", width: 90,
              render: (s: string, r: any) => (
                <Space size={4}>
                  <Tag color={s === "ready" ? "green" : s === "failed" ? "red" : "orange"}>
                    {s === "ready" ? "就绪" : s === "failed" ? "失败" : "处理中"}
                  </Tag>
                  {r.is_current === 0 && (
                    <Tag color="default">历史版本</Tag>
                  )}
                </Space>
              ),
            },
            {
              title: "指纹", dataIndex: "file_hash", width: 100,
              render: (h: string) => h ? (
                <Tooltip title={h}><Text code style={{ fontSize: 11 }}>{h.slice(0, 8)}</Text></Tooltip>
              ) : "-",
            },
            { title: "上传时间", dataIndex: "created_at", width: 160 },
            {
              title: "操作", width: 200, fixed: "right" as const,
              render: (_: any, r: any) => (
                <Space size={0}>
                  <Button type="link" size="small" icon={<EyeOutlined />}
                    onClick={() => openChunks(r.doc_id, r.title || r.source || r.doc_id)}>
                    切片
                  </Button>
                  <Button type="link" size="small" icon={<HistoryOutlined />}
                    onClick={() => openVersions(r.doc_id)}>
                    版本
                  </Button>
                  <Button danger size="small"
                    onClick={() => confirmRemove(r.doc_id, r.title || r.source || r.doc_id)}>
                    删除
                  </Button>
                </Space>
              ),
            },
          ]}
        />
      </Card>

      {/* ── 上传弹窗 ────────────────────────────────────────── */}
      <Modal
        title="上传文档"
        open={uploadModal}
        onCancel={() => { setUploadModal(false); setSelectedFile(null); }}
        onOk={() => doUpload("new")}
        okText="开始上传"
        okButtonProps={{ disabled: !selectedFile }}
      >
        <Space direction="vertical" style={{ width: "100%" }} size="middle">
          <Upload.Dragger
            beforeUpload={(file) => { setSelectedFile(file); return false; }}
            onRemove={() => setSelectedFile(null)}
            maxCount={1}
            accept=".xlsx,.xlsm,.xls,.csv,.txt,.md,.json,.log,.pdf,.docx"
          >
            <p className="ant-upload-drag-icon">
              <UploadOutlined style={{ fontSize: 32, color: "#1677ff" }} />
            </p>
            <p>点击或拖拽文件到此处上传</p>
            <p style={{ color: "#8c8c8c", fontSize: 12 }}>
              支持 xlsx / xls / csv / txt / md / json / log / pdf / docx（最大 50MB）
            </p>
          </Upload.Dragger>

          <Divider plain style={{ fontSize: 13 }}>向量切分规则（仅对文本类文档生效）</Divider>

          <Descriptions size="small" column={2}>
            <Descriptions.Item label="每段字数">
              <InputNumber
                min={100} max={2000} step={50}
                value={chunkSize} onChange={(v) => setChunkSize(v || 400)}
                style={{ width: 120 }}
              />
              <Text type="secondary" style={{ marginLeft: 6, fontSize: 12 }}>
                默认 400 字
              </Text>
            </Descriptions.Item>
            <Descriptions.Item label="重叠字数">
              <InputNumber
                min={0} max={500} step={10}
                value={overlap} onChange={(v) => setOverlap(v || 80)}
                style={{ width: 120 }}
              />
              <Text type="secondary" style={{ marginLeft: 6, fontSize: 12 }}>
                默认 80 字
              </Text>
            </Descriptions.Item>
          </Descriptions>
          <Text type="secondary" style={{ fontSize: 12 }}>
            * 每段字数：把文档切成多长的小段；重叠字数：相邻两段之间重复多少字（防止一句话被切断）
          </Text>
        </Space>
      </Modal>

      {/* ── 去重弹窗 ────────────────────────────────────────── */}
      <Modal
        title="检测到重复文档"
        open={dupModal}
        onCancel={() => { setDupModal(false); setDupFile(null); setDupInfo(null); }}
        footer={[
          <Button key="cancel" onClick={() => { setDupModal(false); setDupFile(null); setDupInfo(null); }}>
            取消
          </Button>,
          <Button key="rebuild" onClick={() => doUpload("rebuild")}>
            重建索引
          </Button>,
          <Button key="new_version" type="primary" onClick={() => doUpload("new_version")}>
            存为新版本
          </Button>,
        ]}
      >
        <div style={{ marginBottom: 12 }}>
          <Text>
            文件「{dupInfo?.existing_doc?.title || dupFile?.name}」已存在（文件指纹相同）
          </Text>
        </div>
        <Descriptions size="small" column={1}>
          <Descriptions.Item label="原始文档">
            {dupInfo?.existing_doc?.title}（{dupInfo?.existing_doc?.source}）
          </Descriptions.Item>
          <Descriptions.Item label="上传时间">
            {dupInfo?.existing_doc?.created_at}
          </Descriptions.Item>
        </Descriptions>
        <Divider />
        <Text type="secondary" style={{ fontSize: 12 }}>
          · 重建索引：删除旧向量后重新入库（不保留历史）<br />
          · 存为新版本：旧版本自动失效、新版本生效（保留历史）
        </Text>
      </Modal>

      {/* ── 配置弹窗 ────────────────────────────────────────── */}
      <Modal
        title="默认切分配置"
        open={configModal}
        onCancel={() => setConfigModal(false)}
        onOk={saveConfig}
        okText="保存"
      >
        <Space direction="vertical" style={{ width: "100%" }}>
          <Descriptions size="small" column={1}>
            <Descriptions.Item label="每段字数（默认值）">
              <InputNumber
                min={100} max={2000} step={50}
                value={chunkSize} onChange={(v) => setChunkSize(v || 400)}
                style={{ width: 160 }}
              />
            </Descriptions.Item>
            <Descriptions.Item label="重叠字数（默认值）">
              <InputNumber
                min={0} max={500} step={10}
                value={overlap} onChange={(v) => setOverlap(v || 80)}
                style={{ width: 160 }}
              />
            </Descriptions.Item>
          </Descriptions>
          <Text type="secondary" style={{ fontSize: 12 }}>
            * 每段字数：把文档切成多长的小段；重叠字数：相邻两段之间重复多少字（防止一句话被切断）
          </Text>
        </Space>
      </Modal>

      {/* ── 切片查看 Drawer ──────────────────────────────────── */}
      <Drawer
        title={`切片详情 - ${chunkDocTitle}`}
        open={chunkDrawer}
        onClose={() => setChunkDrawer(false)}
        width={700}
      >
        {chunks.length === 0 ? (
          <Text type="secondary">加载中...</Text>
        ) : (
          chunks.map((c: any, i: number) => (
            <Card
              key={c.chunk_id || i}
              size="small"
              style={{ marginBottom: 12 }}
              title={
                <Space size={4}>
                  <Tag color="blue">#{c.chunk_idx !== undefined ? c.chunk_idx + 1 : i + 1}</Tag>
                  {c.chunk_id && (
                    <Tooltip title={c.chunk_id}>
                      <Text code copyable={{ text: c.chunk_id }} style={{ fontSize: 11 }}>
                        {c.chunk_id.slice(0, 12)}...
                      </Text>
                    </Tooltip>
                  )}
                </Space>
              }
            >
              <Descriptions size="small" column={2} style={{ marginBottom: 8 }}>
                {c.page_no && <Descriptions.Item label="页码">第{c.page_no}页</Descriptions.Item>}
                {c.sheet && <Descriptions.Item label="工作表">{c.sheet}</Descriptions.Item>}
                {c.row && <Descriptions.Item label="行号">第{c.row}行</Descriptions.Item>}
                {c.heading_path && <Descriptions.Item label="章节">{c.heading_path}</Descriptions.Item>}
                {c.char_count && <Descriptions.Item label="字数">{c.char_count}字</Descriptions.Item>}
              </Descriptions>
              <div style={{
                background: "#fafafa", padding: 10, borderRadius: 6,
                fontSize: 13, lineHeight: 1.8, whiteSpace: "pre-wrap",
                wordBreak: "break-word",
              }}>
                {c.text}
              </div>
            </Card>
          ))
        )}
      </Drawer>

      {/* ── 版本历史 Modal ───────────────────────────────────── */}
      <Modal
        title="版本历史"
        open={verModal}
        onCancel={() => setVerModal(false)}
        footer={null}
        width={600}
      >
        <Table
          rowKey="id"
          dataSource={versions}
          pagination={false}
          columns={[
            { title: "版本", dataIndex: "version_no", width: 60, render: (v: number) => <Tag>v{v}</Tag> },
            { title: "标题", dataIndex: "title", ellipsis: true },
            { title: "来源", dataIndex: "source", ellipsis: true },
            { title: "切片数", dataIndex: "chunk_count", width: 80 },
            {
              title: "状态", dataIndex: "is_current", width: 80,
              render: (v: number) => v ? <Tag color="green">生效中</Tag> : <Tag color="default">历史</Tag>,
            },
            { title: "创建时间", dataIndex: "created_at", width: 160 },
          ]}
        />
      </Modal>
    </div>
  );
}