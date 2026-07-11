import PlaceholderPage from "../../components/PlaceholderPage";

export default function SystemPage() {
  return (
    <PlaceholderPage
      title="通用设置"
      description="系统级配置：站点信息、登录策略、日志保留、安全策略等。"
      category="system"
      features={[
        "站点信息：Logo、名称、域名、备案号",
        "登录策略：密码强度、失败锁定、二次验证",
        "日志保留：操作日志 / 工具调用 / Token 用量保留天数",
        "安全策略：IP 白名单、会话超时、敏感词过滤",
      ]}
    />
  );
}
