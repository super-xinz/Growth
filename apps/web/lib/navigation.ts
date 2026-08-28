export type ProductNavItem = {
  id: string;
  name: string;
  status: string;
  website_url?: string | null;
  github_url?: string | null;
  daily_reply_limit?: number;
  sort_order?: number;
  deleted_at?: string | null;
  purge_after?: string | null;
  is_owned?: boolean;
  autopublish_enabled?: boolean;
  automation_status?: string;
  automation_error?: string | null;
  next_auto_search_at?: string | null;
  last_auto_publish_at?: string | null;
};

export type OpportunityWorkflowItem = {
  opportunity_score: number;
  generated_reply?: string | null;
  publish_status?: string | null;
};

export type OpportunityView = "all" | "qualified" | "published" | "attention";

export function isCurrentAutoReply(reply?: string | null) {
  const length = reply?.trim().length ?? 0;
  return length >= 6 && length <= 25;
}

export function summarizeOpportunityWorkflow(rows: OpportunityWorkflowItem[]) {
  return {
    total: rows.length,
    highIntent: rows.filter((row) => row.opportunity_score >= 0.75).length,
    ready: rows.filter((row) => isCurrentAutoReply(row.generated_reply) && !row.publish_status).length,
    published: rows.filter((row) => row.publish_status === "COMMENTED").length,
  };
}

export function filterOpportunities(
  rows: OpportunityWorkflowItem[],
  view: OpportunityView,
) {
  if (view === "qualified") return rows.filter((row) => row.opportunity_score >= 0.75);
  if (view === "attention") {
    return rows.filter((row) => Boolean((row as OpportunityWorkflowItem & {publish_error?:string|null}).publish_error));
  }
  if (view === "published") {
    return rows.filter((row) => row.publish_status === "COMMENTED");
  }
  return rows;
}

export function parseProductId(pathname: string) {
  const match = pathname.match(/^\/products\/([^/]+)/);
  return match?.[1] && match[1] !== "new" ? match[1] : null;
}

export function filterProducts(products: ProductNavItem[], query: string) {
  const normalized = query.trim().toLocaleLowerCase("zh-CN");
  return normalized
    ? products.filter((product) =>
        product.name.toLocaleLowerCase("zh-CN").includes(normalized),
      )
    : products;
}

export function summarizeProducts(products: ProductNavItem[]) {
  return {
    total: products.length,
    ready: products.filter((product) => product.status === "READY").length,
    running: products.filter((product) => product.status === "SHADOW_RUNNING")
      .length,
    attention: products.filter((product) =>
      ["ANALYSIS_FAILED", "INGEST_FAILED"].includes(product.status),
    ).length,
  };
}

export function isNavActive(pathname: string, href: string) {
  return pathname === href;
}

export function moveProduct<T>(items: T[], from: number, to: number) {
  if (from < 0 || to < 0 || from >= items.length || to >= items.length || from === to) {
    return items.slice();
  }
  const reordered = items.slice();
  const [moved] = reordered.splice(from, 1);
  reordered.splice(to, 0, moved);
  return reordered;
}

export function retentionDays(purgeAfter: string, now = new Date()) {
  return Math.max(0, Math.ceil((new Date(purgeAfter).getTime() - now.getTime()) / 86_400_000));
}
