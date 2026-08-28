"use client";

import {useEffect} from "react";

export default function ErrorPage({error,reset}:{error:Error&{digest?:string};reset:()=>void}){
  useEffect(()=>{console.error(error)},[error]);
  return <section className="state-page card"><div className="state-icon">!</div><h1>页面暂时无法加载</h1><p>后端服务可能正在重启，或者请求暂时失败。你的产品数据没有被删除。</p><button className="button" onClick={reset}>重新加载</button></section>;
}
