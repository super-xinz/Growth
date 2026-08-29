import "./globals.css";
import "./navigation.css";
import {cookies} from "next/headers";
import {getAdminSession, getHealth, getProducts} from "@/lib/api";
import TopNav from "./SideNav";
import XiaohongshuGate from "./XiaohongshuGate";

export const metadata = {
  title: "GrowthAgent｜把真实需求变成增长",
  description: "发现真实需求，自动完成克制、透明的产品沟通",
};

export default async function Layout({children}: {children: React.ReactNode}) {
  const cookieHeader=(await cookies()).getAll()
    .map(({name,value})=>`${name}=${value}`)
    .join("; ");
  const [health, products, adminSession] = await Promise.all([
    getHealth(),
    getProducts(),
    getAdminSession(cookieHeader),
  ]);
  const ownerMode=!health.public_demo||Boolean(adminSession.authenticated);
  return (
    <html lang="zh-CN">
      <body>
        <XiaohongshuGate enabled={ownerMode} />
        <div className="app-shell">
          <TopNav products={products} />
          <main className="workspace-main">{children}</main>
        </div>
      </body>
    </html>
  );
}
