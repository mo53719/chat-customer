import { useEffect, useMemo, useState } from "react";
import { Row, Col, Segmented, Spin, Empty, Table, Tag, Tooltip } from "antd";
import {
  MessageOutlined, ThunderboltOutlined, ClockCircleOutlined,
  SmileOutlined, WarningFilled, FrownOutlined,
  TeamOutlined, UserAddOutlined,
  ArrowUpOutlined, ArrowDownOutlined,
  PlusOutlined, FileTextOutlined, ShoppingCartOutlined,
  ControlOutlined, BarChartOutlined,
} from "@ant-design/icons";
import { Line, Pie } from "@ant-design/charts";
import { useNavigate } from "react-router-dom";
import { statsApi } from "../../../api";
import {
  RADIUS, SHADOW, COLOR_TITLE, COLOR_VALUE, COLOR_NORMAL, COLOR_WARN, COLOR_SUCCESS,
  COLOR_WARN_BG, COLOR_TITLE_BG, FONT_STACK,
  cardBase, cardAlert, titleStyle, valueStyle, moduleHeaderStyle,
  calcTrend, trendStyle,
} from "./styles";

interface DailyRow { d: string; sessions: number; msgs: number }
interface IntentRow { name: string; value: number }
interface RecentSession {
  session_id: string;
  title: string | null;
  channel: string;
  status: string;
  created_at: string;
  visitor_region: string | null;
  last_message_preview: string | null;
  last_active_at: string | null;
}

const dayOptions = [
  { label: "1天", value: 1 },
  { label: "7天", value: 7 },
  { label: "30天", value: 30 },
  { label: "90天", value: 90 },
];

const STATUS_MAP: Record<string, { color: string; text: string }> = {
  active: { color: "green", text: "对话中" },
  closed: { color: "default", text: "已结束" },
  transferred: { color: "orange", text: "已转接" },
};

/** 快捷操作卡片 */
function QuickActionCard(props: {
  title: string;
  icon: React.ReactNode;
  color: string;
  bg: string;
  onClick: () => void;
  disabled?: boolean;
}) {
  const { title, icon, color, bg, onClick, disabled } = props;
  return (
    <div
      onClick={disabled ? undefined : onClick}
      style={{
        background: "#fff",
        borderRadius: RADIUS,
        boxShadow: SHADOW,
        padding: "14px 16px",
        display: "flex",
        alignItems: "center",
        gap: 12,
        cursor: disabled ? "not-allowed" : "pointer",
        opacity: disabled ? 0.5 : 1,
        transition: "box-shadow 0.2s, transform 0.2s",
        height: "100%",
      }}
      onMouseEnter={(e) => {
        if (!disabled) {
          e.currentTarget.style.boxShadow = "0 4px 12px rgba(0,0,0,0.15)";
          e.currentTarget.style.transform = "translateY(-1px)";
        }
      }}
      onMouseLeave={(e) => {
        e.currentTarget.style.boxShadow = SHADOW;
        e.currentTarget.style.transform = "none";
      }}
    >
      <div style={{
        width: 36, height: 36, borderRadius: 8,
        background: bg,
        display: "flex", alignItems: "center", justifyContent: "center",
        fontSize: 18, color,
      }}>{icon}</div>
      <span style={{ fontSize: 14, fontWeight: 500, color: COLOR_VALUE }}>
        {title}{disabled ? "（开发中）" : ""}
      </span>
    </div>
  );
}

const quickActions = [
  { title: "新建对话", icon: <PlusOutlined />, color: "#1890ff", bg: "#e6f4ff", path: "/chat" },
  { title: "知识库管理", icon: <FileTextOutlined />, color: "#722ed1", bg: "#f9f0ff", path: "/team/rag" },
  { title: "商品管理", icon: <ShoppingCartOutlined />, color: "#eb2f96", bg: "#fff0f6", path: "/mall/products" },
  { title: "运维观测", icon: <ControlOutlined />, color: "#13c2c2", bg: "#e6fffb", path: "/ops" },
  { title: "生成报表", icon: <BarChartOutlined />, color: "#fa8c16", bg: "#fff7e6", path: "", disabled: true },
];
function StatCard(props: {
  title: string;
  value: number | string;
  icon: React.ReactNode;
  alert?: boolean;
  iconColor?: string;
  trend?: { up: boolean; pct: number };
}) {
  const { title, value, icon, alert, iconColor, trend } = props;
  return (
    <div style={{
      ...(alert ? cardAlert : cardBase),
      padding: "16px 20px",
      height: "100%",
    }}>
      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
        <span style={titleStyle}>{title}</span>
        <span style={{
          fontSize: 18,
          color: iconColor || (alert ? COLOR_WARN : COLOR_NORMAL),
          opacity: 0.85,
        }}>{icon}</span>
      </div>
      <div style={{ display: "flex", alignItems: "baseline", marginTop: 6 }}>
        <span style={valueStyle}>{typeof value === "number" ? value.toLocaleString() : value}</span>
        {trend && trend.pct > 0 && (
          <span style={trendStyle(trend.up)}>
            {trend.up ? <ArrowUpOutlined /> : <ArrowDownOutlined />}
            {trend.pct}%
          </span>
        )}
      </div>
    </div>
  );
}

export default function DashboardPage() {
  const nav = useNavigate();
  const [days, setDays] = useState(7);
  const [data, setData] = useState<any>(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    setLoading(true);
    statsApi.dashboard(days)
      .then((r: any) => setData(r.data))
      .catch(() => setData(null))
      .finally(() => setLoading(false));
  }, [days]);

  const today = data?.today || {};
  const yesterday = data?.yesterday || {};
  const daily: DailyRow[] = data?.daily || [];
  const intents: IntentRow[] = data?.intents || [];
  const recentSessions: RecentSession[] = data?.recent_sessions || [];

  // 折线图数据
  const chartData = useMemo(() => {
    const rows: { date: string; value: number; type: string }[] = [];
    daily.forEach((r) => {
      rows.push({ date: r.d, value: r.sessions || 0, type: "会话数" });
      rows.push({ date: r.d, value: r.msgs || 0, type: "消息数" });
    });
    return rows;
  }, [daily]);

  // 饼图数据（意图分布）
  const pieData = useMemo(() => {
    if (intents.length === 0) return [];
    const total = intents.reduce((s, i) => s + i.value, 0);
    return intents.map((i) => ({ name: i.name, value: i.value, percent: ((i.value / total) * 100).toFixed(1) }));
  }, [intents]);

  // 环比趋势
  const sessionsTrend = calcTrend(today.sessions || 0, yesterday.sessions || 0);
  const msgsTrend = calcTrend(today.messages || 0, yesterday.messages || 0);
  const satisfactionTrend = calcTrend(today.satisfaction || 0, yesterday.satisfaction || 0);
  const transferTrend = calcTrend(today.transfer_human || 0, yesterday.transfer_human || 0);
  const badTrend = calcTrend(today.bad_feedback || 0, yesterday.bad_feedback || 0);
  const visitorsTrend = calcTrend(today.new_visitors || 0, yesterday.new_visitors || 0);

  const fmtLatency = (ms: number) => {
    if (ms >= 1000) return `${(ms / 1000).toFixed(1)}s`;
    return `${ms}ms`;
  };

  return (
    <div style={{ fontFamily: FONT_STACK }}>
      {/* 顶部：标题 + 时间切换器 */}
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 16 }}>
        <span style={{ fontSize: 18, fontWeight: 600, color: COLOR_VALUE }}>数据看板</span>
        <Segmented
          options={dayOptions}
          value={days}
          onChange={(v) => setDays(v as number)}
          style={{
            background: "#f5f7fa",
            border: "1px solid #e8ecef",
            borderRadius: RADIUS,
            padding: 2,
          }}
        />
      </div>

      {/* 快捷操作 */}
      <Row gutter={[16, 16]} style={{ marginBottom: 16 }}>
        {quickActions.map((a) => (
          <Col xs={12} sm={8} md={24 / 5} key={a.title}>
            <QuickActionCard
              title={a.title}
              icon={a.icon}
              color={a.color}
              bg={a.bg}
              disabled={a.disabled}
              onClick={() => nav(a.path)}
            />
          </Col>
        ))}
      </Row>

      <Spin spinning={loading}>
        {/* 第一行：核心指标 */}
        <Row gutter={[16, 16]}>
          <Col xs={24} sm={12} md={6}>
            <StatCard title="会话数" value={today.sessions || 0}
              icon={<MessageOutlined />} iconColor={COLOR_NORMAL} trend={sessionsTrend} />
          </Col>
          <Col xs={24} sm={12} md={6}>
            <StatCard title="消息数" value={today.messages || 0}
              icon={<ThunderboltOutlined />} iconColor={COLOR_NORMAL} trend={msgsTrend} />
          </Col>
          <Col xs={24} sm={12} md={6}>
            <StatCard title="平均响应时间" value={fmtLatency(today.avg_latency_ms || 0)}
              icon={<ClockCircleOutlined />} iconColor={COLOR_SUCCESS}
              trend={today.avg_latency_ms && yesterday.avg_latency_ms
                ? calcTrend(yesterday.avg_latency_ms, today.avg_latency_ms) : undefined} />
          </Col>
          <Col xs={24} sm={12} md={6}>
            <StatCard title="满意度" value={`${today.satisfaction || 0}%`}
              icon={<SmileOutlined />} iconColor={COLOR_SUCCESS} trend={satisfactionTrend} />
          </Col>
        </Row>

        {/* 第二行：预警指标 */}
        <Row gutter={[16, 16]} style={{ marginTop: 16 }}>
          <Col xs={24} sm={12} md={6}>
            <StatCard title="转人工" value={today.transfer_human || 0}
              icon={<WarningFilled />} alert trend={transferTrend} />
          </Col>
          <Col xs={24} sm={12} md={6}>
            <StatCard title="差评数" value={today.bad_feedback || 0}
              icon={<FrownOutlined />} alert trend={badTrend} />
          </Col>
          <Col xs={24} sm={12} md={6}>
            <StatCard title="在线客服" value={today.online_agents || 0}
              icon={<TeamOutlined />} iconColor={COLOR_NORMAL} />
          </Col>
          <Col xs={24} sm={12} md={6}>
            <StatCard title="今日新增访客" value={today.new_visitors || 0}
              icon={<UserAddOutlined />} iconColor={COLOR_NORMAL} trend={visitorsTrend} />
          </Col>
        </Row>
      </Spin>

      {/* 图表区域：双图并排 */}
      <Spin spinning={loading}>
        <Row gutter={[16, 16]} style={{ marginTop: 16 }}>
          {/* 左侧：每日会话趋势 */}
          <Col xs={24} lg={14}>
            <div style={{
              background: "#fff",
              borderRadius: RADIUS,
              boxShadow: SHADOW,
              overflow: "hidden",
            }}>
              <div style={moduleHeaderStyle}>每日会话趋势</div>
              <div style={{ padding: "16px 8px 8px", minHeight: 360 }}>
                {chartData.length === 0 ? (
                  <div style={{
                    height: 320, display: "flex", alignItems: "center", justifyContent: "center",
                    flexDirection: "column", color: COLOR_TITLE,
                  }}>
                    <Empty description="暂无数据" />
                  </div>
                ) : (
                  <Line
                    data={chartData}
                    height={320}
                    xField="date"
                    yField="value"
                    seriesField="type"
                    color={["#1890ff", "#52c41a"]}
                    smooth
                    point={{ size: 4, shape: "circle" }}
                    line={{ style: { lineWidth: 2 } }}
                    legend={{ position: "top-right" }}
                    tooltip={{
                      shared: true,
                      showCrosshairs: true,
                    }}
                    yAxis={{
                      label: { style: { fill: COLOR_TITLE, fontSize: 12 } },
                    }}
                    xAxis={{
                      label: { style: { fill: COLOR_TITLE, fontSize: 12 } },
                    }}
                  />
                )}
              </div>
            </div>
          </Col>

          {/* 右侧：问题类型分布 */}
          <Col xs={24} lg={10}>
            <div style={{
              background: "#fff",
              borderRadius: RADIUS,
              boxShadow: SHADOW,
              overflow: "hidden",
            }}>
              <div style={moduleHeaderStyle}>问题类型分布</div>
              <div style={{ padding: "16px 8px 8px", minHeight: 360 }}>
                {pieData.length === 0 ? (
                  <div style={{
                    height: 320, display: "flex", alignItems: "center", justifyContent: "center",
                    flexDirection: "column", color: COLOR_TITLE,
                  }}>
                    <Empty description="暂无意图数据" />
                  </div>
                ) : (
                  <Pie
                    data={pieData}
                    height={320}
                    angleField="value"
                    colorField="name"
                    radius={0.8}
                    innerRadius={0.6}
                    label={{
                      type: "outer",
                      content: "{name} {percentage}",
                    }}
                    legend={{ position: "bottom" }}
                    tooltip={{
                      formatter: (datum: any) => ({
                        name: datum.name,
                        value: `${datum.value} 次 (${datum.percent}%)`,
                      }),
                    }}
                    interactions={[{ type: "element-active" }]}
                  />
                )}
              </div>
            </div>
          </Col>
        </Row>
      </Spin>

      {/* 底部：最近访客列表 */}
      <Spin spinning={loading}>
        <div style={{
          marginTop: 16,
          background: "#fff",
          borderRadius: RADIUS,
          boxShadow: SHADOW,
          overflow: "hidden",
        }}>
          <div style={moduleHeaderStyle}>最近访客</div>
          <Table
            dataSource={recentSessions}
            rowKey="session_id"
            pagination={false}
            size="middle"
            columns={[
              {
                title: "会话标题",
                dataIndex: "title",
                ellipsis: true,
                render: (v: string | null) => v || "（未命名会话）",
              },
              {
                title: "渠道",
                dataIndex: "channel",
                width: 80,
                render: (v: string) => {
                  const m: Record<string, string> = { web: "官网", miniapp: "小程序", wework: "企微" };
                  return <Tag>{m[v] || v}</Tag>;
                },
              },
              {
                title: "地区",
                dataIndex: "visitor_region",
                width: 100,
                render: (v: string | null) => v || "-",
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
                title: "访问时间",
                dataIndex: "created_at",
                width: 160,
                render: (v: string) => {
                  const d = new Date(v + "Z");
                  return d.toLocaleString("zh-CN", {
                    month: "2-digit", day: "2-digit",
                    hour: "2-digit", minute: "2-digit",
                  });
                },
              },
              {
                title: "操作",
                width: 80,
                render: (_: any, r: RecentSession) => (
                  <a onClick={() => nav(`/chat?session=${r.session_id}`)}>查看详情</a>
                ),
              },
            ]}
          />
        </div>
      </Spin>
    </div>
  );
}