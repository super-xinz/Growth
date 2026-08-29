import "./globals.css";
import "./navigation.css";
import {getHealth, getProducts} from "@/lib/api";
import TopNav from "./SideNav";
import XiaohongshuGate from "./XiaohongshuGate";

export const metadata = {
  title: "GrowthAgent｜把真实需求变成增长",
  description: "发现真实需求，自动完成克制、透明的产品沟通",
};

export default async function Layout({children}: {children: React.ReactNode}) {
  const [health, products] = await Promise.all([getHealth(), getProducts()]);
  return (
    <html lang="zh-CN">
      <body>
        <XiaohongshuGate publicDemo={Boolean(health.public_demo)} />
        <div className="app-shell">
          <TopNav products={products} />
          <main className="workspace-main">{children}</main>
        </div>
      </body>
    </html>
  );
}
