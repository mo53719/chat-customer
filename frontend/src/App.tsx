import { Routes, Route, Navigate, useLocation, useNavigate } from "react-router-dom";
import { Layout, Menu, Typography } from "antd";
import {
  AppstoreOutlined, MessageOutlined, DashboardOutlined, FileTextOutlined,
  ExperimentOutlined, LikeOutlined, ControlOutlined, DeleteOutlined,
  UserOutlined, TeamOutlined, ShopOutlined, SettingOutlined,
  ApiOutlined, WechatOutlined, CustomerServiceOutlined, TeamOutlined as TeamIcon,
  BarChartOutlined, ThunderboltOutlined, ShopOutlined as ShopIcon,
  ShoppingCartOutlined, OrderedListOutlined, GlobalOutlined, ContactsOutlined,
} from "@ant-design/icons";
import { useAuthStore } from "./stores";
import LoginPage from "./pages/Login";
import BusinessHome from "./pages/business";
import ChatPage from "./pages/chat";
import DashboardPage from "./pages/dashboard";
import KnowledgePage from "./pages/knowledge";
import PromptsPage from "./pages/prompts";
import FeedbackPage from "./pages/feedback";
import OpsPage from "./pages/ops";
import RecyclePage from "./pages/recycle";

// 团队设置下的二级
import ConfigListPage from "./pages/team/config-list";
import LLMSettingsPage from "./pages/team/llm-settings";  // 大模型设置
import WechatPage from "./pages/team/wechat";
import AgentManagePage from "./pages/team/agent-manage";
import VisitorManagePage from "./pages/team/visitor-manage";
import ServiceStatsPage from "./pages/team/service-stats";
import DouyinPage from "./pages/team/douyin";

// 商城设置下的二级
import MerchantPage from "./pages/mall/merchant";
import OrderManagePage from "./pages/mall/order-manage";
import ProductManagePage from "./pages/mall/product-manage";

// 个人设置 / 系统设置
import ProfilePage from "./pages/profile";
import SystemPage from "./pages/system";

const { Header: AntHeader, Sider, Content } = Layout;
const { Text } = Typography;

const teamSubItems = [
  { key: "/team/llm", icon: <ApiOutlined />, label: "大模型设置" },
  { key: "/team/rag", icon: <FileTextOutlined />, label: "RAG 知识库" },
  { key: "/team/config", icon: <OrderedListOutlined />, label: "配置列表" },
  { key: "/team/wechat", icon: <WechatOutlined />, label: "微信客服" },
  { key: "/team/agents", icon: <CustomerServiceOutlined />, label: "客服管理" },
  { key: "/team/visitors", icon: <TeamIcon />, label: "访客管理" },
  { key: "/team/service-stats", icon: <BarChartOutlined />, label: "服务统计" },
  { key: "/team/douyin", icon: <ThunderboltOutlined />, label: "抖音接入" },
];

const mallSubItems = [
  { key: "/mall/merchant", icon: <ShopIcon />, label: "商家设置" },
  { key: "/mall/products", icon: <ShoppingCartOutlined />, label: "商品管理" },
  { key: "/mall/orders", icon: <OrderedListOutlined />, label: "订单管理" },
];

// 业务中心（一级）
const businessSubItems = [
  { key: "/chat", icon: <MessageOutlined />, label: "对话工作台" },
  { key: "/dashboard", icon: <DashboardOutlined />, label: "数据看板" },
  { key: "/prompts", icon: <ExperimentOutlined />, label: "提示词版本" },
  { key: "/feedback", icon: <LikeOutlined />, label: "反馈历史" },
  { key: "/ops", icon: <ControlOutlined />, label: "运维观测" },
  { key: "/recycle", icon: <DeleteOutlined />, label: "回收站" },
];

const menuItems = [
  {
    key: "business",
    icon: <AppstoreOutlined />,
    label: "业务中心",
    children: businessSubItems,
  },
  {
    key: "team",
    icon: <TeamOutlined />,
    label: "团队设置",
    children: teamSubItems,
  },
  {
    key: "mall",
    icon: <ShopOutlined />,
    label: "商城设置",
    children: mallSubItems,
  },
  {
    key: "personal",
    icon: <UserOutlined />,
    label: "个人设置",
    children: [
      { key: "/personal/profile", icon: <ContactsOutlined />, label: "个人资料" },
    ],
  },
  {
    key: "system",
    icon: <SettingOutlined />,
    label: "系统设置",
    children: [
      { key: "/system/general", icon: <GlobalOutlined />, label: "通用设置" },
    ],
  },
];

// 根据当前路径推断要展开的分组
function getOpenKeys(pathname: string): string[] {
  if (pathname.startsWith("/chat") || pathname.startsWith("/dashboard") ||
      pathname.startsWith("/prompts") || pathname.startsWith("/feedback") ||
      pathname.startsWith("/ops") || pathname.startsWith("/recycle")) return ["business"];
  if (pathname.startsWith("/team/")) return ["team"];
  if (pathname.startsWith("/mall/")) return ["mall"];
  if (pathname.startsWith("/personal/")) return ["personal"];
  if (pathname.startsWith("/system/")) return ["system"];
  return ["business"];
}

function Shell() {
  const location = useLocation();
  const nav = useNavigate();
  const openKeys = getOpenKeys(location.pathname);

  return (
    <Layout style={{ height: "100vh" }}>
      <Sider width={220} theme="light" style={{ borderRight: "1px solid #f0f0f0" }}>
        <div style={{
          padding: "20px 16px", borderBottom: "1px solid #f5f5f5",
          display: "flex", alignItems: "center", gap: 10,
        }}>
          <div style={{
            width: 28, height: 28, borderRadius: 6,
            background: "linear-gradient(135deg, #1677ff 0%, #4096ff 100%)",
            display: "flex", alignItems: "center", justifyContent: "center",
            color: "#fff", fontWeight: 700, fontSize: 14,
          }}>智</div>
          <Text strong style={{ fontSize: 15 }}>智能客服</Text>
        </div>
        <Menu
          mode="inline"
          defaultOpenKeys={openKeys}
          selectedKeys={[location.pathname === "/business" ? "/chat" : location.pathname]}
          items={menuItems}
          onClick={({ key }) => nav(key)}
          style={{ borderRight: 0, paddingTop: 8 }}
        />
      </Sider>
      <Layout>
        <Content style={{
          padding: 16,
          overflow: "auto",
          background: "#f5f7fa",
          fontFamily:
            '"Inter", "PingFang SC", "Microsoft YaHei", "Source Han Sans CN", -apple-system, BlinkMacSystemFont, "Helvetica Neue", sans-serif',
        }}>
          <Routes>
            {/* 业务中心 */}
            <Route path="/business" element={<BusinessHome />} />
            <Route path="/chat" element={<ChatPage />} />
            <Route path="/dashboard" element={<DashboardPage />} />
            <Route path="/prompts" element={<PromptsPage />} />
            <Route path="/feedback" element={<FeedbackPage />} />
            <Route path="/ops" element={<OpsPage />} />
            <Route path="/recycle" element={<RecyclePage />} />

            {/* 团队设置 */}
            <Route path="/team/llm" element={<LLMSettingsPage />} />
            <Route path="/team/rag" element={<KnowledgePage />} />
            <Route path="/team/config" element={<ConfigListPage />} />
            <Route path="/team/wechat" element={<WechatPage />} />
            <Route path="/team/agents" element={<AgentManagePage />} />
            <Route path="/team/visitors" element={<VisitorManagePage />} />
            <Route path="/team/service-stats" element={<ServiceStatsPage />} />
            <Route path="/team/douyin" element={<DouyinPage />} />

            {/* 商城设置 */}
            <Route path="/mall/merchant" element={<MerchantPage />} />
            <Route path="/mall/products" element={<ProductManagePage />} />
            <Route path="/mall/orders" element={<OrderManagePage />} />

            {/* 个人设置 / 系统设置 */}
            <Route path="/personal/profile" element={<ProfilePage />} />
            <Route path="/system/general" element={<SystemPage />} />

            <Route path="*" element={<Navigate to="/chat" replace />} />
          </Routes>
        </Content>
      </Layout>
    </Layout>
  );
}

export default function App() {
  const token = useAuthStore((s) => s.token);
  if (!token) {
    return (
      <Routes>
        <Route path="/login" element={<LoginPage />} />
        <Route path="*" element={<Navigate to="/login" replace />} />
      </Routes>
    );
  }
  return (
    <Routes>
      <Route path="/login" element={<Navigate to="/chat" replace />} />
      <Route path="/*" element={<Shell />} />
    </Routes>
  );
}
