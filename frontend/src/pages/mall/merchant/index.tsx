import { useEffect, useState } from "react";
import {
  Card, Form, Input, Button, Switch, TimePicker, message,
  Typography, Space, Divider, Select, Tooltip,
} from "antd";
import {
  SaveOutlined, ReloadOutlined, InfoCircleOutlined,
} from "@ant-design/icons";
import dayjs from "dayjs";
import api from "../../../api";

const { Text, Paragraph } = Typography;
const { TextArea } = Input;

// 可用变量列表
const VARIABLES = [
  { key: "{用户名}", label: "用户名" },
  { key: "{订单号}", label: "订单号" },
  { key: "{当前时间}", label: "当前时间" },
  { key: "{客服姓名}", label: "客服姓名" },
  { key: "{商品名称}", label: "商品名称" },
];

export default function MerchantPage() {
  const [form] = Form.useForm();
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);

  const load = async () => {
    setLoading(true);
    try {
      const r: any = await api.get("/merchant");
      const d = r.data || {};
      const [start, end] = (d.service_hours || "09:00-18:00").split("-");
      form.setFieldsValue({
        shop_name: d.shop_name,
        shop_logo: d.shop_logo,
        service_start: dayjs(start, "HH:mm"),
        service_end: dayjs(end, "HH:mm"),
        auto_reply: d.auto_reply,
        auto_reply_enabled: !!d.auto_reply_enabled,
        support_contact: d.support_contact,
      });
    } catch (e: any) {
      message.error(e.message);
    }
    setLoading(false);
  };

  useEffect(() => { load(); }, []);

  const insertVariable = (variable: string) => {
    const current = form.getFieldValue("auto_reply") || "";
    form.setFieldValue("auto_reply", current + variable);
  };

  const handleSave = async () => {
    const values = await form.validateFields();
    setSaving(true);
    try {
      const start = values.service_start ? values.service_start.format("HH:mm") : "09:00";
      const end = values.service_end ? values.service_end.format("HH:mm") : "18:00";
      await api.put("/merchant", {
        shop_name: values.shop_name,
        shop_logo: values.shop_logo || "",
        service_hours: `${start}-${end}`,
        auto_reply: values.auto_reply || "",
        auto_reply_enabled: values.auto_reply_enabled ? 1 : 0,
        support_contact: values.support_contact || "",
      });
      message.success("已保存");
    } catch (e: any) {
      message.error(e.message);
    }
    setSaving(false);
  };

  return (
    <div>
      <Card
        title="商家设置"
        extra={
          <Space>
            <Button icon={<ReloadOutlined />} onClick={load} loading={loading}>刷新</Button>
            <Button type="primary" icon={<SaveOutlined />} onClick={handleSave} loading={saving}>
              保存设置
            </Button>
          </Space>
        }
      >
        <Form form={form} layout="vertical" style={{ maxWidth: 700 }}>
          <Divider plain orientation="left" style={{ fontSize: 13, color: "#8c8c8c" }}>基本信息</Divider>

          <Form.Item
            name="shop_name" label="商家名称"
            rules={[{ required: true, message: "请输入商家名称" }]}
          >
            <Input placeholder="如：智能客服商城" />
          </Form.Item>

          <Form.Item name="shop_logo" label="店铺 Logo URL">
            <Input placeholder="图片链接地址" />
          </Form.Item>

          <Divider plain orientation="left" style={{ fontSize: 13, color: "#8c8c8c" }}>客服设置</Divider>

          <Space size="large">
            <Form.Item name="service_start" label="客服接待开始时间">
              <TimePicker format="HH:mm" placeholder="开始时间" />
            </Form.Item>
            <Form.Item name="service_end" label="客服接待结束时间">
              <TimePicker format="HH:mm" placeholder="结束时间" />
            </Form.Item>
          </Space>

          <Form.Item name="auto_reply_enabled" label="非工作时间自动回复" valuePropName="checked">
            <Switch checkedChildren="启用" unCheckedChildren="禁用" />
          </Form.Item>

          <Form.Item name="auto_reply" label="自动回复语">
            <TextArea rows={5} placeholder="输入自动回复内容..." />
          </Form.Item>

          <div style={{ marginTop: -8, marginBottom: 16 }}>
            <Space size={4} wrap>
              <Text type="secondary" style={{ fontSize: 12, marginRight: 4 }}>
                <InfoCircleOutlined /> 插入变量：
              </Text>
              {VARIABLES.map((v) => (
                <Tooltip key={v.key} title={`插入 ${v.key}`}>
                  <Button
                    size="small"
                    onClick={() => insertVariable(v.key)}
                  >
                    {v.label}
                  </Button>
                </Tooltip>
              ))}
            </Space>
          </div>

          <Divider plain orientation="left" style={{ fontSize: 13, color: "#8c8c8c" }}>联系方式</Divider>

          <Form.Item name="support_contact" label="售后联系方式">
            <Input placeholder="如：400-123-4567 或 support@shop.com" />
          </Form.Item>
        </Form>
      </Card>
    </div>
  );
}