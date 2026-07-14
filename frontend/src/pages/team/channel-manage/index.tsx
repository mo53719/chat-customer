import { useEffect, useState } from "react";
import {
  Card, Row, Col, Switch, Button, Modal, Form, Input, Tag, message,
  Descriptions, Spin, Typography, Space, Divider,
} from "antd";
import {
  ApiOutlined, SettingOutlined, LinkOutlined,
  CheckCircleOutlined, CloseCircleOutlined, ReloadOutlined,
} from "@ant-design/icons";
import { channelApi } from "../../../api";

const { Text, Paragraph } = Typography;

interface ChannelItem {
  id: number;
  channel_key: string;
  channel_name: string;
  icon: string;
  enabled: number;
  api_key: string;
  api_secret: string;
  webhook_url: string;
  auto_reply: string;
  remark: string;
  config_json: string;
}

export default function ChannelManagePage() {
  const [channels, setChannels] = useState<ChannelItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [editOpen, setEditOpen] = useState(false);
  const [editChannel, setEditChannel] = useState<ChannelItem | null>(null);
  const [saving, setSaving] = useState(false);
  const [form] = Form.useForm();

  const fetchChannels = async () => {
    setLoading(true);
    try {
      const res: any = await channelApi.list();
      setChannels(res.data || []);
    } catch (e: any) {
      message.error("加载渠道列表失败: " + e.message);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchChannels();
  }, []);

  const openEdit = (ch: ChannelItem) => {
    setEditChannel(ch);
    form.setFieldsValue({
      channel_name: ch.channel_name,
      icon: ch.icon,
      api_key: ch.api_key,
      api_secret: ch.api_secret,
      webhook_url: ch.webhook_url,
      auto_reply: ch.auto_reply,
      remark: ch.remark,
    });
    setEditOpen(true);
  };

  const handleSave = async () => {
    if (!editChannel) return;
    try {
      const values = await form.validateFields();
      setSaving(true);
      await channelApi.update(editChannel.channel_key, values);
      message.success("配置已保存");
      setEditOpen(false);
      fetchChannels();
    } catch (e: any) {
      if (e.message) message.error("保存失败: " + e.message);
    } finally {
      setSaving(false);
    }
  };

  const handleToggle = async (ch: ChannelItem) => {
    try {
      const res: any = await channelApi.toggle(ch.channel_key);
      message.success(res.data?.enabled ? "渠道已启用" : "渠道已停用");
      fetchChannels();
    } catch (e: any) {
      message.error("切换失败: " + e.message);
    }
  };

  if (loading) {
    return (
      <div style={{ textAlign: "center", paddingTop: 80 }}>
        <Spin size="large" tip="加载渠道列表..." />
      </div>
    );
  }

  return (
    <div>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 16 }}>
        <div>
          <Text strong style={{ fontSize: 16 }}>渠道管理</Text>
          <div style={{ fontSize: 12, color: "#8c8c8c", marginTop: 2 }}>
            管理各渠道接入配置，启用/停用渠道
          </div>
        </div>
        <Button icon={<ReloadOutlined />} onClick={fetchChannels}>刷新</Button>
      </div>

      <Row gutter={[16, 16]}>
        {channels.map((ch) => (
          <Col xs={24} sm={12} lg={8} key={ch.channel_key}>
            <Card
              bordered={false}
              style={{
                borderRadius: 8,
                boxShadow: "0 1px 3px rgba(0,0,0,0.06)",
                height: "100%",
              }}
              bodyStyle={{ padding: "20px 20px 16px" }}
            >
              <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 12 }}>
                <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
                  <span style={{ fontSize: 28 }}>{ch.icon || "🔌"}</span>
                  <div>
                    <Text strong style={{ fontSize: 15 }}>{ch.channel_name}</Text>
                    <div style={{ fontSize: 12, color: "#8c8c8c" }}>{ch.channel_key}</div>
                  </div>
                </div>
                <Switch
                  checked={ch.enabled === 1}
                  onChange={() => handleToggle(ch)}
                  checkedChildren="启用"
                  unCheckedChildren="停用"
                />
              </div>

              <div style={{ marginBottom: 12 }}>
                <Tag
                  icon={ch.enabled === 1 ? <CheckCircleOutlined /> : <CloseCircleOutlined />}
                  color={ch.enabled === 1 ? "success" : "default"}
                >
                  {ch.enabled === 1 ? "已启用" : "已停用"}
                </Tag>
                {ch.webhook_url && (
                  <Tag icon={<LinkOutlined />} color="blue">已配置 Webhook</Tag>
                )}
                {ch.api_key && (
                  <Tag icon={<ApiOutlined />} color="purple">已配置 API</Tag>
                )}
              </div>

              {ch.remark && (
                <Paragraph
                  type="secondary"
                  ellipsis={{ rows: 1 }}
                  style={{ fontSize: 12, marginBottom: 12 }}
                >
                  {ch.remark}
                </Paragraph>
              )}

              <Button
                icon={<SettingOutlined />}
                block
                onClick={() => openEdit(ch)}
              >
                配置
              </Button>
            </Card>
          </Col>
        ))}
      </Row>

      <Modal
        title={
          <Space>
            <span>{editChannel?.icon}</span>
            <span>配置 - {editChannel?.channel_name}</span>
          </Space>
        }
        open={editOpen}
        onOk={handleSave}
        onCancel={() => setEditOpen(false)}
        confirmLoading={saving}
        width={640}
        destroyOnClose
      >
        <Form form={form} layout="vertical" style={{ marginTop: 16 }}>
          <Descriptions bordered size="small" column={2} style={{ marginBottom: 16 }}>
            <Descriptions.Item label="渠道标识">{editChannel?.channel_key}</Descriptions.Item>
            <Descriptions.Item label="状态">
              <Tag color={editChannel?.enabled === 1 ? "success" : "default"}>
                {editChannel?.enabled === 1 ? "已启用" : "已停用"}
              </Tag>
            </Descriptions.Item>
          </Descriptions>

          <Divider orientation="left" plain style={{ fontSize: 13 }}>
            基本设置
          </Divider>
          <Row gutter={16}>
            <Col span={12}>
              <Form.Item name="channel_name" label="渠道名称" rules={[{ required: true, message: "请输入渠道名称" }]}>
                <Input placeholder="渠道显示名称" />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item name="icon" label="图标（Emoji）">
                <Input placeholder="如 🌐" maxLength={4} />
              </Form.Item>
            </Col>
          </Row>

          <Divider orientation="left" plain style={{ fontSize: 13 }}>
            API 配置
          </Divider>
          <Form.Item name="api_key" label="API Key">
            <Input.Password placeholder="渠道 API Key" />
          </Form.Item>
          <Form.Item name="api_secret" label="API Secret">
            <Input.Password placeholder="渠道 API Secret" />
          </Form.Item>
          <Form.Item name="webhook_url" label="Webhook URL">
            <Input placeholder="https://..." />
          </Form.Item>

          <Divider orientation="left" plain style={{ fontSize: 13 }}>
            自动回复
          </Divider>
          <Form.Item name="auto_reply" label="自动回复内容">
            <Input.TextArea rows={3} placeholder="访客首次进入时的自动回复消息" />
          </Form.Item>

          <Form.Item name="remark" label="备注">
            <Input.TextArea rows={2} placeholder="内部备注" />
          </Form.Item>
        </Form>
      </Modal>
    </div>
  );
}