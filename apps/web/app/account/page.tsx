import XiaohongshuLogin from "./XiaohongshuLogin";
import ModelSettings from "./ModelSettings";

export default function AccountPage(){
  return <><header className="page-header account-header"><div><div className="eyebrow">SETTINGS</div><h1>连接与模型</h1><p>配置模型服务，并管理本机的小红书登录状态。</p></div></header><div className="settings-stack"><ModelSettings/><XiaohongshuLogin initialStatus={null}/></div></>;
}
