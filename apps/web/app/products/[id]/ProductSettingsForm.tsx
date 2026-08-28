"use client";

import {useState} from "react";
import {useRouter} from "next/navigation";
import {API,responseDetail} from "@/lib/api";

type ProductSettings={id:string;name:string;website_url:string|null;github_url:string|null;daily_reply_limit:number;disclosure_template:string;is_owned:boolean};

export default function ProductSettingsForm({product}:{product:ProductSettings}){
  const router=useRouter();
  const [busy,setBusy]=useState(false);
  const [message,setMessage]=useState("");
  const [failed,setFailed]=useState(false);
  const [owned,setOwned]=useState(product.is_owned);
  async function save(e:React.FormEvent<HTMLFormElement>){
    e.preventDefault();const data=new FormData(e.currentTarget);
    const website=String(data.get("website_url")||"").trim();const github=String(data.get("github_url")||"").trim();
    if(!website&&!github){setFailed(true);setMessage("请至少保留产品网站或 GitHub 仓库地址。");return}
    const disclosure=String(data.get("disclosure_template")||"").trim();
    if(owned&&!disclosure){setFailed(true);setMessage("自有产品需要填写真实的关系披露，例如“自家做的”。");return}
    setBusy(true);setFailed(false);setMessage("正在保存…");
    const payload={name:data.get("name"),website_url:website||null,github_url:github||null,daily_reply_limit:Number(data.get("daily_reply_limit")),disclosure_template:disclosure,is_owned:owned};
    try{
      const response=await fetch(`${API}/v1/products/${product.id}`,{method:"PATCH",headers:{"content-type":"application/json"},body:JSON.stringify(payload)});
      if(!response.ok)throw new Error(await responseDetail(response));
      setMessage("产品设置已保存。需要时请重新分析，以更新 Product Brain。");router.refresh();
    }catch(error){setFailed(true);setMessage(error instanceof Error?error.message:"保存失败")}
    finally{setBusy(false)}
  }
  return <form onSubmit={save} className="settings-form">
    <label>产品名称<input name="name" required disabled={busy} defaultValue={product.name}/></label>
    <label>产品网站<input name="website_url" type="url" disabled={busy} defaultValue={product.website_url||""}/></label>
    <label>GitHub 仓库<input name="github_url" type="url" disabled={busy} defaultValue={product.github_url||""}/></label>
    <label>每日回复上限<input name="daily_reply_limit" type="number" min={1} max={2} disabled={busy} defaultValue={Math.min(product.daily_reply_limit,2)}/></label>
    <label className="ownership-option"><input name="is_owned" type="checkbox" checked={owned} onChange={event=>setOwned(event.target.checked)} disabled={busy}/><span><strong>这是我方产品</strong><small>允许草稿在确实相关时自然提及产品，并明确披露关系。</small></span></label>
    <label>关系披露短语<input name="disclosure_template" maxLength={50} required={owned} disabled={busy} defaultValue={product.disclosure_template} placeholder="例如：自家做的"/></label>
    {message&&<p className={failed?"feedback-error":"feedback-message"} role={failed?"alert":"status"}>{message}</p>}
    <button className="button secondary" disabled={busy}>{busy?"正在保存…":"保存产品设置"}</button>
  </form>;
}
