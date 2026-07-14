import { useNavigate, useSearchParams } from "react-router-dom";

export type PagePath =
  | "/chat" | "/dashboard" | "/prompts" | "/feedback"
  | "/ops" | "/recycle" | "/business"
  | "/team/llm" | "/team/rag" | "/team/config" | "/team/wechat"
  | "/team/douyin" | "/team/channels" | "/team/agents"
  | "/team/visitors" | "/team/service-stats"
  | "/mall/merchant" | "/mall/products" | "/mall/orders"
  | "/personal/profile" | "/system/general" | "/system/badcase";

export const useNav = () => {
  const navigate = useNavigate();
  return {
    go: (path: PagePath, params?: Record<string, string | number>) => {
      const search = params
        ? "?" + new URLSearchParams(
            Object.entries(params).map(([k, v]) => [k, String(v)])
          ).toString()
        : "";
      navigate(path + search);
    },
    back: () => navigate(-1),
  };
};

export const useQueryParams = <T extends Record<string, string>>(): Partial<T> => {
  const [searchParams] = useSearchParams();
  const result: any = {};
  searchParams.forEach((v, k) => { result[k] = v; });
  return result;
};