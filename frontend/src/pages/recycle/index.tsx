import { useEffect, useState } from "react";
import { Card, Table, Button, Select, message, Tag } from "antd";
import { recycleApi } from "../../api";

const TABLES = ["", "users", "orders", "sessions", "messages", "prompt_versions", "feedback", "examples", "knowledge_meta"];

export default function RecyclePage() {
  const [table, setTable] = useState("");
  const [rows, setRows] = useState<any[]>([]);

  const load = async () => {
    try {
      const r: any = await recycleApi.list(table);
      setRows(r.data || []);
    } catch (e: any) { message.error(e.message); }
  };

  useEffect(() => { load(); }, [table]);

  const restore = async (id: number) => {
    try {
      await recycleApi.restore(id);
      message.success("已恢复");
      load();
    } catch (e: any) { message.error(e.message); }
  };

  return (
    <Card title="回收站 - 一键回溯" extra={
      <Select value={table} onChange={setTable} style={{ width: 200 }}
        options={TABLES.map((t) => ({ value: t, label: t || "全部表" }))} />
    }>
      <Table
        rowKey="id"
        dataSource={rows}
        columns={[
          { title: "表", dataIndex: "table_name", render: (t: string) => <Tag color="blue">{t}</Tag> },
          { title: "记录ID", dataIndex: "record_id" },
          { title: "删除人", dataIndex: "deleted_by" },
          { title: "删除时间", dataIndex: "deleted_at" },
          { title: "恢复时间", dataIndex: "restored_at", render: (v: string) => v || "-" },
          {
            title: "操作", render: (_: any, r: any) => (
              <Button type="primary" size="small" disabled={!!r.restored_at} onClick={() => restore(r.id)}>恢复</Button>
            ),
          },
        ]}
      />
    </Card>
  );
}
