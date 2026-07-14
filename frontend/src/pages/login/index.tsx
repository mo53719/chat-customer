import { useState } from "react";
import { Card, Form, Input, Button, Tabs, message } from "antd";
import { useSearchParams } from "react-router-dom";
import { useAuthStore } from "../../stores";
import { authApi } from "../../api";

export default function LoginPage() {
  const setAuth = useAuthStore((s) => s.setAuth);
  const [searchParams] = useSearchParams();
  const redirect = searchParams.get("redirect") || "/chat";
  const [loginForm] = Form.useForm();
  const [regForm] = Form.useForm();
  const [loading, setLoading] = useState(false);

  const onLogin = async (vals: any) => {
    setLoading(true);
    try {
      const r: any = await authApi.login(vals.username, vals.password);
      localStorage.setItem("token", r.data.access_token);
      setAuth(r.data.access_token, r.data.username, r.data.role, r.data.user_id);
      window.location.href = redirect;
    } catch (e: any) {
      message.error(e.message);
    } finally {
      setLoading(false);
    }
  };

  const onRegister = async (vals: any) => {
    setLoading(true);
    try {
      const r: any = await authApi.register(vals.username, vals.password, vals.nickname);
      localStorage.setItem("token", r.data.access_token);
      setAuth(r.data.access_token, r.data.username, r.data.role, r.data.user_id);
      window.location.href = redirect;
    } catch (e: any) {
      message.error(e.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div style={{ display: "flex", justifyContent: "center", paddingTop: 80 }}>
      <Card style={{ width: 420 }} title="智能客服系统">
        <Tabs
          items={[
            {
              key: "login",
              label: "登录",
              children: (
                <Form form={loginForm} onFinish={onLogin} layout="vertical">
                  <Form.Item name="username" label="用户名" rules={[{ required: true }]}>
                    <Input />
                  </Form.Item>
                  <Form.Item name="password" label="密码" rules={[{ required: true }]}>
                    <Input.Password />
                  </Form.Item>
                  <Button type="primary" htmlType="submit" block loading={loading}>
                    登录
                  </Button>
                </Form>
              ),
            },
            {
              key: "register",
              label: "注册",
              children: (
                <Form form={regForm} onFinish={onRegister} layout="vertical">
                  <Form.Item name="username" label="用户名" rules={[{ required: true }]}>
                    <Input />
                  </Form.Item>
                  <Form.Item name="password" label="密码" rules={[{ required: true }]}>
                    <Input.Password />
                  </Form.Item>
                  <Form.Item name="nickname" label="昵称">
                    <Input />
                  </Form.Item>
                  <Button type="primary" htmlType="submit" block loading={loading}>
                    注册
                  </Button>
                </Form>
              ),
            },
          ]}
        />
      </Card>
    </div>
  );
}
