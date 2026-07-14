import { Card, Row, Col, Typography, Space } from "antd";
import {
  ApiOutlined, FileTextOutlined, OrderedListOutlined,
  GlobalOutlined, CustomerServiceOutlined, TeamOutlined, BarChartOutlined,
} from "@ant-design/icons";
import { useNavigate } from "react-router-dom";

const { Title, Paragraph } = Typography;

const QUICK_LINKS = [
  { key: "/team/llm", icon: <ApiOutlined />, title: "大模型设置", desc: "配置 LLM 模型参数", color: "#1677ff" },
  { key: "/team/rag", icon: <FileTextOutlined />, title: "RAG 知识库", desc: "管理检索增强生成知识库", color: "#52c41a" },
  { key: "/team/config", icon: <OrderedListOutlined />, title: "配置列表", desc: "系统配置项管理", color: "#fa8c16" },
  { key: "/team/channels", icon: <GlobalOutlined />, title: "渠道管理", desc: "多渠道接入配置", color: "#722ed1" },
  { key: "/team/agents", icon: <CustomerServiceOutlined />, title: "客服管理", desc: "Agent 配置与权限", color: "#eb2f96" },
  { key: "/team/visitors", icon: <TeamOutlined />, title: "访客管理", desc: "访客信息与画像", color: "#13c2c2" },
  { key: "/team/service-stats", icon: <BarChartOutlined />, title: "服务统计", desc: "服务数据与趋势分析", color: "#fa541c" },
];

export default function TeamHome() {
  const nav = useNavigate();
  return (
    <Space direction="vertical" size={16} style={{ width: "100%" }}>
      <Card bordered={false} style={{ borderRadius: 10, boxShadow: "0 1px 3px rgba(0,0,0,0.06)" }}>
        <Title level={4} style={{ margin: 0 }}>团队设置</Title>
        <Paragraph type="secondary" style={{ marginTop: 8, marginBottom: 0 }}>
          Agent、渠道、知识库等团队协作配置。
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