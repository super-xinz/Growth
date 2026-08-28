import {notFound} from "next/navigation";
import {getBrain,getProduct} from "@/lib/api";
import RebuildBrainButton from "./RebuildBrainButton";
import ProductModeControls from "./ProductModeControls";
import ProductSettingsForm from "./ProductSettingsForm";

function Items({items}:{items?:string[]}){return items?.length?<ul>{items.map((item,i)=><li key={i}>{item}</li>)}</ul>:<p>暂未识别。</p>}

export default async function ProductPage({params}:{params:Promise<{id:string}>}){
  const {id}=await params;
  const [p,brain]=await Promise.all([getProduct(id),getBrain(id)]);
  if(!p)notFound();
  const b=brain?.brain||{};
  return <>
    <header className="product-heading"><div><div className="eyebrow">{b.category||"产品"} · PRODUCT BRAIN V{brain?.version||"—"}</div><h1>{p.name}</h1><p>{b.one_liner||"等待产品分析。"}</p></div></header>
    <ProductModeControls product={p}/>
    <div className="record-stack">
    <details className="details-section" open>
      <summary><span><span className="eyebrow">Product Brain</span><strong>受众与需求</strong></span><span>＋</span></summary>
      <section className="grid brain-grid">
      <div className="card wide"><div className="label">目标用户</div><Items items={b.target_users}/></div>
      <div className="card wide"><div className="label">用户要完成的任务</div><Items items={b.jobs_to_be_done}/></div>
      <div className="card wide"><div className="label">核心痛点</div><Items items={b.pain_points}/></div>
      <div className="card wide"><div className="label">使用场景</div><Items items={b.use_cases}/></div>
      <div className="card wide"><div className="label">适合推荐</div><Items items={b.recommend_when}/></div>
      <div className="card wide"><div className="label">不应推荐</div><Items items={b.do_not_recommend_when}/></div>
      <div className="card full"><div className="label">搜索信号</div><div className="signal-cloud">{[...(b.query_graph?.pain_phrases||[]),...(b.query_graph?.use_cases||[])].map((x:string)=><span key={x}>{x}</span>)}</div></div>
      </section>
    </details>
    <details className="details-section"><summary><span><span className="eyebrow">Evidence & Settings</span><strong>证据与设置</strong></span><span>＋</span></summary><section className="grid brain-grid">
      <div className="card full"><div className="label">有来源支持的能力</div>{(b.supported_claims||[]).map((c:any,i:number)=><div key={i} className="claim-row"><p>{c.claim}</p><blockquote>{c.source_quote}</blockquote></div>)}</div>
      <div className="card wide"><div className="label">不确定或缺少证据</div><Items items={b.unsupported_or_uncertain_claims}/></div>
      <div className="card wide"><div className="label">更新产品资料</div><ProductSettingsForm product={p}/><div className="subtle-actions"><RebuildBrainButton productId={id}/></div></div>
    </section></details>
    </div>
  </>;
}
