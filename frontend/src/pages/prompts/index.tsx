import { useEffect, useState } from "react";
import { Card, Select, Button, Input, Table, message, Space, Tag, Modal, Row, Col } from "antd";
import { promptApi } from "../../api";

export default function PromptsPage() {
  const [agents, setAgents] = useState<string[]>([]);
  const [agent, setAgent] = useState<string>("main_agent");
  const [versions, setVersions] = useState<any[]>([]);
  const [editing, setEditing] = useState<string>("");
  const [changeNote, setChangeNote] = useState("");
  const [compareModal, setCompareModal] = useState<{ open: boolean; a?: number; b?: number; q?: string }>({ open: false });
  const [compareResult, setCompareResult] = useState<any>(null);

  const loadAgents = async () => {
    const r: any = await promptApi.agents();
    setAgents(r.data || []);
  };
  const loadVersions = async () => {
    const r: any = await promptApi.versions(agent);
    setVersions(r.data || []);
    const act = (r.data || []).find((v: any) => v.is_active);
    setEditing(act?.content || "");
  };

  useEffect(() => { loadAgents(); }, []);
  useEffect(() => { loadVersions(); }, [agent]);

  const save = async () => {
    try {
      await promptApi.save(agent, editing, changeNote);
      message.success("已保存新版本");
      setChangeNote("");
      loadVersions();
    } catch (e: any) { message.error(e.message); }
  };

  const activate = async (vid: number) => {
    await promptApi.activate(vid);
    message.success("已切换启用版本");
    loadVersions();
  };

  const runCompare = async () => {
    if (!compareModal.a || !compareModal.b || !compareModal.q) return;
    try {
      const r: any = await promptApi.compare(compareModal.a, compareModal.b, compareModal.q);
      setCompareResult(r.data);
    } catch (e: any) { message.error(e.message); }
  };

  return (
    <div>
      <Card
        title="提示词版本管理"
        extra={
          <Select value={agent} onChange={setAgent} style={{ width: 200 }}
            options={agents.map((a) => ({ value: a, label: a }))} />
        }
        style={{ marginBottom: 16 }}
      >
        <Space direction="vertical" style={{ width: "100%" }}>
          <Input.TextArea value={editing} onChange={(e) => setEditing(e.target.value)} rows={12} />
          <Space>
            <Input placeholder="修改说明（可选）" value={changeNote} onChange={(e) => setChangeNote(e.target.value)} style={{ width: 300 }} />
            <Button type="primary" onClick={save}>保存为新版本</Button>
          </Space>
        </Space>
      </Card>

      <Card title="历史版本">
        <Table
          rowKey="id"
          dataSource={versions}
          columns={[
            { title: "版本", dataIndex: "version_no", render: (v: number) => `v${v}` },
            { title: "修改说明", dataIndex: "change_note" },
            { title: "自动生成", dataIndex: "auto_generated", render: (v: number) => v ? <Tag color="orange">是</Tag> : <Tag>否</Tag> },
            { title: "创建人", dataIndex: "created_by" },
            { title: "创建时间", dataIndex: "created_at" },
            {
              title: "状态", dataIndex: "is_active",
              render: (v: number) => v ? <Tag color="green">启用中</Tag> : <Tag>未启用</Tag>,
            },
            {
              title: "操作", render: (_: any, r: any) => (
                <Space>
                  {!r.is_active && <Button size="small" type="link" onClick={() => activate(r.id)}>启用</Button>}
                  <Button size="small" type="link" onClick={() => setCompareModal({ open: true, a: r.id, b: compareModal.b, q: compareModal.q })}>加入对比</Button>
                </Space>
              ),
            },
          ]}
        />
      </Card>

      <Modal
        open={compareModal.open}
        title="版本对比"
        onCancel={() => { setCompareModal({ open: false }); setCompareResult(null); }}
        width={900}
        footer={[
          <Button key="run" type="primary" onClick={runCompare}>运行对比</Button>,
          <Button key="close" onClick={() => { setCompareModal({ open: false }); setCompareResult(null); }}>关闭</Button>,
        ]}
      >
        <Space direction="vertical" style={{ width: "100%" }}>
          <Input.TextArea placeholder="测试问题" value={compareModal.q} onChange={(e) => setCompareModal({ ...compareModal, q: e.target.value })} rows={2} />
          <Space>
            <span>版本A: v{versions.find(v => v.id === compareModal.a)?.version_no || "-"}</span>
            <span>版本B: v{versions.find(v => v.id === compareModal.b)?.version_no || "-"}</span>
          </Space>
          {compareResult && (
            <Row gutter={16}>
              <Col span={12}>
                <Card title={`版本A (v${compareResult.version_a.version_no})`} size="small">
                  <pre style={{ whiteSpace: "pre-wrap" }}>{compareResult.version_a.answer}</pre>
                </Card>
              </Col>
              <Col span={12}>
                <Card title={`版本B (v${compareResult.version_b.version_no})`} size="small">
                  <pre style={{ whiteSpace: "pre-wrap" }}>{compareResult.version_b.answer}</pre>
                </Card>
              </Col>
            </Row>
          )}
        </Space>
      </Modal>
    </div>
  );
}
