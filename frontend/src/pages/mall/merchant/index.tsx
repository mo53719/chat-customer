import PlaceholderPage from "../../../components/PlaceholderPage";

export default function MerchantPage() {
  return (
    <PlaceholderPage
      title="商家设置"
      description="管理商家档案、店铺信息、子账号与品牌定制项。"
      category="mall"
      features={[
        "商家基本信息：公司名、Logo、联系方式、营业执照",
        "店铺装修：欢迎语、对话皮肤、品牌色",
        "子账号 / 多店铺切换",
        "第三方授权（支付、物流、ERP）",
      ]}
    />
  );
}
