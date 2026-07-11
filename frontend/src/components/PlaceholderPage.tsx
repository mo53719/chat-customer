import { Card, Typography, Space, Tag } from "antd";
import { ClockCircleOutlined, BulbOutlined } from "@ant-design/icons";
import type { ReactNode } from "react";

const { Title, Paragraph } = Typography;

interface PlaceholderProps {
  title: string;
  description: string;
  category: "team" | "personal" | "mall" | "system";
  features?: string[];
  extra?: ReactNode;
}

const CATEGORY_LABEL: Record<PlaceholderProps["category"], { text: string; color: string }> = {
  team: { text: "团队设置", color: "blue" },
  personal: { text: "个人设置", color: "purple" },
  mall: { text: "商城设置", color: "orange" },
  system: { text: "系统设置", color: "geekblue" },
};

/** 统一风格的「开发中」占位页 */
export default function PlaceholderPage({
  title, description, category, features = [], extra,
}: PlaceholderProps) {
  const cat = CATEGORY_LABEL[category];
  return (
    <Card
      bordered={false}
      style={{ height: "100%", borderRadius: 10, boxShadow: "0 1px 3px rgba(0,0,0,0.06)" }}
      bodyStyle={{ padding: 32 }}
    >
      <Space direction="vertical" size={20} style={{ width: "100%" }}>
        <Space align="center" size={12}>
          <Tag color={cat.color}>{cat.text}</Tag>
          <Title level={3} style={{ margin: 0 }}>{title}</Title>
        </Space>

        <Paragraph type="secondary" style={{ fontSize: 14, marginBottom: 0 }}>
          {description}
        </Paragraph>

        {features.length > 0 && (
          <Card type="inner" title={<Space><BulbOutlined />计划提供的能力</Space>} size="small">
            <ul style={{ margin: 0, paddingLeft: 20, lineHeight: 1.9 }}>
              {features.map((f, i) => (<li key={i}>{f}</li>))}
            </ul>
          </Card>
        )}

        <Card type="inner" style={{ background: "#fafafa" }}>
          <Space>
            <ClockCircleOutlined style={{ color: "#999" }} />
            <span style={{ color: "#999" }}>该功能正在开发中，欢迎提交需求反馈。</span>
          </Space>
        </Card>

        {extra}
      </Space>
    </Card>
  );
}
