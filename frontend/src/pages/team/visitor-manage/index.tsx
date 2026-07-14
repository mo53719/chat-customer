import { useEffect, useState, useCallback } from "react";
import {
  Table, Input, Select, DatePicker, Space, Tag, Card, Button, Row, Col,
} from "antd";
import { SearchOutlined, ReloadOutlined, EyeOutlined, HistoryOutlined } from "@ant-design/icons";
import { useNavigate } from "react-router-dom";
import dayjs from "dayjs";
import { sessionApi } from "../../../api";

const { RangePicker } = DatePicker;

const CHANNEL_MAP: Record<string, string> = { web: "官网", miniapp: "小程序", wework: "企微" };
const STATUS_MAP: Record<string, { color: string; text: string }> = {
  active: { color: "green", text: "对话中" },
  closed: { color: "default", text: "已结束" },
  transferred: { color: "orange", text: "已转接" },
};

interface VisitorItem {
  session_id: string;
  title: string | null;
  channel: string;
  status: string;
  created_at: string;
  visitor_ip: string | null;
  visitor_region: string | null;
  last_active_at: string | null;
  last_message_preview: string | null;
  device: string | null;
  browser: string | null;
  referrer: string | null;
  visit_count: number;
}

export default function VisitorManagePage() {
  const nav = useNavigate();
  const [loading, setLoading] = useState(false);
  const [data, setData] = useState<VisitorItem[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(20);

  const [keyword, setKeyword] = useState("");
  const [channel, setChannel] = useState<string | undefined>();
  const [status, setStatus] = useState<string | undefined>();
  const [dateRange, setDateRange] = useState<[string, string] | null>(null);

  const fetchData = useCallback(async (p?: number, ps?: number) => {
    setLoading(true);
    try {
      const params: any = {
        page: p || page,
        page_size: ps || pageSize,
      };
      if (keyword) params.keyword = keyword;
      if (channel) params.channel = channel;
      if (status) params.status = status;
      if (dateRange) {
        params.date_from = dateRange[0];
        params.date_to = dateRange[1];
      }
      const r: any = await sessionApi.visitors(params);
      setData(r.data.items || []);
      setTotal(r.data.total || 0);
    } catch {
      setData([]);
      setTotal(0);
    } finally {
      setLoading(false);
    }
  }, [keyword, channel, status, dateRange, page, pageSize]);

  useEffect(() => {
    fetchData(1, pageSize);
  }, []);

  const handleSearch = () => {
    setPage(1);
    fetchData(1, pageSize);
  };

  const handlePageChange = (p: number, ps: number) => {
    setPage(p);
    setPageSize(ps);
    fetchData(p, ps);
  };

  const fmtTime = (v: string) => {
    const d = new Date(v + "Z");
    return d.toLocaleString("zh-CN", {
      month: "2-digit", day: "2-digit",
      hour: "2-digit", minute: "2-digit",
    });
  };

  return (
    <div>
      <Card
        bordered={false}
        style={{ borderRadius: 8, boxShadow: "0 1px 3px rgba(0,0,0,0.06)", marginBottom: 16 }}
        bodyStyle={{ padding: "12px 16px" }}
      >
        <Row gutter={[12, 12]} align="middle">
          <Col xs={24} sm={12} md={6}>
            <Input
              placeholder="搜索访客 / IP / 地区"
              prefix={<SearchOutlined />}
              value={keyword}
              onChange={(e) => setKeyword(e.target.value)}
              onPressEnter={handleSearch}
              allowClear
            />
          </Col>
          <Col xs={12} sm={6} md={3}>
            <Select
              placeholder="渠道"
              value={channel}
              onChange={(v) => setChannel(v)}
              allowClear
              style={{ width: "100%" }}
              options={[
                { label: "官网", value: "web" },
                { label: "小程序", value: "miniapp" },
                { label: "企微", value: "wework" },
              ]}
            />
          </Col>
          <Col xs={12} sm={6} md={3}>
            <Select
              placeholder="状态"
              value={status}
              onChange={(v) => setStatus(v)}
              allowClear
              style={{ width: "100%" }}
              options={[
                { label: "对话中", value: "active" },
                { label: "已结束", value: "closed" },
                { label: "已转接", value: "transferred" },
              ]}
            />
          </Col>
          <Col xs={24} sm={12} md={6}>
            <RangePicker
              style={{ width: "100%" }}
              onChange={(dates) => {
                if (dates && dates[0] && dates[1]) {
                  setDateRange([dates[0].format("YYYY-MM-DD"), dates[1].format("YYYY-MM-DD")]);
                } else {
                  setDateRange(null);
                }
              }}
            />
          </Col>
          <Col xs={24} sm={12} md={6}>
            <Space>
              <Button type="primary" icon={<SearchOutlined />} onClick={handleSearch}>搜索</Button>
              <Button icon={<ReloadOutlined />} onClick={() => {
                setKeyword(""); setChannel(undefined); setStatus(undefined);
                setDateRange(null); setPage(1);
                setTimeout(() => fetchData(1, pageSize), 0);
              }}>重置</Button>
            </Space>
          </Col>
        </Row>
      </Card>

      <Card
        bordered={false}
        style={{ borderRadius: 8, boxShadow: "0 1px 3px rgba(0,0,0,0.06)" }}
        bodyStyle={{ padding: 0 }}
      >
        <Table
          rowKey="session_id"
          dataSource={data}
          loading={loading}
          pagination={{
            current: page,
            pageSize,
            total,
            showSizeChanger: true,
            showTotal: (t) => `共 ${t} 条`,
            onChange: handlePageChange,
          }}
          columns={[
            {
              title: "访客",
              dataIndex: "title",
              ellipsis: true,
              width: 180,
              render: (v: string | null, r: VisitorItem) => (
                <div>
                  <div style={{ fontWeight: 500 }}>{v || "（未命名会话）"}</div>
                  <div style={{ fontSize: 12, color: "#8c8c8c" }}>
                    {r.visitor_ip || "IP 未知"} {r.visitor_region ? `· ${r.visitor_region}` : ""}
                  </div>
                </div>
              ),
            },
            {
              title: "渠道",
              dataIndex: "channel",
              width: 80,
              render: (v: string) => <Tag>{CHANNEL_MAP[v] || v}</Tag>,
            },
            {
              title: "设备",
              dataIndex: "device",
              width: 130,
              ellipsis: true,
              render: (v: string | null) => v || "未知",
            },
            {
              title: "来源",
              dataIndex: "referrer",
              width: 100,
              ellipsis: true,
              render: (v: string | null) => v || "-",
            },
            {
              title: "访问次数",
              dataIndex: "visit_count",
              width: 80,
              align: "center",
            },
            {
              title: "状态",
              dataIndex: "status",
              width: 90,
              render: (v: string) => {
                const s = STATUS_MAP[v] || { color: "default", text: v };
                return <Tag color={s.color}>{s.text}</Tag>;
              },
            },
            {
              title: "最近消息",
              dataIndex: "last_message_preview",
              ellipsis: true,
              width: 200,
              render: (v: string | null) => v ? (
                <span style={{ color: "#8c8c8c", fontSize: 13 }}>{v}</span>
              ) : "-",
            },
            {
              title: "访问时间",
              dataIndex: "created_at",
              width: 140,
              render: (v: string) => fmtTime(v),
            },
            {
              title: "操作",
              width: 120,
              render: (_: any, r: VisitorItem) => (
                <Space size="small">
                  <Button
                    type="link" size="small" icon={<EyeOutlined />}
                    onClick={() => nav(`/chat?session=${r.session_id}`)}
                  >查看</Button>
                </Space>
              ),
            },
          ]}
        />
      </Card>
    </div>
  );
}