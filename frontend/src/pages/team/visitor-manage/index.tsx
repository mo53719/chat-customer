import PlaceholderPage from "../../../components/PlaceholderPage";

export default function VisitorManagePage() {
  return (
    <PlaceholderPage
      title="访客管理"
      description="查看网站访客列表、来源、设备、行为轨迹，支持主动邀请对话。"
      category="team"
      features={[
        "实时访客列表：IP、地区、来源页、停留时长",
        "访客画像：访问次数、历史会话、转化漏斗",
        "行为回放：访问路径 + 停留热力图",
        "主动邀请：触发条件、话术模板",
      ]}
    />
  );
}
