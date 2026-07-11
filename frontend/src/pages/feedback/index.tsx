import { useEffect, useState } from "react";
import { Card, Table, Tag, Modal, Segmented, message } from "antd";
import { feedbackApi } from "../../api";

export default function FeedbackPage() {
  const [rating, setRating] = useState<string | undefined>(undefined);
  const [rows, setRows] = useState<any[]>([]);
  const [analysis, setAnalysis] = useState<any[]>([]);

  const load = async () => {
    try {
      const r: any = await feedbackApi.list(rating);
      setRows(r.data || []);
      const a: any = await feedbackApi.analysis();
      setAnalysis(a.data || []);
    } catch (e: any) { message.error(e.message); }
  };

  useEffect(() => { load(); }, [rating]);

  return (
    <div>
      <Card title="反馈历史" extra={<Segmented options={[{ label: "全部", value: undefined }, { label: "满意", value: "good" }, { label: "不满意", value: "bad" }]} value={rating} onChange={(v) => setRating(v as any)} />}>
        <Table
          rowKey="id"
          dataSource={rows}
          columns={[
            { title: "评分", dataIndex: "rating", render: (r: string) => <Tag color={r === "good" ? "green" : "red"}>{r === "good" ? "满意" : "不满意"}</Tag> },
            { title: "问题", dataIndex: "question", ellipsis: true },
            { title: "回答", dataIndex: "answer", ellipsis: true },
            { title: "反馈说明", dataIndex: "comment", ellipsis: true },
            { title: "时间", dataIndex: "created_at" },
            {
              title: "操作", render: (_: any, r: any) => (
                <a onClick={async () => {
                  const a: any = await feedbackApi.analysisOf(r.id);
                  Modal.info({
                    title: "原因分析", width: 600,
                    content: a.data ? (
                      <div>
                        <p><b>分类：</b>{a.data.category}</p>
                        <p><b>原因：</b>{a.data.reason}</p>
                        <p><b>改进建议：</b>{a.data.suggestion}</p>
                      </div>
                    ) : "无分析记录",
                  });
                }}>查看分析</a>
              ),
            },
          ]}
        />
      </Card>

      <Card title="原因分析汇总" style={{ marginTop: 16 }}>
        <Table
          rowKey="id"
          dataSource={analysis}
          columns={[
            { title: "反馈ID", dataIndex: "feedback_id" },
            { title: "分类", dataIndex: "category" },
            { title: "原因", dataIndex: "reason", ellipsis: true },
            { title: "改进建议", dataIndex: "suggestion", ellipsis: true },
            { title: "优化版本ID", dataIndex: "optimized_prompt_version_id" },
            { title: "时间", dataIndex: "created_at" },
          ]}
        />
      </Card>
    </div>
  );
}
