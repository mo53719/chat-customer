import { useEffect, useState, useRef } from "react";
import {
  Card, Table, Upload, Button, message, Space, Tag, Modal,
  InputNumber, Progress, Typography, Descriptions, Divider,
} from "antd";
import { UploadOutlined, SettingOutlined } from "@ant-design/icons";
import { knowledgeApi } from "../../api";

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

  // 组件卸载时断开 WebSocket
  useEffect(() => {
    return () => { wsRef.current?.close(); };
  }, []);

  // ── 上传流程 ──────────────────────────────────────────────
  const doUpload = async () => {
    if (!selectedFile) return;
    setUploading(true);
    setUploadModal(false);
    setProgress(null);

    try {
      const r: any = await knowledgeApi.upload(
        selectedFile, selectedFile.name, chunkSize, overlap
      );
      const docId = r.data?.doc_id;
      if (!docId) throw new Error("未获取到文档 ID");

      // 连接 WebSocket 接收进度
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
          {progress?.phase === "error" && (
            <Text type="danger" style={{ display: "block", marginTop: 4, fontSize: 12 }}>
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
            { title: "类型", dataIndex: "file_type", width: 80 },
            { title: "切片数", dataIndex: "chunk_count", width: 90 },
            {
              title: "状态", dataIndex: "status", width: 100,
              render: (s: string) => (
                <Tag color={s === "ready" ? "green" : s === "failed" ? "red" : "orange"}>
                  {s === "ready" ? "就绪" : s === "failed" ? "失败" : "处理中"}
                </Tag>
              ),
            },
            { title: "上传时间", dataIndex: "created_at", width: 170 },
            {
              title: "操作", width: 100, fixed: "right" as const,
              render: (_: any, r: any) => (
                <Button
                  danger
                  size="small"
                  onClick={() => confirmRemove(r.doc_id, r.title || r.source || r.doc_id)}
                >
                  删除
                </Button>
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
        onOk={doUpload}
        okText="开始上传"
        okButtonProps={{ disabled: !selectedFile }}
      >
        <Space direction="vertical" style={{ width: "100%" }} size="middle">
          <Upload.Dragger
            beforeUpload={(file) => { setSelectedFile(file); return false; }}
            onRemove={() => setSelectedFile(null)}
            maxCount={1}
            accept=".xlsx,.xlsm,.xls,.csv,.txt,.md,.json,.log"
          >
            <p className="ant-upload-drag-icon">
              <UploadOutlined style={{ fontSize: 32, color: "#1677ff" }} />
            </p>
            <p>点击或拖拽文件到此处上传</p>
            <p style={{ color: "#8c8c8c", fontSize: 12 }}>
              支持 xlsx / xls / csv / txt / md / json / log（最大 50MB）
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
            保存后，每次上传文档时切分规则默认使用此配置，可在上传弹窗中临时调整。
          </Text>
        </Space>
      </Modal>
    </div>
  );
}