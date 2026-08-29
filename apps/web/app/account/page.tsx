import XiaohongshuLogin from "./XiaohongshuLogin";
import ModelSettings from "./ModelSettings";
import {getHealth} from "@/lib/api";

export default async function AccountPage(){
  const health=await getHealth();
  const publicDemo=Boolean(health.public_demo);
  return <><header className="page-header account-header"><div><div className="eyebrow">{publicDemo?"本机使用":"只需最后一步"}</div><h1>{publicDemo?"下载后连接小红书":"连接小红书账号"}</h1><p>{publicDemo?"公开网页不读取账号 Cookie；安装版已自动配置模型，只需本人扫码。":"模型、密钥和运行参数均已自动配置；使用者本人扫码后即可运行。"}</p></div></header><div className="settings-stack"><XiaohongshuLogin initialStatus={null} publicDemo={publicDemo}/><ModelSettings/></div></>;
}
