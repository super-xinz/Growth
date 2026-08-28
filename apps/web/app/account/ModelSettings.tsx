"use client";

import {useEffect, useState} from "react";
import {KeyRound, PlugZap} from "lucide-react";
import {API, responseDetail} from "@/lib/api";

type LLMSettings = {
  provider: "mock" | "openai";
  base_url: string;
  model: string;
  enable_thinking: boolean;
  api_key_configured: boolean;
  api_key_hint?: string | null;
};

export default function ModelSettings(){
  const [provider,setProvider]=useState<LLMSettings["provider"]>("openai");
  const [baseUrl,setBaseUrl]=useState("https://api.openai.com/v1");
  const [model,setModel]=useState("");
  const [apiKey,setApiKey]=useState("");
  const [enableThinking,setEnableThinking]=useState(false);
  const [keyHint,setKeyHint]=useState<string|null>(null);
  const [loading,setLoading]=useState(true);
  const [busy,setBusy]=useState(false);
  const [message,setMessage]=useState("");
  const [failed,setFailed]=useState(false);

  async function request(path:string,init?:RequestInit){
    const response=await fetch(`${API}${path}`,init);
    if(!response.ok)throw new Error(await responseDetail(response));
    return response.json();
  }

  function applySettings(settings:LLMSettings){
    setProvider(settings.provider);
    setBaseUrl(settings.base_url);
    setModel(settings.model);
    setEnableThinking(settings.enable_thinking);
    setKeyHint(settings.api_key_hint||null);
    setApiKey("");
  }

  useEffect(()=>{
    let active=true;
    request("/v1/settings/llm")
      .then(settings=>{if(active)applySettings(settings)})
      .catch(reason=>{if(active){setFailed(true);setMessage(reason instanceof Error?reason.message:"无法读取模型配置")}})
      .finally(()=>{if(active)setLoading(false)});
    return()=>{active=false};
  },[]);

  async function save(event:React.FormEvent){
    event.preventDefault();setBusy(true);setFailed(false);setMessage("");
    try{
      const settings=await request("/v1/settings/llm",{
        method:"PUT",
        headers:{"Content-Type":"application/json"},
        body:JSON.stringify({
          provider,
          api_key:apiKey||null,
          base_url:baseUrl,
          model,
          enable_thinking:enableThinking,
        }),
      });
      applySettings(settings);setMessage("模型配置已加密保存。");
    }catch(reason){setFailed(true);setMessage(reason instanceof Error?reason.message:"保存失败")}
    finally{setBusy(false)}
  }

  async function testConnection(){
    setBusy(true);setFailed(false);setMessage("");
    try{
      const settings=await request("/v1/settings/llm",{
        method:"PUT",
        headers:{"Content-Type":"application/json"},
        body:JSON.stringify({provider,api_key:apiKey||null,base_url:baseUrl,model,enable_thinking:enableThinking}),
      });
      applySettings(settings);
      const result=await request("/v1/settings/llm/test",{method:"POST"});
      setMessage(result.message||"连接成功。");
    }
    catch(reason){setFailed(true);setMessage(reason instanceof Error?reason.message:"连接失败")}
    finally{setBusy(false)}
  }

  return <section className="card model-settings-card">
    <div className="settings-card-heading">
      <span className="settings-card-icon"><KeyRound size={18}/></span>
      <div><div className="eyebrow">MODEL</div><h2>模型服务</h2><p>密钥由本机后端加密保存，不会进入前端构建或返回浏览器。</p></div>
    </div>
    {loading?<div className="settings-loading"><span className="spinner small"/>正在读取配置…</div>:<form className="settings-form" onSubmit={save}>
      <label>服务类型
        <select value={provider} onChange={event=>setProvider(event.target.value as LLMSettings["provider"])}>
          <option value="openai">OpenAI 兼容接口</option>
          <option value="mock">Mock（本地演示，不调用模型）</option>
        </select>
      </label>
      <label>API Base URL<input type="url" required value={baseUrl} onChange={event=>setBaseUrl(event.target.value)} placeholder="https://api.openai.com/v1" spellCheck={false}/></label>
      <label>模型名称<input required={provider!=="mock"} value={model} onChange={event=>setModel(event.target.value)} placeholder="例如：gpt-4.1-mini" spellCheck={false}/></label>
      <label>API Key
        <input type="password" value={apiKey} onChange={event=>setApiKey(event.target.value)} placeholder={keyHint?`已保存 ${keyHint}；留空则不修改`:"输入 API Key"} autoComplete="new-password" spellCheck={false}/>
      </label>
      <label className="ownership-option model-thinking"><input type="checkbox" checked={enableThinking} onChange={event=>setEnableThinking(event.target.checked)}/><span>启用兼容接口的思考模式<small>仅对支持该参数的服务生效。</small></span></label>
      {message&&<div className={failed?"feedback-error":"feedback-message"} role={failed?"alert":"status"}>{message}</div>}
      <div className="actions"><button className="button" disabled={busy}>{busy?"正在保存…":"保存配置"}</button><button className="button secondary" type="button" disabled={busy||loading} onClick={testConnection}><PlugZap size={16}/>保存并测试</button></div>
    </form>}
  </section>;
}
