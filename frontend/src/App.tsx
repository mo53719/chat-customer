import { Routes, Route, Navigate, useLocation, useNavigate } from "react-router-dom";
import { Layout, Menu, Typography } from "antd";
import { useAuthStore } from "./stores";
import { buildMenuItems, getOpenKeys } from "./pages/_shared/registry";

import LoginPage from "./pages/login";
import BusinessHome from "./pages/business";
import ChatPage from "./pages/business/chat";
import DashboardPage from "./pages/business/dashboard";
import PromptsPage from "./pages/business/prompts";
import FeedbackPage from "./pages/business/feedback";
import OpsPage from "./pages/business/ops";
import RecyclePage from "./pages/business/recycle";

// 团队设置
import TeamHome from "./pages/team";
import ConfigListPage from "./pages/team/config-list";
import LLMSettingsPage from "./pages/team/llm-settings";
import KnowledgePage from "./pages/team/rag";
import WechatPage from "./pages/team/wechat";
import AgentManagePage from "./pages/team/agent-manage";
import VisitorManagePage from "./pages/team/visitor-manage";
import ServiceStatsPage from "./pages/team/service-stats";
import DouyinPage from "./pages/team/douyin";
import ChannelManagePage from "./pages/team/channel-manage";

// 商城设置
import MallHome from "./pages/mall";
import MerchantPage from "./pages/mall/merchant";
import OrderManagePage from "./pages/mall/orders";
import ProductManagePage from "./pages/mall/products";

// 个人设置 / 系统设置
import PersonalHome from "./pages/personal";
import ProfilePage from "./pages/personal/profile";
import SystemHome from "./pages/system";
import SystemGeneralPage from "./pages/system/general";
import BadcasePage from "./pages/system/badcase";

const { Header: AntHeader, Sider, Content } = Layout;
const { Text } = Typography;

function Shell() {
  const location = useLocation();
  const nav = useNavigate();
  const openKeys = getOpenKeys(location.pathname);
  const menuItems = buildMenuItems();

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
          selectedKeys={[location.pathname === "/business" ? "/dashboard" : location.pathname]}
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
            <Route path="/team" element={<TeamHome />} />
            <Route path="/team/llm" element={<LLMSettingsPage />} />
            <Route path="/team/rag" element={<KnowledgePage />} />
            <Route path="/team/config" element={<ConfigListPage />} />
            <Route path="/team/wechat" element={<WechatPage />} />
            <Route path="/team/douyin" element={<DouyinPage />} />
            <Route path="/team/channels" element={<ChannelManagePage />} />
            <Route path="/team/agents" element={<AgentManagePage />} />
            <Route path="/team/visitors" element={<VisitorManagePage />} />
            <Route path="/team/service-stats" element={<ServiceStatsPage />} />

            {/* 商城设置 */}
            <Route path="/mall" element={<MallHome />} />
            <Route path="/mall/merchant" element={<MerchantPage />} />
            <Route path="/mall/products" element={<ProductManagePage />} />
            <Route path="/mall/orders" element={<OrderManagePage />} />

            {/* 个人设置 */}
            <Route path="/personal" element={<PersonalHome />} />
            <Route path="/personal/profile" element={<ProfilePage />} />

            {/* 系统设置 */}
            <Route path="/system" element={<SystemHome />} />
            <Route path="/system/general" element={<SystemGeneralPage />} />
            <Route path="/system/badcase" element={<BadcasePage />} />

            <Route path="*" element={<Navigate to="/dashboard" replace />} />
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
      <Route path="/login" element={<Navigate to="/dashboard" replace />} />
      <Route path="/*" element={<Shell />} />
    </Routes>
  );
}