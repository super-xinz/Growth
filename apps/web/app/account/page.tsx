import XiaohongshuLogin from "./XiaohongshuLogin";
import ModelSettings from "./ModelSettings";
import {cookies} from "next/headers";
import {getAdminSession, getHealth} from "@/lib/api";

export default async function AccountPage(){
  const cookieHeader=(await cookies()).getAll()
    .map(({name,value})=>`${name}=${value}`)
    .join("; ");
  const [health,adminSession]=await Promise.all([
    getHealth(),
    getAdminSession(cookieHeader),
  ]);
  const publicDemo=Boolean(health.public_demo)&&!adminSession.authenticated;
  return <><header className="page-header account-header"><div><div className="eyebrow">{publicDemo?"本机使用":"只需最后一步"}</div><h1>{publicDemo?"下载后连接小红书":"连接小红书账号"}</h1><p>{publicDemo?"公开网页不读取账号 Cookie；安装版已自动配置模型，只需本人扫码。":"模型、密钥和运行参数均已自动配置；使用者本人扫码后即可运行。"}</p></div></header><div className="settings-stack"><XiaohongshuLogin initialStatus={null} publicDemo={publicDemo}/><ModelSettings/></div></>;
}
