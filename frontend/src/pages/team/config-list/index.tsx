import PlaceholderPage from "../../../components/PlaceholderPage";

export default function ConfigListPage() {
  return (
    <PlaceholderPage
      title="配置列表"
      description="集中管理客服系统的全局配置项、字典、环境变量等。"
      category="team"
      features={[
        "支持键值对形式的配置管理（编辑/版本/回滚）",
        "配置项分组：渠道接入、回复策略、安全策略等",
        "变更审计日志：谁、何时、改了什么",
        "支持导入/导出配置文件",
      ]}
    />
  );
}
