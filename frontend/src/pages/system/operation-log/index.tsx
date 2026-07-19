import { useEffect, useState } from "react";
import {
  Card, Table, Input, Space, Tag, Select, Typography, message,
} from "antd";
import { SearchOutlined, ReloadOutlined } from "@ant-design/icons";
import api from "../../../api";

const { Text } = Typography;

const ACTION_LABELS: Record<string, { label: string; color: string }> = {
  login: { label: "登录", color: "blue" },
  logout: { label: "登出", color: "default" },
  create: { label: "新增", color: "green" },
  update: { label: "编辑", color: "orange" },
  delete: { label: "删除", color: "red" },
  view: { label: "查看", color: "cyan" },
  export: { label: "导出", color: "purple" },
};

export default function OperationLogPage() {
  const [rows, setRows] = useState<any[]>([]);
  const [loading, setLoading] = useState(false);
  const [pageFilter, setPageFilter] = useState<string | undefined>();
  const [actionFilter, setActionFilter] = useState<string | undefined>();

  const load = async () => {
    setLoading(true);
    try {
      const r: any = await api.get("/logs/page-ops", {
        params: {
          page: pageFilter || undefined,
          action: actionFilter || undefined,
          limit: 100,
        },
      });
      setRows(r.data || []);
    } catch (e: any) {
      message.error(e.message);
    }
    setLoading(false);
  };

  useEffect(() => { load(); }, []);

  return (
    <div>
      <Card
        title="操作日志"
        extra={
          <Space>
            <Select
              placeholder="操作类型"
              value={actionFilter}
              onChange={(v) => { setActionFilter(v); }}
              allowClear
              style={{ width: 130 }}
              options={Object.entries(ACTION_LABELS).map(([k, v]) => ({ value: k, label: v.label }))}
            />
            <Input.Search
              placeholder="搜索页面..."
              value={pageFilter}
              onChange={(e) => setPageFilter(e.target.value)}
              onSearch={load}
              enterButton={<><SearchOutlined /> 搜索</>}
              allowClear
              style={{ width: 240 }}
            />
            <Text type="secondary">共 {rows.length} 条</Text>
          </Space>
        }
      >
        <Table
          rowKey="id"
          dataSource={rows}
          loading={loading}
          columns={[
            { title: "ID", dataIndex: "id", width: 60 },
            { title: "用户ID", dataIndex: "user_id", width: 80 },
            {
              title: "操作页面", dataIndex: "page", width: 160, ellipsis: true,
            },
            {
              title: "操作行为", dataIndex: "action", width: 100,
              render: (a: string) => {
                const cfg = ACTION_LABELS[a] || { label: a, color: "default" };
                return <Tag color={cfg.color}>{cfg.label}</Tag>;
              },
            },
            {
              title: "操作详情", dataIndex: "payload", width: 280, ellipsis: true,
              render: (v: string) => {
                if (!v) return "-";
                try {
                  const obj = JSON.parse(v);
                  return <Text code style={{ fontSize: 12 }}>{JSON.stringify(obj)}</Text>;
                } catch {
                  return <Text style={{ fontSize: 12 }}>{v}</Text>;
                }
              },
            },
            { title: "会话ID", dataIndex: "session_id", width: 120, ellipsis: true },
            {
              title: "操作时间", dataIndex: "created_at", width: 160,
              render: (v: string) => v ? new Date(v + "Z").toLocaleString("zh-CN") : "-",
            },
          ]}
          scroll={{ x: 1000 }}
        />
      </Card>
    </div>
  );
}