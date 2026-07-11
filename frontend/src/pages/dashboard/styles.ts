/** 数据看板设计 token：圆角 / 阴影 / 字号 / 字体栈。 */

export const RADIUS = 8;
export const SHADOW = "0 1px 3px rgba(0,0,0,0.1)";

export const FONT_STACK =
  '"Inter", "PingFang SC", "Microsoft YaHei", "Source Han Sans CN", -apple-system, BlinkMacSystemFont, "Helvetica Neue", sans-serif';

export const COLOR_TITLE = "#8c8c8c";
export const COLOR_VALUE = "#262626";
export const COLOR_NORMAL = "#1890ff";
export const COLOR_WARN = "#ff4d4f";
export const COLOR_WARN_BG = "#fff1f0";
export const COLOR_TITLE_BG = "#fafafa";

export const cardBase = {
  background: "#fff",
  borderRadius: RADIUS,
  boxShadow: SHADOW,
  border: "none",
};

export const cardAlert = {
  ...cardBase,
  background: COLOR_WARN_BG,
};

export const titleStyle = {
  fontSize: 13,
  color: COLOR_TITLE,
  fontWeight: 400,
  margin: 0,
};

export const valueStyle = {
  fontSize: 28,
  color: COLOR_VALUE,
  fontWeight: 600,
  lineHeight: 1.2,
  marginTop: 8,
};

export const moduleHeaderStyle = {
  padding: "12px 16px",
  background: COLOR_TITLE_BG,
  borderBottom: "1px solid #f0f0f0",
  fontSize: 15,
  fontWeight: 600,
  color: COLOR_VALUE,
  borderTopLeftRadius: RADIUS,
  borderTopRightRadius: RADIUS,
};
