import { useState, useEffect } from "react";
import { Card, Table, Tag, Space, Select, Input, Typography, Button, Modal, message } from "antd";
import { SearchOutlined, ReloadOutlined, EyeOutlined } from "@ant-design/icons";
import PageContainer from "../../_shared/PageContainer";

const { Text, Paragraph } = Typography;

interface BadcaseItem {
  id: number;
  session_id: string;
  user_input: string;
  agent_answer: string;
  intent: string;
  agent_name: string;
  failed_rules: string[];
  review_details: any[];
  trace_id: string;
  status: string;
  note: string;
  created_at: string;
}

const STATUS_MAP: Record<string, { color: string; label: string }> = {
  new: { color: "red", label: "未处理" },
  reviewed: { color: "blue", label: "已审核" },
  fixed: { color: "green", label: "已修复" },
  ignored: { color: "default", label: "已忽略" },
};

export default function BadcasePage() {
  const [data, setData] = useState<BadcaseItem[]>([]);
  const [loading, setLoading] = useState(false);
  const [status, setStatus] = useState("new");
  const [keyword, setKeyword] = useState("");
  const [detail, setDetail] = useState<BadcaseItem | null>(null);

  const fetchData = async () => {
    setLoading(true);
    try {
      const params = new URLSearchParams({ status, limit: "50" });
      if (keyword) params.set("keyword", keyword);
      const res = await fetch(`/api/badcase/list?${params}`);
      const json = await res.json();
      setData(json.data || []);
    } catch {
      message.error("获取失败案例失败");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { fetchData(); }, [status]);

  const handleMark = async (id: number, newStatus: string) => {
    await fetch(`/api/badcase/${id}/mark`, {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ status: newStatus }),
    });
    message.success("状态已更新");
    fetchData();
  };

  const columns = [
    { title: "ID", dataIndex: "id", width: 60 },
    { title: "时间", dataIndex: "created_at", width: 160 },
    {
      title: "用户输入", dataIndex: "user_input", width: 200,
      render: (t: string) => <Text ellipsis style={{ maxWidth: 180 }}>{t}</Text>,
    },
    {
      title: "Agent回答", dataIndex: "agent_answer", width: 200,
      render: (t: string) => <Text ellipsis style={{ maxWidth: 180 }}>{t || "-"}</Text>,
    },
    { title: "Agent", dataIndex: "agent_name", width: 100 },
    {
      title: "失败规则", dataIndex: "failed_rules", width: 150,
      render: (rules: string[]) => (
        <Space size={4} wrap>
          {rules?.map((r) => <Tag color="red" key={r}>{r}</Tag>)}
        </Space>
      ),
    },
    {
      title: "状态", dataIndex: "status", width: 90,
      render: (s: string) => {
        const cfg = STATUS_MAP[s] || { color: "default", label: s };
        return <Tag color={cfg.color}>{cfg.label}</Tag>;
      },
    },
    {
      title: "操作", width: 160,
      render: (_: any, record: BadcaseItem) => (
        <Space>
          <Button size="small" icon={<EyeOutlined />} onClick={() => setDetail(record)}>详情</Button>
          {record.status === "new" && (
            <>
              <Button size="small" onClick={() => handleMark(record.id, "reviewed")}>已审</Button>
              <Button size="small" onClick={() => handleMark(record.id, "ignored")}>忽略</Button>
            </>
          )}
        </Space>
      ),
    },
  ];

  return (
    <PageContainer title="失败案例">
      <Card>
        <Space style={{ marginBottom: 16 }}>
          <Select value={status} onChange={setStatus} style={{ width: 120 }}
            options={[
              { value: "new", label: "未处理" },
              { value: "reviewed", label: "已审核" },
              { value: "fixed", label: "已修复" },
              { value: "ignored", label: "已忽略" },
            ]}
          />
          <Input.Search
            placeholder="搜索关键词"
            value={keyword}
            onChange={(e) => setKeyword(e.target.value)}
            onSearch={fetchData}
            style={{ width: 240 }}
          />
          <Button icon={<ReloadOutlined />} onClick={fetchData}>刷新</Button>
        </Space>
        <Table
          rowKey="id"
          columns={columns}
          dataSource={data}
          loading={loading}
          pagination={{ pageSize: 20 }}
          size="small"
        />
      </Card>

      <Modal
        title="失败案例详情"
        open={!!detail}
        onCancel={() => setDetail(null)}
        footer={null}
        width={700}
      >
        {detail && (
          <Space direction="vertical" style={{ width: "100%" }}>
            <div><Text strong>会话ID: </Text>{detail.session_id}</div>
            <div><Text strong>Trace ID: </Text>{detail.trace_id}</div>
            <div><Text strong>Agent: </Text>{detail.agent_name}</div>
            <div><Text strong>意图: </Text>{detail.intent}</div>
            <div>
              <Text strong>失败规则: </Text>
              {(detail.failed_rules || []).map((r) => <Tag color="red" key={r}>{r}</Tag>)}
            </div>
            <Card title="用户输入" size="small"><Paragraph>{detail.user_input}</Paragraph></Card>
            <Card title="Agent回答" size="small"><Paragraph>{detail.agent_answer || "(空)"}</Paragraph></Card>
            {detail.review_details?.length > 0 && (
              <Card title="评分明细" size="small">
                {detail.review_details.map((d: any, i: number) => (
                  <div key={i}>
                    <Tag color={d.passed ? "green" : "red"}>{d.rule}</Tag>
                    {d.reason}
                  </div>
                ))}
              </Card>
            )}
          </Space>
        )}
      </Modal>
    </PageContainer>
  );
}