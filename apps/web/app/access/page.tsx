"use client";

import {useCallback, useEffect, useRef, useState} from "react";
import {API, responseDetail} from "@/lib/api";

type AccessState="waiting"|"authorizing"|"failed";

export default function AccessPage(){
  const [state,setState]=useState<AccessState>("authorizing");
  const [message,setMessage]=useState("正在建立此浏览器的私有运营会话…");
  const credentialRef=useRef<HTMLInputElement>(null);

  const authorize=useCallback(async(credential:string)=>{
    let token=credential.trim();
    if(!token){
      setState("waiting");
      setMessage("请输入私有授权凭据，再进入小红书扫码登录。");
      return;
    }
    setState("authorizing");
    setMessage("正在建立此浏览器的私有运营会话…");
    try{
      const response=await fetch(`${API}/v1/admin/session`,{
        method:"POST",
        headers:{"Content-Type":"application/json"},
        body:JSON.stringify({token}),
        cache:"no-store",
      });
      token="";
      if(credentialRef.current)credentialRef.current.value="";
      if(!response.ok)throw new Error(await responseDetail(response));
      window.location.replace("/account?onboarding=1&next=%2Fdashboard");
    }catch(reason){
      token="";
      if(credentialRef.current)credentialRef.current.value="";
      setState("failed");
      setMessage(reason instanceof Error?reason.message:"无法建立私有运营会话");
    }
  },[]);

  useEffect(()=>{
    const rawToken=window.location.hash.startsWith("#")
      ? window.location.hash.slice(1)
      : "";
    window.history.replaceState(null,"",window.location.pathname);
    let token="";
    try{token=decodeURIComponent(rawToken).trim()}
    catch{token=""}
    if(token)void authorize(token);
    else{
      setState("waiting");
      setMessage("请输入私有授权凭据，再进入小红书扫码登录。");
    }
    token="";
  },[authorize]);

  function submit(event:React.FormEvent){
    event.preventDefault();
    void authorize(credentialRef.current?.value||"");
  }

  return <div className="login-gate" role={state==="failed"?"alert":"status"}>
    <section className="login-gate-card">
      <div className="eyebrow">PRIVATE ACCESS</div>
      <h1>{state==="authorizing"?"正在安全授权":state==="failed"?"授权失败":"私有运营入口"}</h1>
      <p>{message}</p>
      {state==="authorizing"&&<span className="spinner" aria-hidden="true"/>}
      {state!=="authorizing"&&<form className="access-form" onSubmit={submit}>
        <label>私有授权凭据
          <input ref={credentialRef} type="password" required autoComplete="off" spellCheck={false}/>
        </label>
        <button className="button" type="submit">授权并继续</button>
      </form>}
    </section>
  </div>;
}
