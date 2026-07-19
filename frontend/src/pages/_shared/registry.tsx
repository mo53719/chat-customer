import { HistoryOutlined, AppstoreOutlined, MessageOutlined, DashboardOutlined, FileTextOutlined,
  ExperimentOutlined, LikeOutlined, ControlOutlined, DeleteOutlined,
  UserOutlined, TeamOutlined, ShopOutlined, SettingOutlined,
  ApiOutlined, CustomerServiceOutlined,
  BarChartOutlined, ShoppingCartOutlined, OrderedListOutlined,
  GlobalOutlined, ContactsOutlined, BugOutlined,
} from "@ant-design/icons";
import type { ReactNode } from "react";

export interface PageMeta {
  group: string;
  path: string;
  title: string;
  icon: ReactNode;
  order: number;
  requireAuth: boolean;
  requireAdmin?: boolean;
}

const GROUP_LABELS: Record<string, string> = {
  business: "业务中心",
  team: "团队设置",
  mall: "商城设置",
  personal: "个人设置",
  system: "系统设置",
};

export const pageMetas: PageMeta[] = [
  // 业务中心
  { group: "business", path: "/chat", title: "对话工作台", icon: <MessageOutlined />, order: 10, requireAuth: true },
  { group: "business", path: "/dashboard", title: "数据看板", icon: <DashboardOutlined />, order: 20, requireAuth: true },
  { group: "business", path: "/prompts", title: "提示词版本", icon: <ExperimentOutlined />, order: 30, requireAuth: true },
  { group: "business", path: "/feedback", title: "反馈历史", icon: <LikeOutlined />, order: 40, requireAuth: true },
  { group: "business", path: "/ops", title: "运维观测", icon: <ControlOutlined />, order: 50, requireAuth: true, requireAdmin: true },
  { group: "business", path: "/recycle", title: "回收站", icon: <DeleteOutlined />, order: 60, requireAuth: true, requireAdmin: true },

  // 团队设置
  { group: "team", path: "/team/llm", title: "大模型设置", icon: <ApiOutlined />, order: 10, requireAuth: true, requireAdmin: true },
  { group: "team", path: "/team/rag", title: "RAG 知识库", icon: <FileTextOutlined />, order: 20, requireAuth: true },
  { group: "team", path: "/team/config", title: "配置列表", icon: <OrderedListOutlined />, order: 30, requireAuth: true, requireAdmin: true },
  { group: "team", path: "/team/channels", title: "渠道管理", icon: <GlobalOutlined />, order: 40, requireAuth: true, requireAdmin: true },
  { group: "team", path: "/team/agents", title: "客服管理", icon: <CustomerServiceOutlined />, order: 50, requireAuth: true, requireAdmin: true },
  { group: "team", path: "/team/visitors", title: "访客管理", icon: <TeamOutlined />, order: 60, requireAuth: true },
  { group: "team", path: "/team/service-stats", title: "服务统计", icon: <BarChartOutlined />, order: 70, requireAuth: true },

  // 商城设置
  { group: "mall", path: "/mall/merchant", title: "商家设置", icon: <ShopOutlined />, order: 10, requireAuth: true, requireAdmin: true },
  { group: "mall", path: "/mall/products", title: "商品管理", icon: <ShoppingCartOutlined />, order: 20, requireAuth: true },
  { group: "mall", path: "/mall/orders", title: "订单管理", icon: <OrderedListOutlined />, order: 30, requireAuth: true },

  // 个人设置
  { group: "personal", path: "/personal/profile", title: "个人资料", icon: <ContactsOutlined />, order: 10, requireAuth: true },

  // 系统设置
  { group: "system", path: "/system/general", title: "通用设置", icon: <GlobalOutlined />, order: 10, requireAuth: true, requireAdmin: true },
  { group: "system", path: "/system/badcase", title: "失败案例", icon: <BugOutlined />, order: 20, requireAuth: true, requireAdmin: true },
  { group: "system", path: "/system/operation-log", title: "操作日志", icon: <HistoryOutlined />, order: 30, requireAuth: true, requireAdmin: true },
];

export function buildMenuItems(role?: string | null) {
  const isAdmin = role === "admin";
  const groups = new Map<string, PageMeta[]>();
  pageMetas.forEach((m) => {
    if (m.requireAdmin && !isAdmin) return; // 非管理员跳过管理页面
    if (!groups.has(m.group)) groups.set(m.group, []);
    groups.get(m.group)!.push(m);
  });

  const groupIcons: Record<string, ReactNode> = {
    business: <AppstoreOutlined />,
    team: <TeamOutlined />,
    mall: <ShopOutlined />,
    personal: <UserOutlined />,
    system: <SettingOutlined />,
  };

  return Array.from(groups.entries()).map(([group, items]) => ({
    key: group,
    icon: groupIcons[group],
    label: GROUP_LABELS[group] || group,
    children: items.sort((a, b) => a.order - b.order)
      .map((m) => ({ key: m.path, icon: m.icon, label: m.title })),
  }));
}

export function getOpenKeys(pathname: string): string[] {
  if (pathname.startsWith("/chat") || pathname.startsWith("/dashboard") ||
      pathname.startsWith("/prompts") || pathname.startsWith("/feedback") ||
      pathname.startsWith("/ops") || pathname.startsWith("/recycle")) return ["business"];
  if (pathname.startsWith("/team/")) return ["team"];
  if (pathname.startsWith("/mall/")) return ["mall"];
  if (pathname.startsWith("/personal/")) return ["personal"];
  if (pathname.startsWith("/system/")) return ["system"];
  return ["business"];
}

/** 判断指定路径是否需要管理员权限 */
export function isAdminPage(pathname: string): boolean {
  const meta = pageMetas.find((m) => m.path === pathname);
  return meta?.requireAdmin === true;
}