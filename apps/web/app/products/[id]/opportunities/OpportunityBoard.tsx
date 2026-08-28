"use client";

import {useMemo, useState} from "react";
import {useRouter} from "next/navigation";
import {ArrowUpRight, Check, CircleAlert, Sparkles} from "lucide-react";
import {API,responseDetail} from "@/lib/api";
import {filterOpportunities, isCurrentAutoReply, summarizeOpportunityWorkflow, type OpportunityView} from "@/lib/navigation";

type Opportunity = {
  id:string;status:string;title?:string|null;body:string;permalink?:string|null;
  opportunity_score:number;risk_score:number;publish_status?:string|null;generated_reply?:string|null;
  target_type?:string|null;author_name?:string|null;score_reason?:string|null;
  match_signals?:string[];publish_error?:string|null;
};

const tabs:{id:OpportunityView;label:string}[] = [
  {id:"all",label:"全部"},{id:"qualified",label:"高意向"},
  {id:"published",label:"已触达"},{id:"attention",label:"需关注"},
];

function stateLabel(row:Opportunity){
  if(row.publish_status==="COMMENTED"||row.status==="COMMENTED")return "已自动触达";
  if(row.publish_error)return "发布状态待确认";
  if(row.generated_reply&&!isCurrentAutoReply(row.generated_reply))return "旧草稿已冻结";
  if(row.opportunity_score>=.75&&row.risk_score<=.35)return row.generated_reply?"等待安全窗口":"准备回复中";
  return "仅记录";
}

export default function OpportunityBoard({rows}:{rows:Opportunity[]}){
  const router=useRouter();
  const [view,setView]=useState<OpportunityView>("all");
  const [selectedId,setSelectedId]=useState<string|null>(rows[0]?.id??null);
  const [publishing,setPublishing]=useState<string|null>(null);
  const [actionError,setActionError]=useState<Record<string,string>>({});
  const summary=useMemo(()=>summarizeOpportunityWorkflow(rows),[rows]);
  const visible=useMemo(()=>filterOpportunities(rows,view) as Opportunity[],[rows,view]);
  const selected=visible.find(row=>row.id===selectedId)??visible[0]??null;
  const counts={all:summary.total,qualified:summary.highIntent,published:summary.published,attention:rows.filter(row=>row.publish_error).length};

  async function generateAndPublish(id:string){
    setPublishing(id);setActionError(current=>({...current,[id]:""}));
    try{
      const response=await fetch(`${API}/v1/xiaohongshu/opportunities/${id}/generate-and-publish`,{method:"POST"});
      if(!response.ok)throw new Error(await responseDetail(response));
      router.refresh();
    }catch(reason){
      setActionError(current=>({...current,[id]:reason instanceof Error?reason.message:"生成并发布失败"}));
    }finally{setPublishing(null)}
  }
  return <section className="opportunity-shell">
    <div className="opportunity-toolbar">
      <nav className="workflow-tabs" aria-label="结果筛选">
        {tabs.map(tab=><button key={tab.id} className={view===tab.id?"active":""} onClick={()=>setView(tab.id)}>{tab.label}<span>{counts[tab.id]}</span></button>)}
      </nav>
      <div className="opportunity-summary"><strong>{summary.highIntent}</strong> 条高意向，<strong>{summary.ready}</strong> 条等待触达</div>
    </div>

    {visible.length?<div className="opportunity-workspace">
      <div className="opportunity-list" role="listbox" aria-label="机会列表">
        {visible.map(row=>{
          const active=row.id===selected?.id;
          return <button
            type="button"
            role="option"
            aria-selected={active}
            className={`opportunity-row${active?" active":""}`}
            key={row.id}
            onClick={()=>setSelectedId(row.id)}
          >
            <div className="opportunity-row-top">
              <span className="score-badge">{Math.round(row.opportunity_score*100)}</span>
              <span className={`row-state${row.publish_error?" warning":""}`}>{stateLabel(row)}</span>
            </div>
            <strong>{row.title||"小红书讨论"}</strong>
            <p>{row.body}</p>
            <div className="row-meta"><span>{row.target_type==="COMMENT"?"评论":"笔记"}</span>{row.author_name&&<span>@{row.author_name}</span>}<span>风险 {Math.round(row.risk_score*100)}</span></div>
          </button>;
        })}
      </div>

      {selected&&<article className="opportunity-detail" aria-live="polite">
        <header className="detail-header">
          <div>
            <div className="detail-kicker"><span className={`status ${selected.publish_error?"warning":""}`}>{stateLabel(selected)}</span><span>机会 {Math.round(selected.opportunity_score*100)}</span><span>风险 {Math.round(selected.risk_score*100)}</span></div>
            <h2>{selected.title||"小红书讨论"}</h2>
            <div className="result-meta"><span>{selected.target_type==="COMMENT"?"评论":"笔记"}</span>{selected.author_name&&<span>@{selected.author_name}</span>}</div>
          </div>
          {selected.permalink&&<a className="source-link" href={selected.permalink} target="_blank" rel="noreferrer">查看原文 <ArrowUpRight size={15}/></a>}
        </header>

        <section className="detail-section source-content">
          <div className="detail-label">原始需求</div>
          <p>{selected.body}</p>
        </section>

        <section className="detail-section decision-section">
          <div className="detail-label"><Sparkles size={15}/> 判断依据</div>
          <p>{selected.score_reason||"系统根据需求表达、产品能力和当前风险综合判断。"}</p>
          {!!selected.match_signals?.length&&<div className="signal-cloud small">{selected.match_signals.map(signal=><span key={signal}>{signal}</span>)}</div>}
          <div className="score-bars">
            <div><span>机会匹配</span><i><b style={{width:`${Math.round(selected.opportunity_score*100)}%`}}/></i><strong>{Math.round(selected.opportunity_score*100)}</strong></div>
            <div><span>发布风险</span><i><b className="risk" style={{width:`${Math.round(selected.risk_score*100)}%`}}/></i><strong>{Math.round(selected.risk_score*100)}</strong></div>
          </div>
        </section>

        <section className="detail-section reply-section">
          <div className="detail-label">{selected.publish_status==="COMMENTED"?<Check size={15}/>:selected.publish_error?<CircleAlert size={15}/>:<Sparkles size={15}/>} 回复状态</div>
          {selected.generated_reply&&(selected.publish_status==="COMMENTED"||isCurrentAutoReply(selected.generated_reply))?<blockquote className="sent-reply">“{selected.generated_reply}”</blockquote>:selected.generated_reply?<p>旧版本草稿不满足 25 字规则，不会发送；再次命中时会重写。</p>:<p>尚未生成回复。系统只会在语境明确且风险足够低时触达。</p>}
          {selected.publish_status!=="COMMENTED"&&selected.status!=="COMMENTED"&&!selected.publish_error&&<button className="button compact" disabled={publishing===selected.id} onClick={()=>void generateAndPublish(selected.id)}>{publishing===selected.id?"正在生成并发布…":"生成回复并发布"}</button>}
          {actionError[selected.id]&&<div className="compact-alert">{actionError[selected.id]}</div>}
          {selected.publish_error&&<div className="compact-alert">{selected.publish_error}</div>}
        </section>
      </article>}
    </div>:<div className="empty-state opportunity-empty"><h3>{rows.length?"这个分组还没有结果":"第一轮搜索后，结果会出现在这里"}</h3><p>{rows.length?"切换其他筛选查看。":"你可以等待自动运行，或回到产品页立即运行一次。"}</p></div>}
  </section>;
}
