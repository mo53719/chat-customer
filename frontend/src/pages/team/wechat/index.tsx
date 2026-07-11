import PlaceholderPage from "../../../components/PlaceholderPage";

export default function WechatPage() {
  return (
    <PlaceholderPage
      title="微信客服"
      description="接入微信公众号 / 小程序 / 企业微信，统一管理微信渠道访客消息。"
      category="team"
      features={[
        "扫码授权接入公众号 / 小程序 / 企业微信",
        "同步微信侧粉丝标签、会话上下文",
        "支持客服消息收发、富文本卡片回复",
        "支持客服账号分配与转接",
      ]}
    />
  );
}
