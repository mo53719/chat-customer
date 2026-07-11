import PlaceholderPage from "../../../components/PlaceholderPage";

export default function AgentManagePage() {
  return (
    <PlaceholderPage
      title="客服管理"
      description="管理客服团队成员、角色权限、技能组与排班。"
      category="team"
      features={[
        "客服人员增删改查、角色与权限分配",
        "技能组管理：售前/售后/技术支持 等",
        "在线状态、接待上限、自动分配规则",
        "排班表：班次、请假、临时调班",
      ]}
    />
  );
}
