import { useEffect, useMemo, useRef, useState } from "react";
import { Input, Button, Tooltip, message, Modal, Tag, Space, Badge, Avatar, Descriptions, Divider, Typography } from "antd";
const { Text } = Typography;
import {
  SearchOutlined, ReloadOutlined, SendOutlined, SmileOutlined,
  PaperClipOutlined, ThunderboltOutlined, CheckCircleTwoTone,
  UserOutlined, GlobalOutlined, ClockCircleOutlined,
  CustomerServiceOutlined, QrcodeOutlined, CloseOutlined,
  FileTextOutlined, LikeOutlined, DislikeOutlined,
  PictureOutlined, AudioOutlined, ScissorOutlined, MoreOutlined,
  EllipsisOutlined, LeftOutlined, PhoneOutlined, VideoCameraOutlined,
  DesktopOutlined, MobileOutlined, TabletOutlined,
  EnvironmentOutlined, GlobalOutlined as GlobalIcon,
  HistoryOutlined, EditOutlined, StarOutlined,
  LinkOutlined, TranslationOutlined, TagOutlined,
} from "@ant-design/icons";
import { chatApi, sessionApi, feedbackApi } from "../../../api";

interface Msg {
  id?: number;
  role: "user" | "assistant";
  content: string;
  created_at?: string;
  agent_name?: string;
  read?: boolean;
  rag_hits?: any[];
}

interface Visitor {
  session_id: string;
  visitor_ip?: string | null;
  visitor_region?: string | null;
  title?: string | null;
  intent_summary?: string | null;
  message_count?: number;
  last_active_at?: string | null;
  last_message_preview?: string | null;
  status?: string;
  created_at?: string;
}

const ONLINE_MINUTES = 5;

function isOnline(v: Visitor): boolean {
  if (!v.last_active_at) return false;
  const t = new Date(v.last_active_at.replace(" ", "T") + (v.last_active_at.includes("Z") ? "" : "Z"));
  if (isNaN(t.getTime())) return false;
  return Date.now() - t.getTime() < ONLINE_MINUTES * 60_000;
}

function relativeTime(t?: string | null): string {
  if (!t) return "-";
  const d = new Date(t.replace(" ", "T") + (t.includes("Z") ? "" : "Z"));
  if (isNaN(d.getTime())) return t;
  const diff = Date.now() - d.getTime();
  if (diff < 60_000) return "刚刚";
  if (diff < 3_600_000) return `${Math.floor(diff / 60_000)} 分钟前`;
  if (diff < 86_400_000) return `${Math.floor(diff / 3_600_000)} 小时前`;
  return d.toLocaleDateString();
}

function regionFlag(region?: string | null) {
  if (!region) return "🌐";
  if (region === "内网") return "🏠";
  if (region === "中国") return "🇨🇳";
  if (region === "海外") return "🌍";
  return "🌐";
}

function shortIp(ip?: string | null) {
  if (!ip) return "未知访客";
  if (ip.length > 15) return ip.slice(0, 15) + "…";
  return ip;
}

function generateQRCodeSVG(text: string, size = 100): string {
  // 占位二维码：用 deterministic 模式生成可视化图案（生产请接 qrcode 库）
  const cells = 21;
  const cell = size / cells;
  let svg = `<svg xmlns="http://www.w3.org/2000/svg" width="${size}" height="${size}" viewBox="0 0 ${size} ${size}">`;
  svg += `<rect width="${size}" height="${size}" fill="#fff"/>`;
  // hash text to seed
  let seed = 0;
  for (let i = 0; i < text.length; i++) seed = (seed * 31 + text.charCodeAt(i)) | 0;
  const rnd = () => (seed = (seed * 9301 + 49297) & 0x7fffffff, seed / 0x7fffffff);
  // 三个定位角
  const corners = [[0, 0], [cells - 7, 0], [0, cells - 7]];
  for (const [cx, cy] of corners) {
    for (let y = 0; y < 7; y++) {
      for (let x = 0; x < 7; x++) {
        const onEdge = x === 0 || x === 6 || y === 0 || y === 6;
        const inner = x >= 2 && x <= 4 && y >= 2 && y <= 4;
        if (onEdge || inner) {
          svg += `<rect x="${(cx + x) * cell}" y="${(cy + y) * cell}" width="${cell}" height="${cell}" fill="#0a2540"/>`;
        }
      }
    }
  }
  // 随机点
  for (let y = 0; y < cells; y++) {
    for (let x = 0; x < cells; x++) {
      // 跳过定位角区域
      const inCorner = (x < 8 && y < 8) || (x > cells - 9 && y < 8) || (x < 8 && y > cells - 9);
      if (inCorner) continue;
      if (rnd() > 0.55) {
        svg += `<rect x="${x * cell}" y="${y * cell}" width="${cell}" height="${cell}" fill="#0a2540"/>`;
      }
    }
  }
  svg += "</svg>";
  return "data:image/svg+xml;utf8," + encodeURIComponent(svg);
}

export default function ChatWorkbench() {
  const [visitors, setVisitors] = useState<Visitor[]>([]);
  const [searchKw, setSearchKw] = useState("");
  const [activeSid, setActiveSid] = useState<string | null>(null);
  const [msgs, setMsgs] = useState<Msg[]>([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [quickReply, setQuickReply] = useState(false);
  const [showQR, setShowQR] = useState(false);
  const [feedback, setFeedback] = useState<{ open: boolean; msg?: Msg; question?: string; text: string }>({
    open: false, text: "",
  });
  const scrollRef = useRef<HTMLDivElement | null>(null);

  // 1. 加载访客列表
  const loadVisitors = async () => {
    try {
      const r: any = await sessionApi.recent(50);
      setVisitors(r.data || []);
      // 默认选第一条
      if (!activeSid && r.data && r.data.length) {
        setActiveSid(r.data[0].session_id);
      }
    } catch (e: any) {
      message.error(e.message);
    }
  };

  useEffect(() => { loadVisitors(); }, []);

  // 2. 选中访客 -> 加载消息
  useEffect(() => {
    if (!activeSid) { setMsgs([]); return; }
    (async () => {
      try {
        const r: any = await sessionApi.messages(activeSid);
        setMsgs((r.data || []).map((m: any) => ({
          id: m.id, role: m.role, content: m.content,
          created_at: m.created_at, agent_name: m.agent_name, read: true,
        })));
      } catch (e: any) { message.error(e.message); }
    })();
  }, [activeSid]);

  // 3. 滚动到底
  useEffect(() => {
    if (scrollRef.current) scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
  }, [msgs]);

  // 4. 定时刷新访客列表（每 30s 同步在线状态）
  useEffect(() => {
    const t = setInterval(() => {
      sessionApi.recent(50).then((r: any) => setVisitors(r.data || [])).catch(() => {});
    }, 30_000);
    return () => clearInterval(t);
  }, []);

  // 5. 分组
  const filtered = useMemo(() => {
    const kw = searchKw.trim().toLowerCase();
    if (!kw) return visitors;
    return visitors.filter((v) =>
      (v.visitor_ip || "").toLowerCase().includes(kw) ||
      (v.visitor_region || "").toLowerCase().includes(kw) ||
      (v.title || "").toLowerCase().includes(kw) ||
      (v.intent_summary || "").toLowerCase().includes(kw) ||
      (v.last_message_preview || "").toLowerCase().includes(kw),
    );
  }, [visitors, searchKw]);

  const onlineList = useMemo(() => filtered.filter(isOnline), [filtered]);
  const allList = useMemo(() => filtered, [filtered]);

  const active = visitors.find((v) => v.session_id === activeSid);

  // 6. 统计
  const stats = useMemo(() => {
    const today = new Date(); today.setHours(0, 0, 0, 0);
    const todayCount = visitors.filter((v) => v.last_active_at && new Date(v.last_active_at.replace(" ", "T") + "Z") >= today).length;
    const online = visitors.filter(isOnline).length;
    const closed = visitors.filter((v) => v.status === "closed").length;
    return { online, today: todayCount, closed, total: visitors.length };
  }, [visitors]);

  // 7. 发送消息
  const send = async () => {
    if (!input.trim() || !activeSid) return;
    const userMsg: Msg = { role: "user", content: input, created_at: new Date().toISOString() };
    setMsgs((m) => [...m, userMsg]);
    setInput("");
    setLoading(true);
    try {
      const r: any = await chatApi.send(userMsg.content, activeSid);
      const asst: Msg = {
        id: r.data.message_id, role: "assistant",
        content: r.data.answer,
        created_at: new Date().toISOString(),
        agent_name: r.data.agent, read: false,
        rag_hits: r.data.rag_hits,
      };
      setMsgs((m) => [...m, asst]);
      loadVisitors();
    } catch (e: any) {
      message.error(e.message);
    } finally {
      setLoading(false);
    }
  };

  // 8. 反馈
  const submitFeedback = async (rating: "good" | "bad") => {
    if (!feedback.msg) return;
    try {
      const r: any = await feedbackApi.submit({
        message_id: feedback.msg.id, session_id: activeSid,
        rating, comment: feedback.text,
        question: feedback.question, answer: feedback.msg.content,
      });
      if (rating === "bad" && r.data?.analysis) {
        Modal.info({
          title: "差评原因分析",
          width: 560,
          content: (
            <div style={{ lineHeight: 1.8 }}>
              <p><b>分类：</b>{r.data.analysis.category}</p>
              <p><b>原因：</b>{r.data.analysis.reason}</p>
              <p><b>建议：</b>{r.data.analysis.suggestion}</p>
              {r.data.optimize?.version_id && (
                <p style={{ color: "#52c41a" }}>已自动生成提示词 v{r.data.optimize.version_id}</p>
              )}
            </div>
          ),
        });
      } else {
        message.success("感谢反馈");
      }
      setFeedback({ open: false, text: "" });
    } catch (e: any) { message.error(e.message); }
  };

  // 9. 转人工 / 关闭
  const transferHuman = async () => {
    if (!activeSid) return;
    await sessionApi.transfer(activeSid);
    message.success("已转人工");
    loadVisitors();
  };
  const closeSession = async () => {
    if (!activeSid) return;
    await sessionApi.close(activeSid);
    message.success("会话已关闭");
    loadVisitors();
  };

  // 10. 快捷回复
  const quickReplies = [
    "您好，请问有什么可以帮您？",
    "正在为您查询，请稍等。",
    "请提供您的订单号或手机号。",
    "感谢您的耐心等待。",
  ];

  return (
    <div style={{
      display: "grid",
      gridTemplateColumns: "260px minmax(0, 1fr) 300px",
      height: "calc(100vh - 24px)",
      background: "#f5f7fa",
      borderRadius: 8,
      overflow: "hidden",
      boxShadow: "0 1px 4px rgba(0,21,41,.08)",
    }}>
      {/* ========== 左侧：访客列表 ========== */}
      <div style={{ background: "#fff", borderRight: "1px solid #e8ecef", display: "flex", flexDirection: "column", minWidth: 0, overflow: "hidden" }}>
        {/* 顶部搜索 */}
        <div style={{ padding: 16, borderBottom: "1px solid #f0f2f5" }}>
          <Input
            prefix={<SearchOutlined style={{ color: "#bfbfbf" }} />}
            placeholder="搜索访客 IP / 地区 / 消息"
            value={searchKw}
            onChange={(e) => setSearchKw(e.target.value)}
            allowClear
          />
        </div>

        {/* 访客列表 */}
        <div style={{ flex: 1, overflow: "auto" }}>
          {/* 在线访客分组 */}
          {onlineList.length > 0 && (
            <>
              <div style={{
                padding: "10px 16px 6px", fontSize: 12, color: "#8c8c8c",
                display: "flex", alignItems: "center", justifyContent: "space-between",
              }}>
                <span>在线访客</span>
                <Badge count={onlineList.length} showZero color="#52c41a" />
              </div>
              {onlineList.map((v) => (
                <VisitorItem
                  key={v.session_id} v={v}
                  active={v.session_id === activeSid}
                  onClick={() => setActiveSid(v.session_id)}
                />
              ))}
            </>
          )}

          {/* 所有访客分组 */}
          <div style={{
            padding: "10px 16px 6px", fontSize: 12, color: "#8c8c8c",
            display: "flex", alignItems: "center", justifyContent: "space-between",
          }}>
            <span>所有访客</span>
            <span>{allList.length}</span>
          </div>
          {allList.map((v) => (
            <VisitorItem
              key={v.session_id} v={v}
              active={v.session_id === activeSid}
              onClick={() => setActiveSid(v.session_id)}
            />
          ))}

          {allList.length === 0 && (
            <div style={{ padding: 40, textAlign: "center", color: "#bfbfbf", fontSize: 13 }}>
              <CustomerServiceOutlined style={{ fontSize: 32, marginBottom: 8 }} />
              <div>暂无访客</div>
            </div>
          )}
        </div>

        {/* 底部操作 */}
        <div style={{
          padding: "8px 16px", borderTop: "1px solid #f0f2f5",
          display: "flex", justifyContent: "space-between", alignItems: "center",
          fontSize: 12, color: "#8c8c8c",
        }}>
          <span>共 {stats.total} 位访客</span>
          <Tooltip title="刷新">
            <Button type="text" size="small" icon={<ReloadOutlined />} onClick={loadVisitors} />
          </Tooltip>
        </div>
      </div>

      {/* ========== 右侧：对话主窗口（极简商务风，按日期分组） ========== */}
      <div style={{ display: "flex", flexDirection: "column", background: "#fafbfc", minHeight: 0, overflow: "hidden" }}>
        {/* 顶部：访客信息 + 操作 */}
        {active ? (
          <div style={{
            background: "#fff", padding: "10px 16px",
            borderBottom: "1px solid #e8ecef",
            display: "flex", justifyContent: "space-between", alignItems: "center",
            flexShrink: 0, gap: 12, minWidth: 0,
          }}>
            <div style={{ flex: 1, minWidth: 0, overflow: "hidden" }}>
              <div style={{ display: "flex", alignItems: "center", gap: 8, minWidth: 0 }}>
                <span style={{ fontSize: 14, fontWeight: 600, color: "#262626", flexShrink: 0 }}>
                  <UserOutlined style={{ marginRight: 6, color: "#1890ff" }} />
                  {shortIp(active.visitor_ip)}
                </span>
                <span style={{ fontSize: 12, color: "#8c8c8c", overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
                  {regionFlag(active.visitor_region)} {active.visitor_region || "未知"}
                </span>
                {active.status === "transferred" && <Tag color="orange" style={{ fontSize: 10, margin: 0, lineHeight: "16px", padding: "0 6px" }}>已转人工</Tag>}
                {active.status === "closed" && <Tag style={{ fontSize: 10, margin: 0, lineHeight: "16px", padding: "0 6px" }}>已结束</Tag>}
                {active.intent_summary && (
                  <Tag color="blue" style={{ fontSize: 10, margin: 0, lineHeight: "16px", padding: "0 6px" }}>{active.intent_summary}</Tag>
                )}
              </div>
              <div style={{ fontSize: 11, color: "#8c8c8c", marginTop: 2 }}>
                <ClockCircleOutlined /> {relativeTime(active.last_active_at)} · 共 {active.message_count || 0} 条消息
              </div>
            </div>
            <Space size={4} style={{ flexShrink: 0 }}>
              <Tooltip title="扫码加入会话（移动端）">
                <Button size="small" icon={<QrcodeOutlined />} onClick={() => setShowQR(true)} />
              </Tooltip>
              <Button size="small" onClick={transferHuman} disabled={active.status === "transferred"}>转人工</Button>
              <Button size="small" onClick={closeSession} disabled={active.status === "closed"}>结束</Button>
            </Space>
          </div>
        ) : (
          <div style={{ background: "#fff", padding: 16, borderBottom: "1px solid #e8ecef", color: "#bfbfbf" }}>
            请在左侧选择一位访客开始对话
          </div>
        )}

        {/* 消息流 + 输入条（flex 布局） */}
        <div style={{ flex: 1, minHeight: 0, display: "flex", flexDirection: "column" }}>
          {/* 滚动消息列表（极简商务风） */}
          <div ref={scrollRef} style={{
            flex: 1, minHeight: 0, overflow: "auto", padding: "16px 24px",
            display: "flex", flexDirection: "column", gap: 4, background: "#fafbfc",
          }}>
            {msgs.length === 0 && active && (
              <div style={{ textAlign: "center", color: "#bfbfbf", padding: 40, fontSize: 13 }}>
                暂无对话记录，发送一条消息开始吧
              </div>
            )}
            {(() => {
              // 按日期分组
              const items: any[] = [];
              let lastDate = "";
              msgs.forEach((m, i) => {
                const d = m.created_at ? new Date(m.created_at.replace(" ", "T") + "Z") : null;
                const dateStr = d ? `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")}` : "";
                if (dateStr && dateStr !== lastDate) {
                  items.push({ type: "date", key: `d-${i}`, date: dateStr });
                  lastDate = dateStr;
                }
                items.push({ type: "msg", key: `m-${i}`, m, i });
              });
              return items.map((it) => {
                if (it.type === "date") return (
                  <div key={it.key} style={{
                    textAlign: "center", margin: "12px 0 8px", fontSize: 11, color: "#8c8c8c",
                  }}>
                    <span style={{
                      background: "#fff", border: "1px solid #e8ecef",
                      padding: "2px 10px", borderRadius: 10,
                    }}>{it.date}</span>
                  </div>
                );
                const m = it.m as Msg;
                const i = it.i as number;
                const isMe = m.role === "assistant";
                return (
                  <div key={it.key} style={{
                    display: "flex", justifyContent: isMe ? "flex-end" : "flex-start",
                    alignItems: "flex-start", gap: 10, padding: "4px 0",
                    width: "100%", minWidth: 0,
                  }}>
                    {/* 对方头像 */}
                    {!isMe && (
                      <div style={{
                        width: 36, height: 36, borderRadius: 8, background: "#e6f4ff",
                        display: "flex", alignItems: "center", justifyContent: "center",
                        color: "#1890ff", fontSize: 16, flexShrink: 0,
                      }}>
                        <UserOutlined />
                      </div>
                    )}
                    <div style={{
                      maxWidth: "70%", minWidth: 0,
                      display: "flex", flexDirection: "column",
                      alignItems: isMe ? "flex-end" : "flex-start",
                    }}>
                      {/* 气泡 */}
                      <div style={{
                        padding: "10px 14px", borderRadius: 10,
                        background: isMe ? "#e6f4ff" : "#fff",
                        color: "#262626", fontSize: 14, lineHeight: 1.6,
                        boxShadow: "0 1px 2px rgba(0,0,0,0.04)",
                        border: isMe ? "none" : "1px solid #f0f2f5",
                        whiteSpace: "pre-wrap",
                        overflowWrap: "break-word",
                        wordBreak: "break-word",
                      }}>
                        {m.content}
                      </div>
                      {/* RAG 引用依据 */}
                      {m.role === "assistant" && m.rag_hits && m.rag_hits.length > 0 && (
                        <div style={{ marginTop: 6, fontSize: 12, color: "#8c8c8c" }}>
                          <Space wrap size={[4, 4]}>
                            <Text type="secondary" style={{ fontSize: 11 }}>参考依据：</Text>
                            {m.rag_hits.map((hit: any, hi: number) => (
                              <Tag key={hi} color="geekblue" style={{ cursor: "pointer", fontSize: 11 }}
                                onClick={() => {
                                  Modal.info({
                                    title: `引用来源 #${hi + 1}`,
                                    width: 500,
                                    content: (
                                      <div style={{ lineHeight: 1.8 }}>
                                        <Descriptions size="small" column={1}>
                                          <Descriptions.Item label="文档">{hit.title || hit.source}</Descriptions.Item>
                                          {hit.page_no && <Descriptions.Item label="页码">第{hit.page_no}页</Descriptions.Item>}
                                          {hit.sheet && <Descriptions.Item label="工作表">{hit.sheet}</Descriptions.Item>}
                                          {hit.row && <Descriptions.Item label="行号">第{hit.row}行</Descriptions.Item>}
                                          {hit.heading_path && <Descriptions.Item label="章节">{hit.heading_path}</Descriptions.Item>}
                                          {hit.score && <Descriptions.Item label="相关度">{(hit.score * 100).toFixed(1)}%</Descriptions.Item>}
                                        </Descriptions>
                                        <Divider />
                                        <div style={{ background: "#fafafa", padding: 10, borderRadius: 6, fontSize: 13, whiteSpace: "pre-wrap", wordBreak: "break-word" }}>
                                          {hit.text}
                                        </div>
                                      </div>
                                    ),
                                  });
                                }}
                              >
                                {hit.title || hit.source || "未知"}
                                {hit.page_no ? ` · 第${hit.page_no}页` : ""}
                                {hit.sheet ? ` · ${hit.sheet}` : ""}
                                {hit.row ? ` · 第${hit.row}行` : ""}
                              </Tag>
                            ))}
                          </Space>
                        </div>
                      )}
                      {/* 时间戳 + 反馈按钮 */}
                      <div style={{
                        marginTop: 4, fontSize: 11, color: "#bfbfbf",
                        display: "flex", alignItems: "center", gap: 8,
                      }}>
                        <span>{m.created_at ? new Date(m.created_at.replace(" ", "T") + "Z").toLocaleTimeString() : ""}</span>
                        {m.role === "assistant" && m.agent_name && (
                          <Tag style={{ fontSize: 10, margin: 0, lineHeight: "16px", padding: "0 4px" }}>
                            {m.agent_name}
                          </Tag>
                        )}
                        {m.role === "assistant" && m.id && (
                          <Space size={0}>
                            <Button type="text" size="small" icon={<LikeOutlined style={{ fontSize: 12 }} />}
                              onClick={() => submitFeedback("good")} />
                            <Button type="text" size="small" danger icon={<DislikeOutlined style={{ fontSize: 12 }} />}
                              onClick={() => {
                                const lastUser = [...msgs].slice(0, i).reverse().find((x) => x.role === "user");
                                setFeedback({ open: true, msg: m, question: lastUser?.content, text: "" });
                              }} />
                          </Space>
                        )}
                      </div>
                    </div>
                    {/* 客服头像 */}
                    {isMe && (
                      <div style={{
                        width: 36, height: 36, borderRadius: 8, background: "#1890ff",
                        display: "flex", alignItems: "center", justifyContent: "center",
                        color: "#fff", fontSize: 16, flexShrink: 0,
                      }}>
                        <CustomerServiceOutlined />
                      </div>
                    )}
                  </div>
                );
              });
            })()}
          </div>

          {/* 底部输入条（flex 自然文档流，绝不滚动、永远可见） */}
          {active && (
            <div style={{
              background: "#fff", borderTop: "1px solid #e8ecef", padding: 12,
              flexShrink: 0, boxShadow: "0 -2px 8px rgba(0,21,41,0.04)",
            }}>
              {quickReply && (
                <div style={{ marginBottom: 8, display: "flex", flexWrap: "wrap", gap: 6 }}>
                  {quickReplies.map((q) => (
                    <Button key={q} size="small" onClick={() => setInput(q)}>{q}</Button>
                  ))}
                </div>
              )}
              <div style={{ display: "flex", gap: 8, alignItems: "flex-end" }}>
                <div style={{ flex: 1, position: "relative" }}>
                  <textarea
                    value={input}
                    onChange={(e) => setInput((e.target as HTMLTextAreaElement).value)}
                    placeholder="请输入回复内容... (Enter 发送 / Shift+Enter 换行)"
                    rows={2}
                    disabled={loading}
                    onKeyDown={(e) => {
                      if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); send(); }
                    }}
                    style={{
                      width: "100%", boxSizing: "border-box", padding: "8px 80px 8px 12px",
                      border: "1px solid #d9d9d9", borderRadius: 6, fontSize: 14,
                      lineHeight: 1.6, fontFamily: "inherit", resize: "none",
                      minHeight: 60, maxHeight: 160, outline: "none",
                      background: "#fff",
                    }}
                  />
                  <div style={{
                    position: "absolute", right: 8, bottom: 8, display: "flex", gap: 4,
                  }}>
                    <Tooltip title="快捷回复">
                      <Button type="text" size="small" icon={<ThunderboltOutlined />}
                        onClick={() => setQuickReply((x) => !x)} />
                    </Tooltip>
                    <Tooltip title="表情">
                      <Button type="text" size="small" icon={<SmileOutlined />} />
                    </Tooltip>
                    <Tooltip title="附件">
                      <Button type="text" size="small" icon={<PaperClipOutlined />} />
                    </Tooltip>
                  </div>
                </div>
                <Button type="primary" icon={<SendOutlined />} onClick={send} loading={loading}
                  style={{ height: 60, padding: "0 24px" }}>发送</Button>
              </div>
            </div>
          )}
        </div>
      </div>

      {/* ========== 右侧：访客名片 ========== */}
      <div style={{
        background: "#fff", borderLeft: "1px solid #e8ecef",
        display: "flex", flexDirection: "column", minWidth: 0, overflow: "hidden",
      }}>
        {active ? (
          <VisitorCard
            session={active}
            onUpdate={(patch) => setVisitors((vs) =>
              vs.map((v) => v.session_id === activeSid ? { ...v, ...patch } as Visitor : v)
            )}
          />
        ) : (
          <div style={{ padding: 24, color: "#bfbfbf", fontSize: 13, textAlign: "center" }}>
            请先选择访客
          </div>
        )}
      </div>

      {/* ===== 弹窗：差评反馈 ===== */}
      <Modal
        open={feedback.open}
        title="反馈详情"
        onCancel={() => setFeedback({ open: false, text: "" })}
        footer={[
          <Button key="good" type="primary" icon={<LikeOutlined />} onClick={() => submitFeedback("good")}>
            满意
          </Button>,
          <Button key="bad" danger icon={<DislikeOutlined />} onClick={() => submitFeedback("bad")}>
            不满意
          </Button>,
        ]}
      >
        <Input.TextArea value={feedback.text} onChange={(e) => setFeedback({ ...feedback, text: e.target.value })}
          placeholder="请说明问题（可选）" rows={4} />
      </Modal>

      {/* ===== 弹窗：二维码卡片（占位实现） ===== */}
      <Modal
        open={showQR}
        onCancel={() => setShowQR(false)}
        footer={null}
        width={360}
        centered
        title={null}
      >
        {active && (
          <div style={{ textAlign: "center", padding: "16px 0" }}>
            <div style={{ fontSize: 15, fontWeight: 600, marginBottom: 6 }}>
              移动端扫码加入会话
            </div>
            <div style={{ fontSize: 12, color: "#8c8c8c", marginBottom: 16 }}>
              会话 ID: {active.session_id.slice(0, 18)}…
            </div>
            <div style={{
              display: "inline-block", padding: 12, background: "#fff",
              border: "1px solid #f0f2f5", borderRadius: 8,
            }}>
              <img src={generateQRCodeSVG(active.session_id, 180)} alt="qr" style={{ display: "block" }} />
            </div>
            <div style={{ fontSize: 12, color: "#bfbfbf", marginTop: 12 }}>
              使用移动端扫码即可无缝接续对话
            </div>
          </div>
        )}
      </Modal>
    </div>
  );
}

/* ============ 访客名片（右侧栏） ============ */
function VisitorCard({ session, onUpdate }: { session: any; onUpdate: (p: any) => void }) {
  const [editingNote, setEditingNote] = useState(false);
  const [note, setNote] = useState(session.note || "");
  const [tag, setTag] = useState(session.tag || "");
  const [name, setName] = useState(session.title || "");
  const [editingName, setEditingName] = useState(false);

  const deviceIcon = (d: string) => {
    if (!d) return <DesktopOutlined />;
    if (/iPhone|iPad|Huawei|Xiaomi|Samsung|Mobile/i.test(d)) return <MobileOutlined />;
    if (/iPad|Tablet/i.test(d)) return <TabletOutlined />;
    return <DesktopOutlined />;
  };

  const row = (icon: React.ReactNode, label: string, value: React.ReactNode) => (
    <div style={{ display: "flex", alignItems: "flex-start", gap: 10, padding: "6px 0" }}>
      <span style={{ color: "#8c8c8c", fontSize: 13, marginTop: 2, flexShrink: 0 }}>{icon}</span>
      <div style={{ flex: 1, minWidth: 0, fontSize: 12, color: "#8c8c8c" }}>
        <div>{label}</div>
        <div style={{ color: "#262626", fontSize: 13, marginTop: 1, wordBreak: "break-all" }}>{value}</div>
      </div>
    </div>
  );

  return (
    <div style={{ display: "flex", flexDirection: "column", height: "100%" }}>
      {/* 头部：头像 + 名称 */}
      <div style={{
        padding: "20px 16px 16px", borderBottom: "1px solid #f0f2f5",
        background: "linear-gradient(180deg, #f0f7ff 0%, #fff 100%)",
      }}>
        <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
          <Avatar size={48} style={{ background: "#1890ff", fontSize: 20 }}>
            {(session.title || session.visitor_ip || "U").substring(0, 1).toUpperCase()}
          </Avatar>
          <div style={{ flex: 1, minWidth: 0 }}>
            {editingName ? (
              <Input
                size="small" value={name} autoFocus
                onChange={(e) => setName(e.target.value)}
                onBlur={() => { setEditingName(false); onUpdate({ title: name }); }}
                onPressEnter={() => { setEditingName(false); onUpdate({ title: name }); }}
                style={{ fontWeight: 600 }}
              />
            ) : (
              <div
                onClick={() => { setName(session.title || ""); setEditingName(true); }}
                style={{ fontSize: 15, fontWeight: 600, color: "#262626", cursor: "text" }}
              >
                {session.title || "未命名访客"}
                <EditOutlined style={{ marginLeft: 6, fontSize: 11, color: "#bfbfbf" }} />
              </div>
            )}
            <div style={{ fontSize: 12, color: "#8c8c8c", marginTop: 2 }}>
              #{session.session_id?.slice(-6) || "000000"}
            </div>
          </div>
        </div>
      </div>

      {/* 信息区（可滚动） */}
      <div style={{ flex: 1, overflow: "auto", padding: "8px 16px" }}>
        <Section title="设备信息">
          {row(<MobileOutlined />, "设备", session.device || "未知")}
          {row(<DesktopOutlined />, "操作系统", session.os_name || "未知")}
          {row(<GlobalIcon />, "浏览器", session.browser || "未知")}
          {row(<TranslationOutlined />, "语言", session.language || "zh-CN")}
        </Section>

        <Section title="访问信息">
          {row(<EnvironmentOutlined />, "所在地", `${session.visitor_region || "未知"} · ${session.visitor_ip || "无 IP"}`)}
          {row(<LinkOutlined />, "来源", session.referrer || "直接访问")}
          {row(<HistoryOutlined />, "访问次数", `${session.visit_count || 1} 次`)}
          {row(<ClockCircleOutlined />, "最近活跃", relativeTime(session.last_active_at))}
          {row(<ClockCircleOutlined />, "首次接入", session.created_at ? new Date(session.created_at.replace(" ", "T") + "Z").toLocaleString() : "-")}
        </Section>

        <Section title="咨询摘要">
          <div style={{
            padding: "8px 10px", background: "#fafbfc", borderRadius: 4,
            fontSize: 13, color: "#262626", lineHeight: 1.5,
          }}>
            {session.intent_summary || "尚未识别意图"}
          </div>
          {session.last_message_preview && (
            <div style={{ fontSize: 12, color: "#8c8c8c", marginTop: 6, fontStyle: "italic" }}>
              最新消息：{session.last_message_preview}
            </div>
          )}
        </Section>

        <Section title="标签">
          <div style={{ display: "flex", gap: 6 }}>
            <Input
              size="small" value={tag}
              placeholder="输入标签后回车或点击保存"
              onChange={(e) => setTag(e.target.value)}
              onPressEnter={() => {
                if (tag.trim()) {
                  onUpdate({ tag: tag.trim() });
                  setTag("");
                  message.success("标签已保存");
                }
              }}
              prefix={<TagOutlined />}
            />
            <Button
              size="small" type="primary"
              disabled={!tag.trim()}
              onClick={() => {
                if (tag.trim()) {
                  onUpdate({ tag: tag.trim() });
                  setTag("");
                  message.success("标签已保存");
                }
              }}
            >
              保存
            </Button>
          </div>
          <div style={{ display: "flex", flexWrap: "wrap", gap: 4, marginTop: 6 }}>
            {(session.tag ? [session.tag] : ["新访客", "高意向"]).map((t) => (
              <Tag
                key={t}
                color="blue"
                closable={!!session.tag}
                onClose={() => onUpdate({ tag: "" })}
                style={{ fontSize: 11 }}
              >
                {t}
              </Tag>
            ))}
          </div>
        </Section>
      </div>

      {/* 底部：备注 */}
      <div style={{ borderTop: "1px solid #f0f2f5", padding: "12px 16px" }}>
        <div style={{ fontSize: 12, color: "#8c8c8c", marginBottom: 4, display: "flex",
                      alignItems: "center", gap: 4 }}>
          <EditOutlined /> 备注
        </div>
        {editingNote ? (
          <Input.TextArea
            value={note} autoFocus
            onChange={(e) => setNote(e.target.value)}
            onBlur={() => { setEditingNote(false); onUpdate({ note }); }}
            rows={3} placeholder="为这个访客添加备注..."
            style={{ fontSize: 12 }}
          />
        ) : (
          <div
            onClick={() => { setNote(session.note || ""); setEditingNote(true); }}
            style={{
              padding: "6px 8px", fontSize: 12, color: session.note ? "#262626" : "#bfbfbf",
              background: "#fafbfc", borderRadius: 4, minHeight: 32, cursor: "text",
            }}
          >
            {session.note || "点击添加备注..."}
          </div>
        )}
      </div>
    </div>
  );
}

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div style={{ marginBottom: 16 }}>
      <div style={{
        fontSize: 11, color: "#8c8c8c", fontWeight: 600, letterSpacing: 0.5,
        textTransform: "uppercase", padding: "8px 0 4px",
        borderBottom: "1px solid #f0f2f5", marginBottom: 4,
      }}>{title}</div>
      {children}
    </div>
  );
}

function VisitorItem({ v, active, onClick }: { v: Visitor; active: boolean; onClick: () => void }) {
  const online = isOnline(v);
  return (
    <div onClick={onClick} style={{
      padding: "12px 16px", cursor: "pointer",
      background: active ? "#e6f4ff" : "transparent",
      borderLeft: active ? "3px solid #1890ff" : "3px solid transparent",
      transition: "all .15s",
      borderBottom: "1px solid #f7f8fa",
    }}>
      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
        <div style={{ display: "flex", alignItems: "center", gap: 8, minWidth: 0 }}>
          <span style={{
            width: 8, height: 8, borderRadius: "50%",
            background: online ? "#52c41a" : "#d9d9d9",
            boxShadow: online ? "0 0 0 3px rgba(82,196,26,0.15)" : "none",
            flexShrink: 0,
          }} />
          <span style={{
            fontSize: 13, color: "#262626", fontWeight: 500,
            overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap",
          }}>
            {regionFlag(v.visitor_region)} {shortIp(v.visitor_ip)}
          </span>
        </div>
        <span style={{ fontSize: 11, color: "#bfbfbf", flexShrink: 0 }}>{relativeTime(v.last_active_at)}</span>
      </div>
      <div style={{
        marginTop: 4, fontSize: 12, color: "#8c8c8c",
        overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap",
      }}>
        {v.last_message_preview || v.intent_summary || v.title || "等待访客发言…"}
      </div>
      <div style={{ marginTop: 2, display: "flex", alignItems: "center", gap: 6 }}>
        {v.intent_summary && (
          <Tag color="blue" style={{ fontSize: 10, margin: 0, lineHeight: "14px", padding: "0 4px" }}>
            {v.intent_summary}
          </Tag>
        )}
        <span style={{ fontSize: 11, color: "#bfbfbf" }}>{v.message_count || 0} 条</span>
      </div>
    </div>
  );
}

function StatCard({ label, value }: { label: string; value: any }) {
  return (
    <div style={{
      padding: "8px 12px", background: "#fafbfc", borderRadius: 6,
      border: "1px solid #f0f2f5",
    }}>
      <div style={{ fontSize: 11, color: "#8c8c8c" }}>{label}</div>
      <div style={{ fontSize: 14, color: "#262626", fontWeight: 600, marginTop: 2 }}>
        {value}
      </div>
    </div>
  );
}
