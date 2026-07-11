import { useEffect, useMemo, useState } from "react";
import { Row, Col, Segmented, Spin, Empty } from "antd";
import {
  MessageOutlined, ThunderboltOutlined,
  WarningFilled, StarFilled, FrownOutlined,
} from "@ant-design/icons";
import { Line } from "@ant-design/charts";
import { statsApi } from "../../api";
import {
  RADIUS, SHADOW, COLOR_TITLE, COLOR_VALUE, COLOR_NORMAL, COLOR_WARN,
  COLOR_WARN_BG, COLOR_TITLE_BG, FONT_STACK,
  cardBase, cardAlert, titleStyle, valueStyle, moduleHeaderStyle,
} from "./styles";

interface DailyRow { d: string; sessions: number; msgs: number }

const dayOptions = [
  { label: "1天", value: 1 },
  { label: "7天", value: 7 },
  { label: "30天", value: 30 },
  { label: "90天", value: 90 },
];

function StatCard(props: {
  title: string;
  value: number;
  icon: React.ReactNode;
  alert?: boolean;
  iconColor?: string;
}) {
  const { title, value, icon, alert, iconColor } = props;
  return (
    <div style={{
      ...(alert ? cardAlert : cardBase),
      padding: "20px 24px",
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
      <div style={valueStyle}>{value.toLocaleString()}</div>
    </div>
  );
}

export default function DashboardPage() {
  const [days, setDays] = useState(7);
  const [data, setData] = useState<any>(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    setLoading(true);
    statsApi.overview(days)
      .then((r: any) => setData(r.data))
      .catch(() => setData(null))
      .finally(() => setLoading(false));
  }, [days]);

  const daily: DailyRow[] = data?.daily || [];
  const totalSessions = useMemo(
    () => daily.reduce((a, b) => a + (b.sessions || 0), 0),
    [daily],
  );
  const totalMsgs = useMemo(
    () => daily.reduce((a, b) => a + (b.msgs || 0), 0),
    [daily],
  );

  // @ant-design/charts 需要长格式：{ date, value, type }
  const chartData = useMemo(() => {
    const rows: { date: string; value: number; type: string }[] = [];
    daily.forEach((r) => {
      rows.push({ date: r.d, value: r.sessions || 0, type: "会话数" });
      rows.push({ date: r.d, value: r.msgs || 0, type: "消息数" });
    });
    return rows;
  }, [daily]);

  return (
    <div style={{ fontFamily: FONT_STACK }}>
      {/* 顶部：时间切换器 */}
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

      {/* 4 张数据卡 */}
      <Spin spinning={loading}>
        <Row gutter={[16, 16]}>
          <Col xs={24} sm={12} md={6}>
            <StatCard
              title="会话数"
              value={totalSessions}
              icon={<MessageOutlined />}
              iconColor={COLOR_NORMAL}
            />
          </Col>
          <Col xs={24} sm={12} md={6}>
            <StatCard
              title="消息数"
              value={totalMsgs}
              icon={<ThunderboltOutlined />}
              iconColor={COLOR_NORMAL}
            />
          </Col>
          <Col xs={24} sm={12} md={6}>
            <StatCard
              title="转人工"
              value={data?.transfer_human || 0}
              icon={<WarningFilled />}
              alert
            />
          </Col>
          <Col xs={24} sm={12} md={6}>
            <StatCard
              title="差评数"
              value={data?.bad_feedback || 0}
              icon={<FrownOutlined />}
              alert
            />
          </Col>
        </Row>
      </Spin>

      {/* 每日会话趋势 */}
      <div style={{
        marginTop: 16,
        background: "#fff",
        borderRadius: RADIUS,
        boxShadow: SHADOW,
        overflow: "hidden",
      }}>
        <div style={moduleHeaderStyle}>每日会话趋势</div>
        <div style={{ padding: "16px 8px 8px", minHeight: 360 }}>
          <Spin spinning={loading}>
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
          </Spin>
        </div>
      </div>
    </div>
  );
}
