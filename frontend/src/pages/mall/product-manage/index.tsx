import { useEffect, useState } from "react";
import {
  Card, Table, Button, Input, Space, Tag, Modal, Form,
  InputNumber, Select, message, Typography, Divider, Popconfirm,
} from "antd";
import { PlusOutlined, SearchOutlined, ReloadOutlined } from "@ant-design/icons";
import { productApi } from "../../../api";

const { Text } = Typography;
const { TextArea } = Input;

const STATUS_OPTIONS = [
  { value: "on_sale", label: "上架" },
  { value: "off_sale", label: "下架" },
];

export default function ProductManagePage() {
  const [products, setProducts] = useState<any[]>([]);
  const [categories, setCategories] = useState<any[]>([]);
  const [loading, setLoading] = useState(false);
  const [keyword, setKeyword] = useState("");
  const [modalOpen, setModalOpen] = useState(false);
  const [editing, setEditing] = useState<any>(null);
  const [form] = Form.useForm();

  // ── 加载数据 ──────────────────────────────────────────────
  const load = async () => {
    setLoading(true);
    try {
      const [pr, cr] = await Promise.all([
        productApi.list({ keyword: keyword || undefined, limit: 100 }),
        productApi.categories(),
      ]);
      setProducts(pr.data || []);
      setCategories(cr.data || []);
    } catch (e: any) { message.error(e.message); }
    setLoading(false);
  };
  useEffect(() => { load(); }, []);

  // ── 新增 / 编辑 ────────────────────────────────────────────
  const openCreate = () => {
    setEditing(null);
    form.resetFields();
    form.setFieldsValue({ status: "on_sale", stock: 0, price: 0 });
    setModalOpen(true);
  };
  const openEdit = (r: any) => {
    setEditing(r);
    form.setFieldsValue({
      ...r,
      specs: r.specs ? JSON.stringify(r.specs, null, 2) : "",
      tags: r.tags ? r.tags.join(", ") : "",
    });
    setModalOpen(true);
  };

  const save = async () => {
    const values = await form.validateFields();
    // 解析 specs 和 tags
    const data = {
      ...values,
      specs: values.specs ? (() => {
        try { return JSON.parse(values.specs); } catch { return {}; }
      })() : {},
      tags: values.tags ? values.tags.split(",").map((t: string) => t.trim()).filter(Boolean) : [],
    };
    try {
      if (editing) {
        await productApi.update(editing.id, data);
        message.success("已更新");
      } else {
        await productApi.create(data);
        message.success("已创建");
      }
      setModalOpen(false);
      load();
    } catch (e: any) { message.error(e.message); }
  };

  // ── 删除 ──────────────────────────────────────────────────
  const remove = async (id: number) => {
    try {
      await productApi.remove(id);
      message.success("已删除");
      load();
    } catch (e: any) { message.error(e.message); }
  };

  return (
    <div>
      <Card
        title="商品管理"
        extra={
          <Space>
            <Button icon={<ReloadOutlined />} onClick={load}>刷新</Button>
            <Button type="primary" icon={<PlusOutlined />} onClick={openCreate}>新增商品</Button>
          </Space>
        }
      >
        {/* 搜索栏 */}
        <Space style={{ marginBottom: 16, width: "100%" }}>
          <Input.Search
            placeholder="搜索商品名称/品牌/型号..."
            value={keyword}
            onChange={(e) => setKeyword(e.target.value)}
            onSearch={load}
            enterButton={<><SearchOutlined /> 搜索</>}
            allowClear
            style={{ width: 360 }}
          />
          <Text type="secondary">共 {products.length} 件商品</Text>
        </Space>

        <Table
          rowKey="id"
          dataSource={products}
          loading={loading}
          columns={[
            { title: "SKU", dataIndex: "sku", width: 130, ellipsis: true },
            { title: "名称", dataIndex: "name", width: 180, ellipsis: true },
            {
              title: "分类", dataIndex: "category_name", width: 100,
              render: (v: string) => v || <Text type="secondary">-</Text>,
            },
            { title: "品牌", dataIndex: "brand", width: 100, render: (v: string) => v || "-" },
            {
              title: "价格", dataIndex: "price", width: 100,
              render: (v: number) => <Text strong>¥{v}</Text>,
            },
            { title: "库存", dataIndex: "stock", width: 80 },
            { title: "销量", dataIndex: "sales_count", width: 80 },
            {
              title: "状态", dataIndex: "status", width: 90,
              render: (s: string) => (
                <Tag color={s === "on_sale" ? "green" : "default"}>
                  {s === "on_sale" ? "上架" : "下架"}
                </Tag>
              ),
            },
            {
              title: "操作", width: 160, fixed: "right" as const,
              render: (_: any, r: any) => (
                <Space>
                  <Button size="small" type="link" onClick={() => openEdit(r)}>编辑</Button>
                  <Popconfirm
                    title="确认删除该商品？"
                    description="删除后不可恢复"
                    onConfirm={() => remove(r.id)}
                    okText="删除"
                    okButtonProps={{ danger: true }}
                    cancelText="取消"
                  >
                    <Button size="small" danger type="link">删除</Button>
                  </Popconfirm>
                </Space>
              ),
            },
          ]}
          scroll={{ x: 1100 }}
        />
      </Card>

      {/* ── 新增/编辑 弹窗 ──────────────────────────────────── */}
      <Modal
        title={editing ? "编辑商品" : "新增商品"}
        open={modalOpen}
        onCancel={() => setModalOpen(false)}
        onOk={save}
        okText={editing ? "保存" : "创建"}
        width={720}
        destroyOnClose
      >
        <Form form={form} layout="vertical" style={{ marginTop: 16 }}>
          <Divider plain orientation="left" style={{ fontSize: 13, color: "#8c8c8c" }}>基本信息</Divider>
          <Space style={{ width: "100%" }} size="middle">
            <Form.Item name="sku" label="SKU" rules={[{ required: true, message: "请输入 SKU" }]} style={{ width: 200 }}>
              <Input placeholder="如：SP-001" />
            </Form.Item>
            <Form.Item name="name" label="商品名称" rules={[{ required: true, message: "请输入名称" }]} style={{ width: 280 }}>
              <Input placeholder="如：智能保温杯" />
            </Form.Item>
            <Form.Item name="category_id" label="分类" style={{ width: 160 }}>
              <Select
                placeholder="请选择"
                allowClear
                options={categories.map((c: any) => ({ value: c.id, label: c.name }))}
              />
            </Form.Item>
          </Space>

          <Space style={{ width: "100%" }} size="middle">
            <Form.Item name="brand" label="品牌" style={{ width: 180 }}>
              <Input placeholder="如：小米" />
            </Form.Item>
            <Form.Item name="model" label="型号" style={{ width: 180 }}>
              <Input placeholder="如：M3 Pro" />
            </Form.Item>
            <Form.Item name="status" label="状态" style={{ width: 120 }}>
              <Select options={STATUS_OPTIONS} />
            </Form.Item>
          </Space>

          <Divider plain orientation="left" style={{ fontSize: 13, color: "#8c8c8c" }}>价格与库存</Divider>
          <Space style={{ width: "100%" }} size="middle">
            <Form.Item name="price" label="售价" rules={[{ required: true, message: "请输入价格" }]} style={{ width: 160 }}>
              <InputNumber min={0} step={0.01} prefix="¥" style={{ width: "100%" }} />
            </Form.Item>
            <Form.Item name="original_price" label="原价" style={{ width: 160 }}>
              <InputNumber min={0} step={0.01} prefix="¥" style={{ width: "100%" }} />
            </Form.Item>
            <Form.Item name="stock" label="库存" style={{ width: 120 }}>
              <InputNumber min={0} style={{ width: "100%" }} />
            </Form.Item>
            <Form.Item name="sales_count" label="销量" style={{ width: 120 }}>
              <InputNumber min={0} style={{ width: "100%" }} />
            </Form.Item>
          </Space>

          <Divider plain orientation="left" style={{ fontSize: 13, color: "#8c8c8c" }}>描述与卖点</Divider>
          <Form.Item name="highlights" label="卖点">
            <Input placeholder="如：316不锈钢、48小时保温、智能温显" />
          </Form.Item>
          <Form.Item name="description" label="详细描述">
            <TextArea rows={3} placeholder="商品详细描述..." />
          </Form.Item>

          <Space style={{ width: "100%" }} size="middle">
            <Form.Item name="package_contents" label="包装清单" style={{ width: 300 }}>
              <Input placeholder="如：杯体×1、杯盖×1、说明书×1" />
            </Form.Item>
            <Form.Item name="warranty" label="保修信息" style={{ width: 300 }}>
              <Input placeholder="如：1年质保" />
            </Form.Item>
          </Space>

          <Divider plain orientation="left" style={{ fontSize: 13, color: "#8c8c8c" }}>扩展信息</Divider>
          <Space style={{ width: "100%" }} size="middle">
            <Form.Item name="tags" label="标签（逗号分隔）" style={{ width: 300 }}>
              <Input placeholder="如：爆款, 新品, 限时优惠" />
            </Form.Item>
            <Form.Item name="image_url" label="图片链接" style={{ width: 340 }}>
              <Input placeholder="可留空" />
            </Form.Item>
          </Space>
          <Form.Item name="specs" label="参数规格（JSON 格式）">
            <TextArea rows={3} placeholder='{"材质": "316不锈钢", "容量": "500ml", "颜色": "白色"}' />
          </Form.Item>
        </Form>
      </Modal>
    </div>
  );
}