import { useEffect, useState } from "react";
import { Card, Segmented, Table, Tag, Row, Col, Statistic, Spin } from "antd";
import {
  CheckCircleOutlined, CloseCircleOutlined, WarningOutlined,
  CloudServerOutlined, DatabaseOutlined, HddOutlined, DashboardOutlined,
  TeamOutlined, ClockCircleOutlined, ReloadOutlined,
} from "@ant-design/icons";
import { opsApi } from "../../../api";

const STATUS_CONFIG: Record<string, { color: string; icon: React.ReactNode }> = {
  ok: { color: "#52c41a", icon: <CheckCircleOutlined /> },
  warning: { color: "#fa8c16", icon: <WarningOutlined /> },
  error: { color: "#f5222d", icon: <CloseCircleOutlined /> },
};

function formatUptime(seconds: number): string {
  const d = Math.floor(seconds / 86400);
  const h = Math.floor((seconds % 86400) / 3600);
  const m = Math.floor((seconds % 3600) / 60);
  if (d > 0) return `${d}天 ${h}时 ${m}分`;
  if (h > 0) return `${h}时 ${m}分`;
  return `${m}分`;
}

export default function OpsPage() {
  const [days, setDays] = useState(7);
  const [tools, setTools] = useState<any[]>([]);
  const [tokens, setTokens] = useState<any[]>([]);
  const [errors, setErrors] = useState<any[]>([]);
  const [latency, setLatency] = useState<any[]>([]);
  const [sysStatus, setSysStatus] = useState<any>(null);
  const [statusLoading, setStatusLoading] = useState(false);

  const fetchSysStatus = async () => {
    setStatusLoading(true);
    try {
      const r: any = await opsApi.systemStatus();
      setSysStatus(r.data);
    } catch {
      setSysStatus(null);
    } finally {
      setStatusLoading(false);
    }
  };

  useEffect(() => {
    opsApi.toolStats(days).then((r: any) => setTools(r.data || []));
    opsApi.tokenStats(days).then((r: any) => setTokens(r.data || []));
    opsApi.topErrors(days).then((r: any) => setErrors(r.data || []));
    opsApi.taskLatency(days).then((r: any) => setLatency(r.data || []));
    fetchSysStatus();
  }, [days]);

  const statusItems = [
    { key: "server", icon: <CloudServerOutlined />, data: sysStatus?.server },
    { key: "db", icon: <DatabaseOutlined />, data: sysStatus?.db },
    { key: "qdrant", icon: <DashboardOutlined />, data: sysStatus?.qdrant },
    { key: "disk", icon: <HddOutlined />, data: sysStatus?.disk },
    { key: "memory", icon: <DashboardOutlined />, data: sysStatus?.memory },
  ];

  return (
    <div>
      {/* 系统状态卡片 */}
      <Spin spinning={statusLoading}>
        <Row gutter={[16, 16]} style={{ marginBottom: 16 }}>
          {statusItems.map((s) => {
            const cfg = STATUS_CONFIG[s.data?.status] || STATUS_CONFIG.ok;
            return (
              <Col xs={12} sm={8} md={4} key={s.key}>
                <Card
                  bordered={false}
                  style={{ borderRadius: 8, boxShadow: "0 1px 3px rgba(0,0,0,0.06)", textAlign: "center" }}
                  bodyStyle={{ padding: "12px 8px" }}
                >
                  <div style={{ fontSize: 24, color: cfg.color, marginBottom: 4 }}>{s.icon}</div>
                  <div style={{ fontSize: 13, fontWeight: 500, marginBottom: 2 }}>{s.data?.label || "..."}</div>
                  <div style={{ fontSize: 12, color: cfg.color, display: "flex", alignItems: "center", justifyContent: "center", gap: 4 }}>
                    {cfg.icon}
                    {s.data?.detail || "检测中..."}
                  </div>
                </Card>
              </Col>
            );
          })}
          <Col xs={12} sm={8} md={4}>
            <Card
              bordered={false}
              style={{ borderRadius: 8, boxShadow: "0 1px 3px rgba(0,0,0,0.06)", textAlign: "center" }}
              bodyStyle={{ padding: "12px 8px" }}
            >
              <div style={{ fontSize: 24, color: "#1890ff", marginBottom: 4 }}><TeamOutlined /></div>
              <div style={{ fontSize: 13, fontWeight: 500, marginBottom: 2 }}>在线客服</div>
              <Statistic value={sysStatus?.online_agents?.count || 0} valueStyle={{ fontSize: 18, color: "#1890ff" }} />
            </Card>
          </Col>
          <Col xs={12} sm={8} md={4}>
            <Card
              bordered={false}
              style={{ borderRadius: 8, boxShadow: "0 1px 3px rgba(0,0,0,0.06)", textAlign: "center" }}
              bodyStyle={{ padding: "12px 8px" }}
            >
              <div style={{ fontSize: 24, color: "#722ed1", marginBottom: 4 }}><ClockCircleOutlined /></div>
              <div style={{ fontSize: 13, fontWeight: 500, marginBottom: 2 }}>运行时长</div>
              <div style={{ fontSize: 18, fontWeight: 600, color: "#722ed1" }}>
                {formatUptime(sysStatus?.uptime_seconds || 0)}
              </div>
            </Card>
          </Col>
        </Row>
      </Spin>

      <Segmented
        options={[
          { label: "1天", value: 1 }, { label: "7天", value: 7 },
          { label: "30天", value: 30 }, { label: "90天", value: 90 },
        ]}
        value={days}
        onChange={(v) => setDays(v as number)}
        style={{ marginBottom: 16 }}
      />

      <Card title="工具调用成功率" style={{ marginBottom: 16 }}>
        <Table
          rowKey="tool_name"
          dataSource={tools}
          pagination={false}
          columns={[
            { title: "工具", dataIndex: "tool_name" },
            { title: "调用数", dataIndex: "total" },
            { title: "成功数", dataIndex: "success_cnt" },
            { title: "失败数", dataIndex: "fail_cnt" },
            { title: "平均耗时(ms)", dataIndex: "avg_latency", render: (v: number) => v?.toFixed(0) },
            {
              title: "成功率", render: (_: any, r: any) =>
                <Tag color={r.total ? (r.success_cnt / r.total > 0.9 ? "green" : "orange") : "default"}>
                  {r.total ? ((r.success_cnt / r.total) * 100).toFixed(1) : 0}%
                </Tag>,
            },
          ]}
        />
      </Card>

      <Card title="任务耗时分布" style={{ marginBottom: 16 }}>
        <Table
          rowKey="stat_date"
          dataSource={latency}
          pagination={false}
          columns={[
            { title: "日期", dataIndex: "stat_date" },
            { title: "任务数", dataIndex: "task_cnt" },
            { title: "平均(ms)", dataIndex: "avg_latency", render: (v: number) => v?.toFixed(0) },
            { title: "最大(ms)", dataIndex: "max_latency" },
          ]}
        />
      </Card>

      <Card title="Token 消耗" style={{ marginBottom: 16 }}>
        <Table
          rowKey={(r) => `${r.stat_date}-${r.agent_name}-${r.model}`}
          dataSource={tokens}
          pagination={false}
          columns={[
            { title: "日期", dataIndex: "stat_date" },
            { title: "Agent", dataIndex: "agent_name" },
            { title: "模型", dataIndex: "model" },
            { title: "Prompt Tokens", dataIndex: "prompt_t" },
            { title: "Completion Tokens", dataIndex: "completion_t" },
            { title: "总计", dataIndex: "total_t" },
          ]}
        />
      </Card>

      <Card title="高频错误 Top-N">
        <Table
          rowKey={(r) => `${r.module}-${r.message}`}
          dataSource={errors}
          pagination={false}
          columns={[
            { title: "模块", dataIndex: "module" },
            { title: "级别", dataIndex: "level", render: (v: string) => <Tag color={v === "ERROR" ? "red" : "orange"}>{v}</Tag> },
            { title: "消息", dataIndex: "message", ellipsis: true },
            { title: "次数", dataIndex: "cnt" },
          ]}
        />
      </Card>
    </div>
  );
}