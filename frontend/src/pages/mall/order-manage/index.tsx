import PlaceholderPage from "../../../components/PlaceholderPage";

export default function OrderManagePage() {
  return (
    <PlaceholderPage
      title="订单管理"
      description="查看和处理用户订单，包括下单、支付、发货、退换货等全流程状态。"
      category="mall"
      features={[
        "订单列表：状态、金额、商品、买家",
        "订单详情：商品快照、收货地址、物流轨迹",
        "改价 / 退款 / 补发 / 取消 一键处理",
        "导出订单、批量打单、批量发货",
      ]}
    />
  );
}
