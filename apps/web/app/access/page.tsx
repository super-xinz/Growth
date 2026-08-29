"use client";

import {useEffect, useState} from "react";
import {API, responseDetail} from "@/lib/api";

type AccessState="authorizing"|"failed";

export default function AccessPage(){
  const [state,setState]=useState<AccessState>("authorizing");
  const [message,setMessage]=useState("正在建立此浏览器的私有运营会话…");

  useEffect(()=>{
    let active=true;
    void (async()=>{
      const rawToken=window.location.hash.startsWith("#")
        ? window.location.hash.slice(1)
        : "";
      window.history.replaceState(null,"",window.location.pathname);
      let token="";
      try{token=decodeURIComponent(rawToken).trim()}
      catch{token=""}
      if(!token){
        if(active){setState("failed");setMessage("授权链接缺少凭据，请重新使用完整的私有链接。")}
        return;
      }
      try{
        const response=await fetch(`${API}/v1/admin/session`,{
          method:"POST",
          headers:{"Content-Type":"application/json"},
          body:JSON.stringify({token}),
          cache:"no-store",
        });
        token="";
        if(!response.ok)throw new Error(await responseDetail(response));
        window.location.replace("/account?onboarding=1&next=%2Fdashboard");
      }catch(reason){
        token="";
        if(active){
          setState("failed");
          setMessage(reason instanceof Error?reason.message:"无法建立私有运营会话");
        }
      }
    })();
    return()=>{active=false};
  },[]);

  return <div className="login-gate" role={state==="failed"?"alert":"status"}>
    <section className="login-gate-card">
      <div className="eyebrow">PRIVATE ACCESS</div>
      <h1>{state==="failed"?"授权失败":"正在安全授权"}</h1>
      <p>{message}</p>
      {state==="authorizing"&&<span className="spinner" aria-hidden="true"/>}
    </section>
  </div>;
}
