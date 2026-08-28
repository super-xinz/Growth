"use client";

import Link from "next/link";
import {usePathname} from "next/navigation";
import {Activity, LayoutDashboard, Menu, Radar, Settings, X} from "lucide-react";
import {useEffect, useState} from "react";
import {isNavActive, parseProductId, type ProductNavItem} from "@/lib/navigation";
import BrandLogo from "./BrandLogo";
import ProductSwitcher from "./ProductSwitcher";

type NavItem = {href: string; label: string};

export default function TopNav({products}: {products: ProductNavItem[]}) {
  const pathname = usePathname();
  const productId = parseProductId(pathname);
  const [menuOpen, setMenuOpen] = useState(false);

  useEffect(() => setMenuOpen(false), [pathname]);
  
  const productItems: NavItem[] = productId
    ? [
        {href: `/products/${productId}`, label: "产品与自动化"},
        {href: `/products/${productId}/opportunities`, label: "机会"},
      ]
    : [];

  return (
    <div className="sidebar-slot">
      <div className="mobile-toolbar">
        <Link href="/dashboard" className="mobile-brand" aria-label="GrowthAgent"><BrandLogo/><strong>GrowthAgent</strong></Link>
        <button className="mobile-nav-trigger" type="button" aria-label={menuOpen ? "关闭导航" : "打开导航"} aria-expanded={menuOpen} onClick={() => setMenuOpen(value => !value)}>
          {menuOpen ? <X size={20} /> : <Menu size={20} />}
        </button>
      </div>

      <aside className={`sidebar${menuOpen ? " open" : ""}`}>
        <div className="sidebar-brand-row">
          <Link href="/dashboard" className="nav-brand" aria-label="GrowthAgent" prefetch={true}>
            <BrandLogo/>
            <span><strong>GrowthAgent</strong><small>机会工作台</small></span>
          </Link>
          <button className="sidebar-close" type="button" aria-label="关闭导航" onClick={() => setMenuOpen(false)}><X size={18}/></button>
        </div>
        <nav className="side-nav" aria-label="主导航">
          <div className="nav-section-label">工作区</div>
          <Link className={`nav-link${pathname === "/dashboard" ? " active" : ""}`} href="/dashboard" prefetch={true}>
            <LayoutDashboard size={18}/><span>工作台</span>
          </Link>

          {productItems.length > 0 && <>
            <div className="nav-section-label">当前产品</div>
            {productItems.map((item, index) => (
              <Link key={item.href} className={`nav-link${isNavActive(pathname, item.href) ? " active" : ""}`} href={item.href} prefetch={true}>
                {index === 0 ? <Activity size={18}/> : <Radar size={18}/>}<span>{item.label}</span>
              </Link>
            ))}
          </>}
        </nav>

        <div className="sidebar-footer">
          {!!products.length && <ProductSwitcher products={products} currentProductId={productId} />}
          <Link href="/account" prefetch={true} className={`account-link${pathname === "/account" ? " active" : ""}`}>
            <span><Settings size={18}/><span>设置</span></span>
          </Link>
        </div>
      </aside>
      {menuOpen && (
        <button className="sidebar-scrim" aria-label="关闭导航" onClick={() => setMenuOpen(false)}/>
      )}
    </div>
  );
}
