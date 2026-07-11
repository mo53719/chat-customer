import { Card, Row, Col, Statistic, Typography, Space } from "antd";
import {
  MessageOutlined, DashboardOutlined, FileTextOutlined,
  ExperimentOutlined, LikeOutlined, DeleteOutlined, ControlOutlined,
} from "@ant-design/icons";
import { useNavigate } from "react-router-dom";

const { Title, Paragraph } = Typography;

const QUICK_LINKS = [
  { key: "/chat", icon: <MessageOutlined />, title: "对话工作台", desc: "与访客进行实时对话", color: "#1677ff" },
  { key: "/dashboard", icon: <DashboardOutlined />, title: "数据看板", desc: "会话量、消息量、转化率", color: "#52c41a" },
  { key: "/knowledge", icon: <FileTextOutlined />, title: "RAG 知识库", desc: "管理可被 RAG 召回的业务文档", color: "#fa8c16" },
  { key: "/prompts", icon: <ExperimentOutlined />, title: "提示词版本", desc: "Agent 系统提示词的版本管理", color: "#722ed1" },
  { key: "/feedback", icon: <LikeOutlined />, title: "反馈历史", desc: "用户反馈与智能分析", color: "#eb2f96" },
  { key: "/ops", icon: <ControlOutlined />, title: "运维观测", desc: "工具调用、Token、异常监控", color: "#13c2c2" },
  { key: "/recycle", icon: <DeleteOutlined />, title: "回收站", desc: "软删数据恢复", color: "#8c8c8c" },
];

export default function BusinessHome() {
  const nav = useNavigate();
  return (
    <Space direction="vertical" size={16} style={{ width: "100%" }}>
      <Card bordered={false} style={{ borderRadius: 10, boxShadow: "0 1px 3px rgba(0,0,0,0.06)" }}>
        <Title level={4} style={{ margin: 0 }}>业务中心</Title>
        <Paragraph type="secondary" style={{ marginTop: 8, marginBottom: 0 }}>
          日常运营相关功能的统一入口。点击下方卡片快速进入。
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
