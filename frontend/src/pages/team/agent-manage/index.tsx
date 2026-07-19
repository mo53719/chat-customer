import { useEffect, useState } from "react";
import {
  Card, Table, Button, Input, Space, Tag, Modal, Form,
  Select, InputNumber, message, Typography, Popconfirm, Badge,
} from "antd";
import {
  PlusOutlined, SearchOutlined, ReloadOutlined,
  EditOutlined, UserOutlined, DownloadOutlined,
} from "@ant-design/icons";
import api from "../../../api";

const { Text } = Typography;

const STATUS_CONFIG: Record<string, { label: string; color: string; badge: "success" | "default" | "processing" }> = {
  online: { label: "在线", color: "green", badge: "success" },
  offline: { label: "离线", color: "default", badge: "default" },
  busy: { label: "忙碌", color: "orange", badge: "processing" },
};

const ROLE_LABELS: Record<string, string> = {
  admin: "管理员",
  supervisor: "客服主管",
  agent: "普通客服",
};

const DEPARTMENTS = ["售前部", "售后部", "技术支持", "综合部"];
const CHANNELS = ["web", "wechat", "douyin", "taobao"];

export default function AgentManagePage() {
  const [rows, setRows] = useState<any[]>([]);
  const [loading, setLoading] = useState(false);
  const [keyword, setKeyword] = useState("");
  const [deptFilter, setDeptFilter] = useState<string | undefined>();
  const [statusFilter, setStatusFilter] = useState<string | undefined>();
  const [modalOpen, setModalOpen] = useState(false);
  const [editing, setEditing] = useState<any>(null);
  const [form] = Form.useForm();

  const load = async () => {
    setLoading(true);
    try {
      const r: any = await api.get("/agents", {
        params: {
          keyword: keyword || undefined,
          department: deptFilter || undefined,
          status: statusFilter || undefined,
        },
      });
      setRows(r.data || []);
    } catch (e: any) {
      message.error(e.message);
    }
    setLoading(false);
  };

  useEffect(() => { load(); }, []);

  const openCreate = () => {
    setEditing(null);
    form.resetFields();
    form.setFieldsValue({ status: "offline", max_sessions: 5, role: "agent" });
    setModalOpen(true);
  };

  const openEdit = (r: any) => {
    setEditing(r);
    form.setFieldsValue({
      name: r.name,
      account: r.account,
      department: r.department,
      status: r.status,
      max_sessions: r.max_sessions,
      channel: r.channel,
      role: r.role,
    });
    setModalOpen(true);
  };

  const handleSave = async () => {
    const values = await form.validateFields();
    try {
      if (editing) {
        await api.put(`/agents/${editing.id}`, {
          name: values.name,
          department: values.department,
          status: values.status,
          max_sessions: values.max_sessions,
          channel: values.channel,
          role: values.role,
        });
        message.success("已更新");
      } else {
        await api.post("/agents", {
          name: values.name,
          account: values.account,
          department: values.department,
          status: values.status,
          max_sessions: values.max_sessions,
          channel: values.channel,
          role: values.role,
        });
        message.success("已创建");
      }
      setModalOpen(false);
      load();
    } catch (e: any) {
      message.error(e.message);
    }
  };

  // 行内快速切换状态
  const quickToggle = async (r: any, newStatus: string) => {
    try {
      await api.put(`/agents/${r.id}/status`, { status: newStatus });
      message.success(`状态已切换为 ${STATUS_CONFIG[newStatus]?.label}`);
      load();
    } catch (e: any) {
      message.error(e.message);
    }
  };

  const handleDelete = async (id: number) => {
    try {
      await api.delete(`/agents/${id}`);
      message.success("已删除");
      load();
    } catch (e: any) {
      message.error(e.message);
    }
  };

  const handleExport = async () => {
    try {
      const params = new URLSearchParams();
      if (deptFilter) params.append("department", deptFilter);
      if (statusFilter) params.append("status", statusFilter);
      window.open(`/api/agents/export?${params.toString()}`, "_blank");
    } catch (e: any) {
      message.error(e.message);
    }
  };

  return (
    <div>
      <Card
        title="客服管理"
        extra={
          <Space>
            <Button icon={<DownloadOutlined />} onClick={handleExport}>导出</Button>
            <Button icon={<ReloadOutlined />} onClick={load}>刷新</Button>
            <Button type="primary" icon={<PlusOutlined />} onClick={openCreate}>
              新增客服
            </Button>
          </Space>
        }
      >
        <Space style={{ marginBottom: 16, width: "100%" }} wrap>
          <Input.Search
            placeholder="搜索姓名/账号..."
            value={keyword}
            onChange={(e) => setKeyword(e.target.value)}
            onSearch={load}
            enterButton={<><SearchOutlined /> 搜索</>}
            allowClear
            style={{ width: 260 }}
          />
          <Select
            placeholder="部门"
            value={deptFilter}
            onChange={setDeptFilter}
            allowClear
            style={{ width: 130 }}
            options={DEPARTMENTS.map((d) => ({ value: d, label: d }))}
          />
          <Select
            placeholder="状态"
            value={statusFilter}
            onChange={setStatusFilter}
            allowClear
            style={{ width: 120 }}
            options={Object.entries(STATUS_CONFIG).map(([k, v]) => ({ value: k, label: v.label }))}
          />
          <Text type="secondary">共 {rows.length} 人</Text>
        </Space>

        <Table
          rowKey="id"
          dataSource={rows}
          loading={loading}
          columns={[
            {
              title: "客服姓名", dataIndex: "name", width: 100,
              render: (v: string, r: any) => (
                <Space>
                  <Badge status={STATUS_CONFIG[r.status]?.badge} />
                  <UserOutlined />
                  <Text strong>{v}</Text>
                </Space>
              ),
            },
            { title: "账号", dataIndex: "account", width: 100 },
            { title: "部门", dataIndex: "department", width: 100 },
            {
              title: "角色", dataIndex: "role", width: 100,
              render: (v: string) => (
                <Tag color={v === "admin" ? "red" : v === "supervisor" ? "blue" : "default"}>
                  {ROLE_LABELS[v] || v}
                </Tag>
              ),
            },
            {
              title: "在线状态", dataIndex: "status", width: 160,
              render: (v: string, r: any) => (
                <Select
                  value={v}
                  size="small"
                  style={{ width: 100 }}
                  onChange={(newVal) => quickToggle(r, newVal)}
                  options={Object.entries(STATUS_CONFIG).map(([k, cfg]) => ({
                    value: k,
                    label: (
                      <Space size={4}>
                        <Badge status={cfg.badge} />
                        <span>{cfg.label}</span>
                      </Space>
                    ),
                  }))}
                />
              ),
            },
            {
              title: "接待数/上限", width: 120,
              render: (_: any, r: any) => (
                <Text>
                  {r.current_sessions} / <Text type={r.current_sessions >= r.max_sessions ? "danger" : undefined}>{r.max_sessions}</Text>
                </Text>
              ),
            },
            { title: "绑定渠道", dataIndex: "channel", width: 120, ellipsis: true },
            {
              title: "操作", width: 160, fixed: "right" as const,
              render: (_: any, r: any) => (
                <Space size={0}>
                  <Button type="link" size="small" icon={<EditOutlined />}
                    onClick={() => openEdit(r)}>编辑</Button>
                  <Popconfirm
                    title="确认删除该客服？"
                    onConfirm={() => handleDelete(r.id)}
                    okText="删除"
                    okButtonProps={{ danger: true }}
                    cancelText="取消"
                  >
                    <Button type="link" danger size="small">删除</Button>
                  </Popconfirm>
                </Space>
              ),
            },
          ]}
          scroll={{ x: 1000 }}
        />
      </Card>

      {/* 新增/编辑弹窗 */}
      <Modal
        title={editing ? "编辑客服" : "新增客服"}
        open={modalOpen}
        onCancel={() => setModalOpen(false)}
        onOk={handleSave}
        okText={editing ? "保存" : "创建"}
        width={520}
        destroyOnClose
      >
        <Form form={form} layout="vertical" style={{ marginTop: 16 }}>
          <Form.Item
            name="name" label="客服姓名"
            rules={[{ required: true, message: "请输入姓名" }]}
          >
            <Input placeholder="如：张客服" />
          </Form.Item>
          <Form.Item
            name="account" label="账号"
            rules={[{ required: true, message: "请输入账号" }]}
          >
            <Input placeholder="登录账号" disabled={!!editing} />
          </Form.Item>
          <Form.Item name="department" label="所属部门">
            <Select
              placeholder="请选择"
              options={DEPARTMENTS.map((d) => ({ value: d, label: d }))}
            />
          </Form.Item>
          <Form.Item
            name="role" label="角色"
            rules={[{ required: true, message: "请选择角色" }]}
          >
            <Select
              placeholder="请选择角色"
              options={Object.entries(ROLE_LABELS).map(([k, v]) => ({ value: k, label: v }))}
            />
          </Form.Item>
          <Form.Item name="max_sessions" label="最大同时接待数">
            <InputNumber min={1} max={50} style={{ width: "100%" }} />
          </Form.Item>
          <Form.Item name="channel" label="绑定渠道">
            <Select
              mode="multiple"
              placeholder="选择渠道"
              options={CHANNELS.map((c) => ({ value: c, label: c }))}
            />
          </Form.Item>
          <Form.Item name="status" label="在线状态">
            <Select
              options={Object.entries(STATUS_CONFIG).map(([k, v]) => ({ value: k, label: v.label }))}
            />
          </Form.Item>
        </Form>
      </Modal>
    </div>
  );
}