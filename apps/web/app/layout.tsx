import "./globals.css";
import "./navigation.css";
import {getProducts} from "@/lib/api";
import TopNav from "./SideNav";

export const metadata = {
  title: "GrowthAgent｜把真实需求变成增长",
  description: "发现真实需求，自动完成克制、透明的产品沟通",
};

export default async function Layout({children}: {children: React.ReactNode}) {
  const products = await getProducts();
  return (
    <html lang="zh-CN">
      <body>
        <div className="app-shell">
          <TopNav products={products} />
          <main className="workspace-main">{children}</main>
        </div>
      </body>
    </html>
  );
}
