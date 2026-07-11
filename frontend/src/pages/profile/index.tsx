import { Card, Form, Input, Button, Avatar, Space, Typography, message } from "antd";
import { UserOutlined } from "@ant-design/icons";

const { Title, Paragraph } = Typography;

export default function ProfilePage() {
  const [form] = Form.useForm();

  const onSave = () => {
    form.validateFields().then(() => {
      message.success("已保存（演示）");
    });
  };

  return (
    <Card
      bordered={false}
      style={{ borderRadius: 10, boxShadow: "0 1px 3px rgba(0,0,0,0.06)" }}
      bodyStyle={{ padding: 32 }}
    >
      <Space direction="vertical" size={24} style={{ width: "100%" }}>
        <Space size={16} align="center">
          <Avatar size={64} icon={<UserOutlined />} style={{ background: "#1677ff" }} />
          <div>
            <Title level={4} style={{ margin: 0 }}>个人资料</Title>
            <Paragraph type="secondary" style={{ margin: 0 }}>维护您的基本信息与登录凭据</Paragraph>
          </div>
        </Space>

        <Form
          form={form}
          layout="vertical"
          initialValues={{ username: "admin", display_name: "管理员", email: "admin@example.com" }}
          style={{ maxWidth: 480 }}
        >
          <Form.Item label="登录账号" name="username" rules={[{ required: true }]}>
            <Input disabled />
          </Form.Item>
          <Form.Item label="显示名称" name="display_name" rules={[{ required: true }]}>
            <Input placeholder="显示名称" />
          </Form.Item>
          <Form.Item label="邮箱" name="email" rules={[{ type: "email" }]}>
            <Input placeholder="邮箱" />
          </Form.Item>
          <Form.Item label="手机号" name="phone">
            <Input placeholder="可选" />
          </Form.Item>
          <Form.Item>
            <Button type="primary" onClick={onSave}>保存修改</Button>
          </Form.Item>
        </Form>
      </Space>
    </Card>
  );
}
