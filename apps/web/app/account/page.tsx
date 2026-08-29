import XiaohongshuLogin from "./XiaohongshuLogin";
import ModelSettings from "./ModelSettings";
import {getHealth} from "@/lib/api";

export default async function AccountPage(){
  const health=await getHealth();
  return <><header className="page-header account-header"><div><div className="eyebrow">SETTINGS</div><h1>模型与小红书</h1><p>模型服务开箱即用；小红书账号由使用者本人扫码登录。</p></div></header><div className="settings-stack"><ModelSettings/><XiaohongshuLogin initialStatus={null} publicDemo={Boolean(health.public_demo)}/></div></>;
}
