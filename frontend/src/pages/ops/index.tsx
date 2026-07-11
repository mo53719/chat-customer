import { useEffect, useState } from "react";
import { Card, Segmented, Table, Tag } from "antd";
import { opsApi } from "../../api";

export default function OpsPage() {
  const [days, setDays] = useState(7);
  const [tools, setTools] = useState<any[]>([]);
  const [tokens, setTokens] = useState<any[]>([]);
  const [errors, setErrors] = useState<any[]>([]);
  const [latency, setLatency] = useState<any[]>([]);

  useEffect(() => {
    opsApi.toolStats(days).then((r: any) => setTools(r.data || []));
    opsApi.tokenStats(days).then((r: any) => setTokens(r.data || []));
    opsApi.topErrors(days).then((r: any) => setErrors(r.data || []));
    opsApi.taskLatency(days).then((r: any) => setLatency(r.data || []));
  }, [days]);

  return (
    <div>
      <Segmented options={[1, 7, 30, 90]} value={days} onChange={(v) => setDays(v as number)} style={{ marginBottom: 16 }} />
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
