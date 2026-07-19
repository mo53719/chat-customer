import { useEffect, useState } from "react";
import {
  Card, Table, Button, Input, Space, Tag, Modal, Typography,
  Select, Descriptions, Divider, message,
} from "antd";
import {
  SearchOutlined, ReloadOutlined, EyeOutlined,
  PhoneOutlined, DownloadOutlined,
} from "@ant-design/icons";
import api from "../../../api";

const { Text } = Typography;

const ORDER_STATUS: Record<string, { label: string; color: string }> = {
  pending: { label: "待付款", color: "orange" },
  paid: { label: "已付款", color: "blue" },
  shipped: { label: "已发货", color: "cyan" },
  delivered: { label: "已签收", color: "green" },
  returned: { label: "退货中", color: "purple" },
  refunded: { label: "已退款", color: "magenta" },
  cancelled: { label: "已取消", color: "default" },
};

const AFTER_SALES_STATUS: Record<string, { label: string; color: string }> = {
  pending: { label: "待处理", color: "orange" },
  processing: { label: "处理中", color: "blue" },
  approved: { label: "已通过", color: "green" },
  rejected: { label: "已驳回", color: "red" },
  completed: { label: "已完成", color: "green" },
};

export default function OrderManagePage() {
  const [rows, setRows] = useState<any[]>([]);
  const [loading, setLoading] = useState(false);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(20);
  const [keyword, setKeyword] = useState("");
  const [statusFilter, setStatusFilter] = useState<string | undefined>();
  const [afterSalesFilter, setAfterSalesFilter] = useState<string | undefined>();

  // 详情弹窗
  const [detailOpen, setDetailOpen] = useState(false);
  const [detail, setDetail] = useState<any>(null);

  const load = async () => {
    setLoading(true);
    try {
      const r: any = await api.get("/orders", {
        params: {
          page, page_size: pageSize,
          keyword: keyword || undefined,
          status: statusFilter || undefined,
          after_sales_status: afterSalesFilter || undefined,
        },
      });
      const data = r.data || {};
      setRows(data.items || []);
      setTotal(data.total || 0);
    } catch (e: any) {
      message.error(e.message);
    }
    setLoading(false);
  };

  useEffect(() => { load(); }, [page, pageSize]);

  // 查看详情
  const openDetail = async (orderNo: string) => {
    try {
      const r: any = await api.get(`/orders/${orderNo}`);
      setDetail(r.data);
      setDetailOpen(true);
    } catch (e: any) {
      message.error(e.message);
    }
  };

  // 联系买家：跳转对话工作台并携带订单上下文
  const contactBuyer = (r: any) => {
    const orderContext = encodeURIComponent(JSON.stringify({
      orderNo: r.order_no,
      productName: r.product_name,
      amount: r.amount,
      status: r.status,
    }));
    window.open(`/chat?orderContext=${orderContext}`, "_blank");
  };

  const handleExport = async () => {
    try {
      const params = new URLSearchParams();
      if (statusFilter) params.append("status", statusFilter);
      if (keyword) params.append("keyword", keyword);
      const url = `/api/orders/export?${params.toString()}`;
      window.open(url, "_blank");
    } catch (e: any) {
      message.error(e.message);
    }
  };

  return (
    <div>
      <Card
        title="订单管理"
        extra={
          <Space>
            <Button icon={<DownloadOutlined />} onClick={handleExport}>导出</Button>
            <Button icon={<ReloadOutlined />} onClick={load}>刷新</Button>
          </Space>
        }
      >
        {/* 筛选栏 */}
        <Space style={{ marginBottom: 16, width: "100%" }} wrap>
          <Input.Search
            placeholder="搜索订单号/商品/手机号..."
            value={keyword}
            onChange={(e) => setKeyword(e.target.value)}
            onSearch={() => { setPage(1); load(); }}
            enterButton={<><SearchOutlined /> 搜索</>}
            allowClear
            style={{ width: 300 }}
          />
          <Select
            placeholder="订单状态"
            value={statusFilter}
            onChange={(v) => { setStatusFilter(v); setPage(1); }}
            allowClear
            style={{ width: 130 }}
            options={Object.entries(ORDER_STATUS).map(([k, v]) => ({ value: k, label: v.label }))}
          />
          <Select
            placeholder="售后状态"
            value={afterSalesFilter}
            onChange={(v) => { setAfterSalesFilter(v); setPage(1); }}
            allowClear
            style={{ width: 130 }}
            options={[
              { value: "", label: "无售后" },
              ...Object.entries(AFTER_SALES_STATUS).map(([k, v]) => ({ value: k, label: v.label })),
            ]}
          />
          <Text type="secondary">共 {total} 条订单</Text>
        </Space>

        <Table
          rowKey="id"
          dataSource={rows}
          loading={loading}
          onRow={(r) => ({
            style: { cursor: "pointer" },
            onClick: () => openDetail(r.order_no),
          })}
          rowClassName={() => "order-row-hover"}
          pagination={{
            current: page,
            pageSize,
            total,
            showSizeChanger: true,
            showTotal: (t) => `共 ${t} 条`,
            onChange: (p, ps) => { setPage(p); setPageSize(ps); },
          }}
          columns={[
            {
              title: "订单号", dataIndex: "order_no", width: 180,
              render: (v: string) => (
                <Button type="link" size="small" onClick={(e) => { e.stopPropagation(); openDetail(v); }}>
                  {v}
                </Button>
              ),
            },
            { title: "商品名称", dataIndex: "product_name", width: 180, ellipsis: true },
            { title: "用户ID", dataIndex: "user_id", width: 100 },
            {
              title: "金额", dataIndex: "amount", width: 100,
              render: (v: number) => <Text strong>¥{v}</Text>,
            },
            {
              title: "订单状态", dataIndex: "status", width: 100,
              render: (s: string) => {
                const cfg = ORDER_STATUS[s] || { label: s, color: "default" };
                return <Tag color={cfg.color}>{cfg.label}</Tag>;
              },
            },
            {
              title: "售后状态", dataIndex: "after_sales_status", width: 100,
              render: (s: string) => {
                if (!s) return <Text type="secondary">-</Text>;
                const cfg = AFTER_SALES_STATUS[s] || { label: s, color: "default" };
                return <Tag color={cfg.color}>{cfg.label}</Tag>;
              },
            },
            {
              title: "下单时间", dataIndex: "created_at", width: 160,
              render: (v: string) => v ? new Date(v + "Z").toLocaleString("zh-CN") : "-",
            },
            {
              title: "操作", width: 120, fixed: "right" as const,
              render: (_: any, r: any) => (
                <Button
                  type="link"
                  size="small"
                  icon={<PhoneOutlined />}
                  onClick={(e) => { e.stopPropagation(); contactBuyer(r); }}
                >
                  联系买家
                </Button>
              ),
            },
          ]}
          scroll={{ x: 1100 }}
        />
      </Card>

      {/* 详情弹窗 */}
      <Modal
        title="订单详情"
        open={detailOpen}
        onCancel={() => setDetailOpen(false)}
        footer={detail ? (
          <Button
            type="primary"
            icon={<PhoneOutlined />}
            onClick={() => { contactBuyer(detail); setDetailOpen(false); }}
          >
            联系买家
          </Button>
        ) : null}
        width={600}
      >
        {detail && (
          <div>
            <Descriptions column={2} size="small" bordered>
              <Descriptions.Item label="订单号">{detail.order_no}</Descriptions.Item>
              <Descriptions.Item label="用户ID">{detail.user_id || "-"}</Descriptions.Item>
              <Descriptions.Item label="商品名称">{detail.product_name || "-"}</Descriptions.Item>
              <Descriptions.Item label="订单金额">
                <Text strong>¥{detail.amount}</Text>
              </Descriptions.Item>
              <Descriptions.Item label="订单状态">
                <Tag color={ORDER_STATUS[detail.status]?.color}>
                  {ORDER_STATUS[detail.status]?.label || detail.status}
                </Tag>
              </Descriptions.Item>
              <Descriptions.Item label="售后状态">
                {detail.after_sales_status ? (
                  <Tag color={AFTER_SALES_STATUS[detail.after_sales_status]?.color}>
                    {AFTER_SALES_STATUS[detail.after_sales_status]?.label}
                  </Tag>
                ) : <Text type="secondary">无</Text>}
              </Descriptions.Item>
              <Descriptions.Item label="收货地址" span={2}>{detail.address || "-"}</Descriptions.Item>
              <Descriptions.Item label="联系电话">{detail.phone || "-"}</Descriptions.Item>
              <Descriptions.Item label="下单时间">
                {detail.created_at ? new Date(detail.created_at + "Z").toLocaleString("zh-CN") : "-"}
              </Descriptions.Item>
              <Descriptions.Item label="备注" span={2}>{detail.remark || "-"}</Descriptions.Item>
            </Descriptions>
          </div>
        )}
      </Modal>
    </div>
  );
}