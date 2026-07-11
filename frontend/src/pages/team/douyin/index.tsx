import PlaceholderPage from "../../../components/PlaceholderPage";

export default function DouyinPage() {
  return (
    <PlaceholderPage
      title="抖音接入"
      description="接入抖音企业号 / 小程序 / 直播间私信，统一管理抖音渠道客户消息。"
      category="team"
      features={[
        "OAuth 授权抖音企业号",
        "私信、评论自动回复 / 触发人工",
        "直播间弹幕监控 + 智能问答",
        "消息统一进入会话工作台",
      ]}
    />
  );
}
