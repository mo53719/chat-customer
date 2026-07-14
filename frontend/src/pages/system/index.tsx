import { Card, Row, Col, Typography, Space } from "antd";
import { GlobalOutlined, BugOutlined } from "@ant-design/icons";
import { useNavigate } from "react-router-dom";

const { Title, Paragraph } = Typography;

const QUICK_LINKS = [
  { key: "/system/general", icon: <GlobalOutlined />, title: "通用设置", desc: "系统基础配置管理", color: "#1677ff" },
  { key: "/system/badcase", icon: <BugOutlined />, title: "失败案例", desc: "AI 回答失败案例收集与分析", color: "#eb2f96" },
];

export default function SystemHome() {
  const nav = useNavigate();
  return (
    <Space direction="vertical" size={16} style={{ width: "100%" }}>
      <Card bordered={false} style={{ borderRadius: 10, boxShadow: "0 1px 3px rgba(0,0,0,0.06)" }}>
        <Title level={4} style={{ margin: 0 }}>系统设置</Title>
        <Paragraph type="secondary" style={{ marginTop: 8, marginBottom: 0 }}>
          系统级配置与运维管理。
        </Paragraph>
      </Card>

      <Row gutter={[16, 16]}>
        {QUICK_LINKS.map((it) => (
          <Col xs={24} sm={12} md={8} lg={6} key={it.key}>
            <Card
              hoverable
              onClick={() => nav(it.key)}
              style={{ borderRadius: 10 }}
              styles={{ body: { padding: 20 } }}
            >
              <Space align="start" size={14}>
                <div style={{
                  width: 40, height: 40, borderRadius: 8,
                  background: it.color + "15",
                  color: it.color, fontSize: 20,
                  display: "flex", alignItems: "center", justifyContent: "center",
                }}>
                  {it.icon}
                </div>
                <div style={{ flex: 1 }}>
                  <div style={{ fontWeight: 600, marginBottom: 4 }}>{it.title}</div>
                  <div style={{ color: "#999", fontSize: 12 }}>{it.desc}</div>
                </div>
              </Space>
            </Card>
          </Col>
        ))}
      </Row>
    </Space>
  );
}