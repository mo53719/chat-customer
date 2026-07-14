import { Typography } from "antd";

const { Title } = Typography;

interface PageContainerProps {
  title: string;
  children: React.ReactNode;
}

export default function PageContainer({ title, children }: PageContainerProps) {
  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
      <Title level={4} style={{ margin: 0 }}>{title}</Title>
      {children}
    </div>
  );
}