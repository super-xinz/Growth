import {notFound} from "next/navigation";
import {getOpportunities, getProduct} from "@/lib/api";
import OpportunityBoard from "./OpportunityBoard";

export default async function Opportunities({params}:{params:Promise<{id:string}>}){
  const {id}=await params;
  const [rows, product]=await Promise.all([getOpportunities(id), getProduct(id)]);
  if(!product)notFound();
  return <>
    <header className="page-header result-header"><div><div className="eyebrow">{product.name}</div><h1>机会</h1><p>按优先级判断需求，只在语境明确时触达。</p></div></header>
    <OpportunityBoard rows={rows}/>
  </>;
}
