import { useEffect, useState } from "react";
import {
  Card, Table, Button, Modal, Form, Select, Input, Slider,
  InputNumber, Tag, Space, message, Descriptions, Typography,
} from "antd";
import { SettingOutlined, ReloadOutlined } from "@ant-design/icons";
import { agentModelApi } from "../../../api";

const { Text } = Typography;

const AGENT_LABELS: Record<string, string> = {
  main_agent: "主客服",
  presales_agent: "售前客服",
  aftersales_agent: "售后客服",
  order_agent: "订单客服",
  safety_agent: "安全审核",
  rag_agent: "知识库客服",
};

const MODEL_OPTIONS = [
  "qwen3.6-flash",
  "qwen-max",
  "qwen-plus",
  "qwen-turbo",
  "glm-4-plus",
  "glm-4-air",
  "deepseek-chat",
  "deepseek-reasoner",
];

interface AgentConfig {
  agent_name: string;
  model: string | null;
  base_url: string | null;
  api_key: string | null;
  temperature: number | null;
  max_tokens: number | null;
}

export default function LLMSettingsPage() {
  const [agents, setAgents] = useState<string[]>([]);
  const [configs, setConfigs] = useState<Record<string, AgentConfig>>({});
  const [defaults, setDefaults] = useState<any>({});
  const [editModal, setEditModal] = useState(false);
  const [editingAgent, setEditingAgent] = useState<string>("");
  const [form] = Form.useForm();

  const loadData = async () => {
    try {
      const [agentsRes, configsRes, defaultsRes] = await Promise.all([
        agentModelApi.agents(),
        agentModelApi.list(),
        agentModelApi.defaults(),
      ]);
      setAgents(agentsRes.data || []);
      setDefaults(defaultsRes.data || {});

      const configMap: Record<string, AgentConfig> = {};
      (configsRes.data || []).forEach((c: AgentConfig) => {
        configMap[c.agent_name] = c;
      });
      setConfigs(configMap);
    } catch (e: any) {
      message.error(e.message);
    }
  };

  useEffect(() => { loadData(); }, []);

  const openEdit = (agentName: string) => {
    setEditingAgent(agentName);
    const cfg = configs[agentName];
    form.setFieldsValue({
      model: cfg?.model || undefined,
      base_url: cfg?.base_url || "",
      api_key: cfg?.api_key ? "(已设置)" : "",
      temperature: cfg?.temperature ?? undefined,
      max_tokens: cfg?.max_tokens ?? undefined,
    });
    setEditModal(true);
  };

  const handleSave = async () => {
    try {
      const values = await form.validateFields();
      const body: any = {};

      // 只提交用户实际填写的字段
      if (values.model && values.model !== "__default__") body.model = values.model;
      if (values.base_url) body.base_url = values.base_url;
      if (values.api_key && values.api_key !== "(已设置)") body.api_key = values.api_key;
      if (values.temperature !== undefined && values.temperature !== null) body.temperature = values.temperature;
      if (values.max_tokens !== undefined && values.max_tokens !== null) body.max_tokens = values.max_tokens;

      await agentModelApi.save(editingAgent, body);
      message.success(`"${AGENT_LABELS[editingAgent] || editingAgent}" 模型配置已保存`);
      setEditModal(false);
      loadData();
    } catch (e: any) {
      message.error(e.message);
    }
  };

  const handleReset = async (agentName: string) => {
    try {
      await agentModelApi.reset(agentName);
      message.success(`"${AGENT_LABELS[agentName] || agentName}" 已恢复为默认配置`);
      loadData();
    } catch (e: any) {
      message.error(e.message);
    }
  };

  const getDisplayValue = (agentName: string, field: string) => {
    const cfg = configs[agentName];
    const def = defaults;
    const val = cfg?.[field];
    if (val === null || val === undefined) {
      return <Text type="secondary">（默认）</Text>;
    }
    if (field === "temperature") {
      return `${val}（默认 ${def.temperature}）`;
    }
    if (field === "max_tokens") {
      return `${val}（默认 ${def.max_tokens}）`;
    }
    return val;
  };

  const columns = [
    {
      title: "角色",
      dataIndex: "agent_name",
      render: (name: string) => (
        <Space>
          <span>{AGENT_LABELS[name] || name}</span>
          <Text type="secondary" style={{ fontSize: 12 }}>({name})</Text>
        </Space>
      ),
    },
    {
      title: "当前模型",
      render: (_: any, r: { agent_name: string }) => {
        const cfg = configs[r.agent_name];
        const model = cfg?.model || defaults.model;
        const isDefault = !cfg?.model;
        return (
          <span>
            {model}
            {isDefault && <Text type="secondary" style={{ marginLeft: 4 }}>（默认）</Text>}
          </span>
        );
      },
    },
    {
      title: "温度",
      width: 160,
      render: (_: any, r: { agent_name: string }) => {
        const cfg = configs[r.agent_name];
        const temp = cfg?.temperature ?? defaults.temperature;
        return <span>{temp}{!cfg?.temperature ? <Text type="secondary">（默认）</Text> : null}</span>;
      },
    },
    {
      title: "状态",
      width: 100,
      render: (_: any, r: { agent_name: string }) => {
        const hasCustom = !!configs[r.agent_name];
        return hasCustom
          ? <Tag color="blue">已自定义</Tag>
          : <Tag>使用默认</Tag>;
      },
    },
    {
      title: "操作",
      width: 160,
      render: (_: any, r: { agent_name: string }) => (
        <Space>
          <Button size="small" onClick={() => openEdit(r.agent_name)}>
            编辑
          </Button>
          {configs[r.agent_name] && (
            <Button size="small" danger onClick={() => handleReset(r.agent_name)}>
              重置
            </Button>
          )}
        </Space>
      ),
    },
  ];

  return (
    <div>
      {/* ── 全局默认配置卡片 ── */}
      <Card
        title={
          <Space>
            <SettingOutlined />
            <span>全局默认配置</span>
          </Space>
        }
        style={{ marginBottom: 16 }}
      >
        <Descriptions size="small" column={4}>
          <Descriptions.Item label="模型">{defaults.model || "-"}</Descriptions.Item>
          <Descriptions.Item label="API 地址">
            <Text copyable={{ text: defaults.base_url }} style={{ fontSize: 12 }}>
              {defaults.base_url ? defaults.base_url.replace(/^https?:\/\//, "").slice(0, 40) + "..." : "-"}
            </Text>
          </Descriptions.Item>
          <Descriptions.Item label="温度">{defaults.temperature ?? "-"}</Descriptions.Item>
          <Descriptions.Item label="最大 Token">{defaults.max_tokens ?? "-"}</Descriptions.Item>
        </Descriptions>
        <Text type="secondary" style={{ fontSize: 12 }}>
          以下为系统全局默认配置。当某个客服角色未单独设置时，将自动使用以上默认值。
          如需修改全局默认配置，请在项目根目录的 .env 文件中更改。
        </Text>
      </Card>

      {/* ── 各角色模型配置表格 ── */}
      <Card
        title="各角色模型配置"
        extra={
          <Button icon={<ReloadOutlined />} onClick={loadData}>刷新</Button>
        }
      >
        <Table
          rowKey="agent_name"
          dataSource={agents.map((name) => ({ agent_name: name }))}
          columns={columns}
          pagination={false}
        />
      </Card>

      {/* ── 编辑弹窗 ── */}
      <Modal
        title={`编辑「${AGENT_LABELS[editingAgent] || editingAgent}」模型配置`}
        open={editModal}
        onCancel={() => setEditModal(false)}
        onOk={handleSave}
        okText="保存"
        width={560}
        footer={(_, { OkBtn, CancelBtn }) => (
          <Space>
            <Button
              danger
              onClick={() => {
                handleReset(editingAgent);
                setEditModal(false);
              }}
            >
              重置为默认配置
            </Button>
            <CancelBtn />
            <OkBtn />
          </Space>
        )}
      >
        <Form
          form={form}
          layout="vertical"
          style={{ marginTop: 16 }}
        >
          <Form.Item name="model" label="模型名称">
            <Select
              allowClear
              placeholder="选择或输入模型名称（不选则使用全局默认）"
              mode="tags"
              maxCount={1}
              onChange={(val: string[]) => {
                if (val.length > 0) {
                  form.setFieldValue("model", val[0]);
                } else {
                  form.setFieldValue("model", undefined);
                }
              }}
              options={MODEL_OPTIONS.map((m) => ({ value: m, label: m }))}
              style={{ width: "100%" }}
            />
          </Form.Item>
          <Text type="secondary" style={{ display: "block", marginTop: -12, marginBottom: 12, fontSize: 12 }}>
            不填写则使用全局默认模型（{defaults.model}）。支持自定义输入任意模型名称。
          </Text>

          <Form.Item name="base_url" label="API 地址（可选）">
            <Input placeholder={`不填则使用默认地址: ${defaults.base_url}`} />
          </Form.Item>

          <Form.Item name="api_key" label="API Key（可选）">
            <Input.Password
              placeholder="不填则使用全局默认 API Key"
              autoComplete="off"
            />
          </Form.Item>

          <Form.Item name="temperature" label="温度（可选）">
            <Slider
              min={0}
              max={2}
              step={0.1}
              marks={{ 0: "0", 0.5: "0.5", 1: "1", 1.5: "1.5", 2: "2" }}
            />
          </Form.Item>

          <Form.Item name="max_tokens" label="最大 Token 数（可选）">
            <InputNumber
              min={64}
              max={32768}
              step={256}
              placeholder={`不填则使用默认值 ${defaults.max_tokens}`}
              style={{ width: "100%" }}
            />
          </Form.Item>

          <Text type="secondary" style={{ fontSize: 12, display: "block" }}>
            不填写的字段将自动使用全局默认配置。API Key 仅保存时传输，不会在页面中明文显示。
          </Text>
        </Form>
      </Modal>
    </div>
  );
}