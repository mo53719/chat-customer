import { useEffect, useState } from "react";
import {
  Card, Form, Input, Button, Switch, InputNumber, message,
  Typography, Space, Divider, Modal,
} from "antd";
import {
  SaveOutlined, ReloadOutlined, ExclamationCircleOutlined,
} from "@ant-design/icons";
import api from "../../../api";

const { Text } = Typography;

// 高危设置字段（修改时需要二次确认）
const HIGH_RISK_FIELDS = ["data_backup_enabled", "log_retention_days"];

export default function SystemPage() {
  const [form] = Form.useForm();
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [originalValues, setOriginalValues] = useState<any>({});

  const load = async () => {
    setLoading(true);
    try {
      const r: any = await api.get("/system-config");
      const d = r.data || {};
      const vals = {
        system_name: d.system_name,
        login_timeout: d.login_timeout,
        log_retention_days: d.log_retention_days,
        message_push_enabled: !!d.message_push_enabled,
        data_backup_enabled: !!d.data_backup_enabled,
        data_backup_time: d.data_backup_time,
      };
      form.setFieldsValue(vals);
      setOriginalValues(vals);
    } catch (e: any) {
      message.error(e.message);
    }
    setLoading(false);
  };

  useEffect(() => { load(); }, []);

  const handleSave = async () => {
    const values = await form.validateFields();

    // 检查是否修改了高危字段
    const changedHighRisk = HIGH_RISK_FIELDS.some((field) => {
      const orig = originalValues[field];
      const curr = values[field];
      if (typeof orig === "boolean") return orig !== curr;
      return orig !== curr;
    });

    const doSave = async () => {
      setSaving(true);
      try {
        await api.put("/system-config", {
          system_name: values.system_name,
          login_timeout: values.login_timeout,
          log_retention_days: values.log_retention_days,
          message_push_enabled: values.message_push_enabled ? 1 : 0,
          data_backup_enabled: values.data_backup_enabled ? 1 : 0,
          data_backup_time: values.data_backup_time,
        });
        message.success("已保存");
        load();
      } catch (e: any) {
        message.error(e.message);
      }
      setSaving(false);
    };

    if (changedHighRisk) {
      Modal.confirm({
        title: "高危操作确认",
        icon: <ExclamationCircleOutlined />,
        content: "您正在修改数据备份或日志保留等关键设置，是否确认保存？",
        okText: "确认保存",
        cancelText: "取消",
        okButtonProps: { danger: true },
        onOk: doSave,
      });
    } else {
      doSave();
    }
  };

  return (
    <div>
      <Card
        title="通用设置"
        extra={
          <Space>
            <Button icon={<ReloadOutlined />} onClick={load} loading={loading}>刷新</Button>
            <Button type="primary" icon={<SaveOutlined />} onClick={handleSave} loading={saving}>
              保存设置
            </Button>
          </Space>
        }
      >
        <Form form={form} layout="vertical" style={{ maxWidth: 600 }}>
          <Divider plain orientation="left" style={{ fontSize: 13, color: "#8c8c8c" }}>系统信息</Divider>

          <Form.Item
            name="system_name" label="系统名称"
            rules={[{ required: true, message: "请输入系统名称" }]}
          >
            <Input placeholder="智能客服系统" />
          </Form.Item>

          <Divider plain orientation="left" style={{ fontSize: 13, color: "#8c8c8c" }}>安全与登录</Divider>

          <Form.Item
            name="login_timeout" label="登录超时时间（分钟）"
            rules={[{ required: true, message: "请输入超时时间" }]}
          >
            <InputNumber min={5} max={1440} style={{ width: 200 }} addonAfter="分钟" />
          </Form.Item>

          <Divider plain orientation="left" style={{ fontSize: 13, color: "#8c8c8c" }}>日志与数据</Divider>

          <Form.Item
            name="log_retention_days" label="日志保留天数"
            rules={[{ required: true, message: "请输入保留天数" }]}
            extra={<Text type="warning">修改此设置将影响历史日志的保留策略，请谨慎操作。</Text>}
          >
            <InputNumber min={7} max={3650} style={{ width: 200 }} addonAfter="天" />
          </Form.Item>

          <Form.Item name="data_backup_enabled" label="数据备份" valuePropName="checked"
            extra={<Text type="warning">启用/禁用数据备份可能影响数据安全，请谨慎操作。</Text>}
          >
            <Switch checkedChildren="启用" unCheckedChildren="禁用" />
          </Form.Item>

          <Form.Item name="data_backup_time" label="备份执行时间">
            <Input placeholder="如：03:00" style={{ width: 200 }} />
          </Form.Item>

          <Divider plain orientation="left" style={{ fontSize: 13, color: "#8c8c8c" }}>消息推送</Divider>

          <Form.Item name="message_push_enabled" label="消息推送" valuePropName="checked">
            <Switch checkedChildren="启用" unCheckedChildren="禁用" />
          </Form.Item>
        </Form>
      </Card>
    </div>
  );
}