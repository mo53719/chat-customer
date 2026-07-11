import PlaceholderPage from "../../../components/PlaceholderPage";

export default function ServiceStatsPage() {
  return (
    <PlaceholderPage
      title="服务统计"
      description="客服团队服务质量与效率的多维度统计：响应时长、满意度、转化率等。"
      category="team"
      features={[
        "会话量、消息量、响应时长 P50/P95",
        "客服工作量排行：会话数 / 时长 / 评分",
        "满意度 CSAT、首次解决率 FCR",
        "按技能组、时段、渠道维度筛选",
      ]}
    />
  );
}
