"use client";

import Link from "next/link";
import {useState} from "react";
import {useRouter} from "next/navigation";
import {API,responseDetail} from "@/lib/api";

export default function NewProduct(){
  const router=useRouter();
  const [busy,setBusy]=useState(false);
  const [error,setError]=useState("");
  const [step,setStep]=useState("");
  const [createdId,setCreatedId]=useState<string|null>(null);

  async function submit(e:React.FormEvent<HTMLFormElement>){
    e.preventDefault();
    const data=new FormData(e.currentTarget);
    const website=String(data.get("website_url")||"").trim();
    const github=String(data.get("github_url")||"").trim();
    if(!website&&!github){setError("请至少填写产品网站或 GitHub 仓库地址。");return}
    setBusy(true);setError("");setCreatedId(null);
    const payload={name:data.get("name"),website_url:website||null,github_url:github||null,daily_reply_limit:2};
    try{
      setStep("正在创建产品…");
      const createResponse=await fetch(`${API}/v1/products`,{method:"POST",headers:{"content-type":"application/json"},body:JSON.stringify(payload)});
      if(!createResponse.ok)throw new Error(`创建产品失败：${await responseDetail(createResponse)}`);
      const product=await createResponse.json();setCreatedId(product.id);
      setStep("正在读取公开资料…");
      const ingest=await fetch(`${API}/v1/products/${product.id}/ingest`,{method:"POST"});
      if(!ingest.ok)throw new Error(`抓取资料失败：${await responseDetail(ingest)}`);
      setStep("正在构建带证据的 Product Brain…");
      const brain=await fetch(`${API}/v1/products/${product.id}/build-brain`,{method:"POST"});
      if(!brain.ok)throw new Error(`产品分析失败：${await responseDetail(brain)}`);
      setStep("分析完成，正在打开产品…");
      router.push(`/products/${product.id}`);router.refresh();
    }catch(reason){setError(reason instanceof Error?reason.message:"无法创建产品");setBusy(false);setStep("")}
  }

  return <>
    <header className="page-header create-header"><div><div className="eyebrow">NEW PRODUCT</div><h1>添加产品</h1><p>一个公开地址，就能开始增长。</p></div></header>
    <form className="card form-card" onSubmit={submit}>
      <label>产品名称<input name="name" required disabled={busy} placeholder="例如：GrowthAgent"/></label>
      <label>产品网站<input name="website_url" type="url" disabled={busy} placeholder="https://example.com"/></label>
      <div className="field-hint">产品网站和 GitHub 仓库至少填写一个。</div>
      <label>GitHub 仓库地址<input name="github_url" type="url" disabled={busy} placeholder="https://github.com/org/repo"/></label>
      {step&&<p className="inline-notice" role="status"><span className="spinner small"/>{step}</p>}
      {error&&<div className="inline-error" role="alert">{error}{createdId&&<> <Link href={`/products/${createdId}`}>打开已创建的草稿继续处理</Link></>}</div>}
      <button className="button" disabled={busy}>{busy?"正在处理，请勿关闭页面…":"创建并分析"}</button>
    </form>
  </>;
}
