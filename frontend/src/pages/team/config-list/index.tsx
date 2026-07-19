import { useEffect, useState } from "react";
import {
  Card, Table, Button, Input, Space, Tag, Modal, Form,
  Select, Switch, message, Typography, Drawer, Popconfirm, Tooltip,
} from "antd";
import {
  PlusOutlined, SearchOutlined, ReloadOutlined,
  EditOutlined, HistoryOutlined, ExclamationCircleOutlined,
} from "@ant-design/icons";
import api from "../../../api";

const { Text } = Typography;
const { TextArea } = Input;

const TYPE_LABELS: Record<string, string> = {
  intent_threshold: "意图识别阈值",
  transfer_rule: "转人工规则",
  timeout_reply: "超时回复设置",
};

const TYPE_COLORS: Record<string, string> = {
  intent_threshold: "red",
  transfer_rule: "orange",
  timeout_reply: "blue",
};

// 核心配置类型（修改时需要二次确认）
const CORE_TYPES = ["intent_threshold", "transfer_rule"];

export default function ConfigListPage() {
  const [rows, setRows] = useState<any[]>([]);
  const [loading, setLoading] = useState(false);
  const [keyword, setKeyword] = useState("");
  const [typeFilter, setTypeFilter] = useState<string | undefined>();
  const [modalOpen, setModalOpen] = useState(false);
  const [editing, setEditing] = useState<any>(null);
  const [form] = Form.useForm();

  // 变更历史
  const [logDrawer, setLogDrawer] = useState(false);
  const [logs, setLogs] = useState<any[]>([]);
  const [logConfigName, setLogConfigName] = useState("");

  const load = async () => {
    setLoading(true);
    try {
      const r: any = await api.get("/config", {
        params: {
          keyword: keyword || undefined,
          config_type: typeFilter || undefined,
        },
      });
      setRows(r.data || []);
    } catch (e: any) {
      message.error(e.message);
    }
    setLoading(false);
  };

  useEffect(() => { load(); }, []);

  // 新增
  const openCreate = () => {
    setEditing(null);
    form.resetFields();
    form.setFieldsValue({ config_value: "{}", is_enabled: true });
    setModalOpen(true);
  };

  // 编辑
  const openEdit = (r: any) => {
    setEditing(r);
    form.setFieldsValue({
      name: r.name,
      config_type: r.config_type,
      config_value: r.config_value,
      description: r.description || "",
      is_enabled: !!r.is_enabled,
    });
    setModalOpen(true);
  };

  // 保存（带风险确认）
  const handleSave = async () => {
    const values = await form.validateFields();
    const configType = editing ? editing.config_type : values.config_type;
    const isCore = CORE_TYPES.includes(configType);

    const doSave = async () => {
      try {
        const body = {
          name: values.name,
          config_type: values.config_type,
          config_value: values.config_value,
          description: values.description || "",
          is_enabled: values.is_enabled ? 1 : 0,
        };
        if (editing) {
          await api.put(`/config/${editing.id}`, body);
          message.success("已更新");
        } else {
          await api.post("/config", body);
          message.success("已创建");
        }
        setModalOpen(false);
        load();
      } catch (e: any) {
        message.error(e.message);
      }
    };

    if (isCore && editing) {
      Modal.confirm({
        title: "风险提示",
        icon: <ExclamationCircleOutlined />,
        content: "修改核心参数可能影响机器人回复准确率，是否确认保存？",
        okText: "确认保存",
        cancelText: "取消",
        okButtonProps: { danger: true },
        onOk: doSave,
      });
    } else {
      doSave();
    }
  };

  // 启用/禁用切换
  const toggleEnabled = async (r: any) => {
    const newVal = r.is_enabled ? 0 : 1;
    // 如果是核心配置且要禁用，也弹确认
    const isCore = CORE_TYPES.includes(r.config_type);
    const doToggle = async () => {
      try {
        await api.put(`/config/${r.id}`, { is_enabled: newVal });
        message.success(newVal ? "已启用" : "已禁用");
        load();
      } catch (e: any) {
        message.error(e.message);
      }
    };
    if (isCore && !newVal) {
      Modal.confirm({
        title: "风险提示",
        icon: <ExclamationCircleOutlined />,
        content: "禁用核心配置可能影响机器人回复准确率，是否确认禁用？",
        okText: "确认禁用",
        cancelText: "取消",
        okButtonProps: { danger: true },
        onOk: doToggle,
      });
    } else {
      doToggle();
    }
  };

  // 删除
  const handleDelete = async (id: number) => {
    try {
      await api.delete(`/config/${id}`);
      message.success("已删除");
      load();
    } catch (e: any) {
      message.error(e.message);
    }
  };

  // 查看变更历史
  const openLogs = async (r: any) => {
    setLogConfigName(r.name);
    setLogDrawer(true);
    setLogs([]);
    try {
      const res: any = await api.get(`/config/${r.id}/logs`, { params: { limit: 5 } });
      setLogs(res.data || []);
    } catch (e: any) {
      message.error(e.message);
    }
  };

  return (
    <div>
      <Card
        title="配置列表"
        extra={
          <Space>
            <Button icon={<ReloadOutlined />} onClick={load}>刷新</Button>
            <Button type="primary" icon={<PlusOutlined />} onClick={openCreate}>
              新增配置
            </Button>
          </Space>
        }
      >
        {/* 筛选栏 */}
        <Space style={{ marginBottom: 16, width: "100%" }} wrap>
          <Input.Search
            placeholder="搜索配置名称..."
            value={keyword}
            onChange={(e) => setKeyword(e.target.value)}
            onSearch={load}
            enterButton={<><SearchOutlined /> 搜索</>}
            allowClear
            style={{ width: 280 }}
          />
          <Select
            placeholder="配置类型"
            value={typeFilter}
            onChange={(v) => { setTypeFilter(v); }}
            allowClear
            style={{ width: 160 }}
            options={Object.entries(TYPE_LABELS).map(([k, v]) => ({ value: k, label: v }))}
          />
          <Text type="secondary">共 {rows.length} 条配置</Text>
        </Space>

        <Table
          rowKey="id"
          dataSource={rows}
          loading={loading}
          columns={[
            { title: "配置名称", dataIndex: "name", ellipsis: true },
            {
              title: "配置类型", dataIndex: "config_type", width: 140,
              render: (t: string) => (
                <Tag color={TYPE_COLORS[t] || "default"}>
                  {TYPE_LABELS[t] || t}
                </Tag>
              ),
            },
            {
              title: "配置值", dataIndex: "config_value", width: 280, ellipsis: true,
              render: (v: string) => {
                try {
                  const obj = JSON.parse(v);
                  return <Text code style={{ fontSize: 12 }}>{JSON.stringify(obj)}</Text>;
                } catch {
                  return <Text code style={{ fontSize: 12 }}>{v}</Text>;
                }
              },
            },
            {
              title: "生效状态", dataIndex: "is_enabled", width: 100,
              render: (v: number, r: any) => (
                <Switch
                  checked={!!v}
                  checkedChildren="启用"
                  unCheckedChildren="禁用"
                  onChange={() => toggleEnabled(r)}
                />
              ),
            },
            { title: "最后修改人", dataIndex: "updated_by", width: 100 },
            {
              title: "更新时间", dataIndex: "updated_at", width: 160,
              render: (v: string) => v ? new Date(v + "Z").toLocaleString("zh-CN") : "-",
            },
            {
              title: "操作", width: 200, fixed: "right" as const,
              render: (_: any, r: any) => (
                <Space size={0}>
                  <Button type="link" size="small" icon={<EditOutlined />}
                    onClick={() => openEdit(r)}>编辑</Button>
                  <Button type="link" size="small" icon={<HistoryOutlined />}
                    onClick={() => openLogs(r)}>历史</Button>
                  <Popconfirm
                    title="确认删除该配置？"
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
        title={editing ? "编辑配置" : "新增配置"}
        open={modalOpen}
        onCancel={() => setModalOpen(false)}
        onOk={handleSave}
        okText={editing ? "保存" : "创建"}
        width={560}
        destroyOnClose
      >
        <Form form={form} layout="vertical" style={{ marginTop: 16 }}>
          <Form.Item
            name="name" label="配置名称"
            rules={[{ required: true, message: "请输入配置名称" }]}
          >
            <Input placeholder="如：意图识别置信度阈值" />
          </Form.Item>
          <Form.Item
            name="config_type" label="配置类型"
            rules={[{ required: true, message: "请选择配置类型" }]}
          >
            <Select
              placeholder="请选择"
              disabled={!!editing}
              options={Object.entries(TYPE_LABELS).map(([k, v]) => ({ value: k, label: v }))}
            />
          </Form.Item>
          <Form.Item
            name="config_value" label="配置值（JSON 格式）"
            rules={[{ required: true, message: "请输入配置值" }]}
          >
            <TextArea rows={4} placeholder='{"threshold": 0.5}' />
          </Form.Item>
          <Form.Item name="description" label="描述">
            <Input placeholder="配置项说明" />
          </Form.Item>
          <Form.Item name="is_enabled" label="生效状态" valuePropName="checked">
            <Switch checkedChildren="启用" unCheckedChildren="禁用" />
          </Form.Item>
        </Form>
        {editing && CORE_TYPES.includes(editing.config_type) && (
          <Text type="warning" style={{ fontSize: 12 }}>
            <ExclamationCircleOutlined /> 此为<strong>核心配置</strong>，修改保存前将弹出风险确认提示。
          </Text>
        )}
      </Modal>

      {/* 变更历史 Drawer */}
      <Drawer
        title={`变更历史 - ${logConfigName}`}
        open={logDrawer}
        onClose={() => setLogDrawer(false)}
        width={560}
      >
        {logs.length === 0 ? (
          <Text type="secondary">暂无变更记录</Text>
        ) : (
          logs.map((l: any, i: number) => (
            <Card key={i} size="small" style={{ marginBottom: 12 }}>
              <Space direction="vertical" size={4} style={{ width: "100%" }}>
                <Space>
                  <Tag>{l.field_name}</Tag>
                  <Text type="secondary" style={{ fontSize: 12 }}>
                    {l.changed_at ? new Date(l.changed_at + "Z").toLocaleString("zh-CN") : ""}
                  </Text>
                  <Text type="secondary" style={{ fontSize: 12 }}>by {l.changed_by}</Text>
                </Space>
                {l.field_name === "create" ? (
                  <Text>新建配置: <Text code>{l.new_value}</Text></Text>
                ) : (
                  <div>
                    <Text type="secondary" style={{ fontSize: 12 }}>旧值: </Text>
                    <Text code style={{ fontSize: 12 }}>{l.old_value || "-"}</Text>
                    <br />
                    <Text type="secondary" style={{ fontSize: 12 }}>新值: </Text>
                    <Text code style={{ fontSize: 12 }}>{l.new_value || "-"}</Text>
                  </div>
                )}
              </Space>
            </Card>
          ))
        )}
      </Drawer>
    </div>
  );
}