import { useEffect, useState } from "react";
import {
  Card, Row, Col, Select, DatePicker, Space, Statistic, Table, Button, Spin,
} from "antd";
import { DownloadOutlined, ReloadOutlined } from "@ant-design/icons";
import ReactECharts from "echarts-for-react";
import dayjs from "dayjs";
import { statsApi } from "../../../api";

const CHANNEL_LABELS: Record<string, string> = { web: "官网", miniapp: "小程序", wework: "企微" };
const CHANNEL_COLORS: Record<string, string> = { web: "#1890ff", miniapp: "#52c41a", wework: "#fa8c16" };

const LATENCY_COLORS: Record<string, string> = {
  "<1s": "#52c41a", "1-3s": "#1890ff", "3-5s": "#fa8c16", "5-10s": "#fa541c", ">10s": "#f5222d",
};

export default function ServiceStatsPage() {
  const [loading, setLoading] = useState(false);
  const [days, setDays] = useState(30);
  const [data, setData] = useState<any>(null);

  const fetchData = async (d: number) => {
    setLoading(true);
    try {
      const r: any = await statsApi.service(d);
      setData(r.data);
    } catch {
      setData(null);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { fetchData(days); }, []);

  const handleDaysChange = (v: number) => {
    setDays(v);
    fetchData(v);
  };

  const handleExport = () => {
    if (!data) return;
    const csv = [
      "type,label,value",
      ...(data.channels || []).map((c: any) => `channel,${CHANNEL_LABELS[c.name] || c.name},${c.value}`),
      ...(data.latency_dist || []).map((l: any) => `latency,${l.bucket},${l.count}`),
      ...(data.intents || []).map((i: any) => `intent,${i.name},${i.value}`),
      ...(data.agents || []).map((a: any) => `agent,${a.agent},${a.msgs}`),
    ].join("\n");
    const blob = new Blob(["\uFEFF" + csv], { type: "text/csv;charset=utf-8" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `service-stats-${dayjs().format("YYYYMMDD")}.csv`;
    a.click();
    URL.revokeObjectURL(url);
  };

  const totalSessions = data?.daily?.reduce((s: number, r: any) => s + (r.sessions || 0), 0) || 0;
  const totalMsgs = data?.daily?.reduce((s: number, r: any) => s + (r.msgs || 0), 0) || 0;
  const avgLatency = data?.agents?.length
    ? Math.round(data.agents.reduce((s: number, a: any) => s + (a.avg_latency_ms || 0), 0) / data.agents.length / 1000 * 10) / 10
    : 0;

  return (
    <Spin spinning={loading}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 16 }}>
        <Space>
          <Select value={days} onChange={handleDaysChange} style={{ width: 120 }}
            options={[
              { label: "最近 7 天", value: 7 }, { label: "最近 30 天", value: 30 },
              { label: "最近 90 天", value: 90 }, { label: "最近 365 天", value: 365 },
            ]}
          />
          <Button icon={<ReloadOutlined />} onClick={() => fetchData(days)}>刷新</Button>
        </Space>
        <Button icon={<DownloadOutlined />} onClick={handleExport} disabled={!data}>导出 CSV</Button>
      </div>

      {/* 概览卡片 */}
      <Row gutter={[16, 16]} style={{ marginBottom: 16 }}>
        <Col xs={12} sm={6}>
          <Card bordered={false} style={{ borderRadius: 8, boxShadow: "0 1px 3px rgba(0,0,0,0.06)" }}>
            <Statistic title={`${days}天会话总数`} value={totalSessions} />
          </Card>
        </Col>
        <Col xs={12} sm={6}>
          <Card bordered={false} style={{ borderRadius: 8, boxShadow: "0 1px 3px rgba(0,0,0,0.06)" }}>
            <Statistic title={`${days}天消息总数`} value={totalMsgs} />
          </Card>
        </Col>
        <Col xs={12} sm={6}>
          <Card bordered={false} style={{ borderRadius: 8, boxShadow: "0 1px 3px rgba(0,0,0,0.06)" }}>
            <Statistic title="平均响应时间" value={avgLatency} suffix="秒" precision={1} />
          </Card>
        </Col>
        <Col xs={12} sm={6}>
          <Card bordered={false} style={{ borderRadius: 8, boxShadow: "0 1px 3px rgba(0,0,0,0.06)" }}>
            <Statistic title="活跃客服数" value={data?.agents?.length || 0} />
          </Card>
        </Col>
      </Row>

      {/* 图表区 */}
      <Row gutter={[16, 16]} style={{ marginBottom: 16 }}>
        <Col xs={24} lg={12}>
          <Card title="每日会话趋势" bordered={false}
            style={{ borderRadius: 8, boxShadow: "0 1px 3px rgba(0,0,0,0.06)" }}
          >
            <ReactECharts
              style={{ height: 300 }}
              option={{
                tooltip: { trigger: "axis" },
                legend: { data: ["会话数", "消息数"], top: 0, right: 10, orient: "vertical" },
                grid: { left: 50, right: 60, top: 20, bottom: 30 },
                xAxis: { type: "category", data: (data?.daily || []).map((r: any) => r.d) },
                yAxis: { type: "value" },
                series: [
                  { name: "会话数", type: "line", data: (data?.daily || []).map((r: any) => r.sessions), smooth: true, color: "#1890ff" },
                  { name: "消息数", type: "line", data: (data?.daily || []).map((r: any) => r.msgs), smooth: true, color: "#52c41a" },
                ],
              }}
              notMerge
            />
          </Card>
        </Col>
        <Col xs={24} lg={12}>
          <Card title="渠道来源分布" bordered={false}
            style={{ borderRadius: 8, boxShadow: "0 1px 3px rgba(0,0,0,0.06)" }}
          >
            <ReactECharts
              style={{ height: 300 }}
              option={{
                tooltip: { trigger: "item" },
                legend: { bottom: 0 },
                series: [{
                  type: "pie", radius: ["40%", "65%"],
                  data: (data?.channels || []).map((c: any) => ({
                    name: CHANNEL_LABELS[c.name] || c.name,
                    value: c.value,
                    itemStyle: { color: CHANNEL_COLORS[c.name] || "#d9d9d9" },
                  })),
                  label: { formatter: "{b}: {c}" },
                }],
              }}
              notMerge
            />
          </Card>
        </Col>
      </Row>

      <Row gutter={[16, 16]} style={{ marginBottom: 16 }}>
        <Col xs={24} lg={12}>
          <Card title="响应时间分布" bordered={false}
            style={{ borderRadius: 8, boxShadow: "0 1px 3px rgba(0,0,0,0.06)" }}
          >
            <ReactECharts
              style={{ height: 300 }}
              option={{
                tooltip: { trigger: "axis" },
                grid: { left: 50, right: 20, top: 20, bottom: 30 },
                xAxis: { type: "category", data: (data?.latency_dist || []).map((l: any) => l.bucket) },
                yAxis: { type: "value", name: "消息数" },
                series: [{
                  type: "bar",
                  data: (data?.latency_dist || []).map((l: any) => ({
                    value: l.count,
                    itemStyle: { color: LATENCY_COLORS[l.bucket] || "#d9d9d9" },
                  })),
                }],
              }}
              notMerge
            />
          </Card>
        </Col>
        <Col xs={24} lg={12}>
          <Card title="问题类型分布" bordered={false}
            style={{ borderRadius: 8, boxShadow: "0 1px 3px rgba(0,0,0,0.06)" }}
          >
            <ReactECharts
              style={{ height: 300 }}
              option={{
                tooltip: { trigger: "item" },
                legend: { bottom: 0, type: "scroll" },
                series: [{
                  type: "pie", radius: "65%",
                  data: (data?.intents || []).map((i: any) => ({ name: i.name, value: i.value })),
                  label: { formatter: "{b}: {c}" },
                }],
              }}
              notMerge
            />
          </Card>
        </Col>
      </Row>

      {/* 客服工作量表格 */}
      <Card title="客服工作量排行" bordered={false}
        style={{ borderRadius: 8, boxShadow: "0 1px 3px rgba(0,0,0,0.06)" }}
      >
        <Table
          rowKey="agent"
          dataSource={data?.agents || []}
          pagination={false}
          columns={[
            { title: "客服", dataIndex: "agent", width: 150 },
            { title: "服务会话数", dataIndex: "sessions", width: 120, align: "center" },
            { title: "回复消息数", dataIndex: "msgs", width: 120, align: "center" },
            {
              title: "平均响应时间", dataIndex: "avg_latency_ms", width: 140, align: "center",
              render: (v: number) => v ? `${(v / 1000).toFixed(1)}s` : "-",
            },
          ]}
        />
      </Card>
    </Spin>
  );
}