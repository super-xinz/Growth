"use client";

import {useState} from "react";
import {useRouter} from "next/navigation";
import {Clock3, Pause, Play, ShieldCheck} from "lucide-react";
import {API,responseDetail} from "@/lib/api";

type Product={
  id:string;autopublish_enabled:boolean;automation_status:string;automation_error?:string|null;
  auto_score_threshold:number;auto_risk_threshold:number;search_interval_hours:number;
  min_publish_interval_hours:number;daily_reply_limit:number;next_auto_search_at?:string|null;
};

function conciseError(message: string) {
  const plain = message.split(/error value:|goroutine\s+\d+|runtime\/debug/i)[0].trim();
  return plain.length > 160 ? `${plain.slice(0, 157)}…` : plain;
}

export default function ProductModeControls({product}:{product:Product}){
  const router=useRouter();
  const [busy,setBusy]=useState(false);
  const [message,setMessage]=useState("");
  const [failed,setFailed]=useState(false);

  async function request(path:string,method="POST"){
    const response=await fetch(`${API}${path}`,{method});
    if(!response.ok)throw new Error(await responseDetail(response));
    return response.json();
  }

  async function runNow(){
    setBusy(true);setFailed(false);setMessage("正在选择需求词并搜索，本轮最多触达 1 人…");
    try{
      await request(`/v1/products/${product.id}/xiaohongshu/auto-search`);
      setMessage("本轮已完成，正在打开发现结果。");
      router.push(`/products/${product.id}/opportunities`);router.refresh();
    }catch(error){setFailed(true);setMessage(error instanceof Error?error.message:"运行失败");}
    finally{setBusy(false);}
  }

  async function toggle(){
    setBusy(true);setFailed(false);setMessage("");
    try{
      await request(`/v1/products/${product.id}/autopublish/${product.autopublish_enabled?"disable":"enable"}`);
      router.refresh();
    }catch(error){setFailed(true);setMessage(error instanceof Error?error.message:"更新失败");}
    finally{setBusy(false);}
  }

  const nextRun=product.next_auto_search_at?new Date(product.next_auto_search_at).toLocaleString("zh-CN",{month:"numeric",day:"numeric",hour:"2-digit",minute:"2-digit",timeZone:"Asia/Shanghai"}):"即将开始";

  return <section className="automation-panel">
    <div className="automation-main">
      <div className="automation-title-row">
        <div><div className="eyebrow">自动化</div><h2>需求发现与低频触达</h2></div>
        <span className={`status ${product.autopublish_enabled?"":"muted"}`}><i className="status-dot"/>{product.autopublish_enabled?"运行中":"已暂停"}</span>
      </div>
      <div className="next-run">
        <Clock3 size={18}/>
        <div><span>下一次运行</span><strong>{product.autopublish_enabled?nextRun:"不会自动运行"}</strong></div>
      </div>
      {product.automation_error&&<div className="compact-alert">{conciseError(product.automation_error)}</div>}
      {message&&<div className={failed?"feedback-error":"feedback-message"} role={failed?"alert":"status"}>{message}</div>}
      <div className="actions"><button className="button" disabled={busy||!product.autopublish_enabled} onClick={runNow}><Play size={16}/>{busy?"运行中…":"立即运行"}</button><button className="button ghost" disabled={busy} onClick={toggle}>{product.autopublish_enabled?<><Pause size={16}/>暂停</>:<><Play size={16}/>重新开启</>}</button></div>
    </div>
    <div className="guardrails">
      <div className="guardrail-heading"><ShieldCheck size={17}/><span>安全规则</span></div>
      <div><span>机会门槛</span><strong>≥ {Math.round(product.auto_score_threshold*100)}</strong></div>
      <div><span>风险上限</span><strong>≤ {Math.round(product.auto_risk_threshold*100)}</strong></div>
      <div><span>搜索间隔</span><strong>{product.search_interval_hours} 小时</strong></div>
      <div><span>触达冷却</span><strong>{product.min_publish_interval_hours} 小时</strong></div>
      <div><span>每日上限</span><strong>{product.daily_reply_limit} 条</strong></div>
    </div>
  </section>;
}
