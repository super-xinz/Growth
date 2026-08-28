"use client";

import Image from "next/image";
import {useCallback, useEffect, useState} from "react";
import {ScanLine} from "lucide-react";
import {API, responseDetail} from "@/lib/api";

type Status={is_logged_in?:boolean;username?:string};
type Qrcode={img?:string;timeout?:string;is_logged_in?:boolean};

export default function XiaohongshuLogin({initialStatus}:{initialStatus:Status|null}){
  const [status,setStatus]=useState(initialStatus);
  const [qr,setQr]=useState<Qrcode|null>(null);
  const [busy,setBusy]=useState(false);
  const [checking,setChecking]=useState(initialStatus===null);
  const [error,setError]=useState("");

  const request=useCallback(async(path:string,method="GET",signal?:AbortSignal)=>{
    const response=await fetch(`${API}${path}`,{method,signal});
    if(!response.ok)throw new Error(await responseDetail(response));
    return response.json();
  },[]);
  const refreshStatus=useCallback(async()=>{
    const controller=new AbortController();
    const timer=window.setTimeout(()=>controller.abort(),5000);
    setChecking(true);
    try{const next=await request("/v1/xiaohongshu/status","GET",controller.signal);setStatus(next);setError("");return Boolean(next.is_logged_in)}
    catch(reason){
      if(controller.signal.aborted)setError("登录状态检查较慢，请稍后重试。");
      else setError(reason instanceof Error?reason.message:"无法连接小红书服务");
      return false;
    }
    finally{window.clearTimeout(timer);setChecking(false)}
  },[request]);
  async function showQr(){
    setBusy(true);setError("");
    try{setQr(await request("/v1/xiaohongshu/login/qrcode"))}
    catch(reason){setError(reason instanceof Error?reason.message:"二维码获取失败")}
    finally{setBusy(false)}
  }
  async function logout(){
    if(!window.confirm("确定清除当前小红书登录状态吗？"))return;
    setBusy(true);
    try{await request("/v1/xiaohongshu/login","DELETE");setStatus({is_logged_in:false});setQr(null)}
    catch(reason){setError(reason instanceof Error?reason.message:"退出失败")}
    finally{setBusy(false)}
  }
  useEffect(()=>{
    if(status?.is_logged_in||!qr)return;
    let stopped=false;
    let timer=0;
    const poll=async()=>{
      if(await refreshStatus())setQr(null);
      else if(!stopped)timer=window.setTimeout(poll,3000);
    };
    timer=window.setTimeout(poll,3000);
    return()=>{stopped=true;window.clearTimeout(timer)};
  },[qr,status?.is_logged_in,refreshStatus]);
  useEffect(()=>{
    if(initialStatus!==null)return;
    void refreshStatus();
  },[initialStatus,refreshStatus]);

  const statusTitle=checking?"正在检查连接":status?.is_logged_in?"已连接小红书":status===null?"连接状态未知":"尚未登录";
  const statusCopy=checking?"页面已就绪，正在后台确认小红书登录状态。":status?.is_logged_in?(status.username||"自动搜索与低频评论已可用"):status===null?"状态服务响应较慢，可以重新检查。":"使用小红书 App 扫码登录，不需要 API Key。";

  return <section className="card account-card">
    <div className="settings-card-heading compact">
      <span className="settings-card-icon"><ScanLine size={18}/></span>
      <div><div className="eyebrow">ACCOUNT</div><h2>小红书账号</h2><p>扫码完成本机登录，Cookie 仅保存在本地数据卷。</p></div>
    </div>
    <div className="account-status"><span className={`account-dot ${status?.is_logged_in?"online":""}`}/><div><strong>{statusTitle}</strong><p>{statusCopy}</p></div></div>
    {error&&<div className="inline-error" role="alert">{error}</div>}
    {qr?.img&&<div className="qr-panel"><Image src={qr.img} alt="小红书登录二维码" width={220} height={220} unoptimized/><p>请使用小红书 App 扫码。二维码约 {qr.timeout||"300"} 秒后过期。</p></div>}
    <div className="actions">{checking?<button className="button secondary" disabled>正在检查…</button>:status?.is_logged_in?<button className="button secondary" disabled={busy} onClick={logout}>退出当前账号</button>:status===null?<button className="button secondary" disabled={busy} onClick={()=>void refreshStatus()}>重新检查</button>:<button className="button" disabled={busy} onClick={showQr}>{qr?"刷新二维码":"显示登录二维码"}</button>}</div>
  </section>;
}
