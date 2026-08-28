import Link from "next/link";
import {getOpportunities, getProducts, getTrashedProducts} from "@/lib/api";
import {summarizeOpportunityWorkflow} from "@/lib/navigation";
import ProductManager from "./ProductManager";

export default async function Dashboard() {
  const [products, trashedProducts] = await Promise.all([getProducts(), getTrashedProducts()]);
  const opportunitySets = await Promise.all(products.map(async (product:any) => {
    try { return [product.id, await getOpportunities(product.id)] as const; }
    catch { return [product.id, []] as const; }
  }));
  const workflowByProduct = Object.fromEntries(opportunitySets.map(([id, rows]) => [id, summarizeOpportunityWorkflow(rows)]));
  const workflow = summarizeOpportunityWorkflow(opportunitySets.flatMap(([, rows]) => rows));
  const running=products.filter((product:any)=>product.autopublish_enabled).length;

  return (
    <div className="workspace-page">
      <header className="workspace-header">
        <div>
          <div className="eyebrow">工作台</div>
          <h1>今天需要关注什么</h1>
          <p>查看产品运行状态，并优先处理高意向机会。</p>
        </div>
        <Link className="button" href="/products/new">添加产品</Link>
      </header>

      <section className="workspace-content">
          <div className="dashboard-metrics">
            <div className="dashboard-metric">
              <span>运行中的产品</span>
              <strong>{running}</strong>
              <small>保持低频搜索</small>
            </div>
            <div className="dashboard-metric">
              <span>高意向机会</span>
              <strong>{workflow.highIntent}</strong>
              <small>建议优先查看</small>
            </div>
            <div className="dashboard-metric">
              <span>已完成触达</span>
              <strong>{workflow.published}</strong>
              <small>自动或手动回复</small>
            </div>
          </div>

          <div className="section-intro">
            <div>
              <div className="eyebrow">产品运行</div>
              <h2 className="heading-lg">所有产品</h2>
              <p>状态、机会和下一次运行集中在一处。</p>
            </div>
          </div>

          <ProductManager initialProducts={products} trashedProducts={trashedProducts} workflowByProduct={workflowByProduct}/>
      </section>
    </div>
  );
}
