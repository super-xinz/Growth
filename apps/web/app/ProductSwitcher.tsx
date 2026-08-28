"use client";

import Link from "next/link";
import {ChevronDown, Plus} from "lucide-react";
import {useEffect, useRef, useState} from "react";
import {filterProducts, type ProductNavItem} from "@/lib/navigation";
import {zhLabel} from "@/lib/labels";

export default function ProductSwitcher({
  products,
  currentProductId,
}: {
  products: ProductNavItem[];
  currentProductId: string | null;
}) {
  const [open, setOpen] = useState(false);
  const [query, setQuery] = useState("");
  const rootRef = useRef<HTMLDivElement>(null);
  const current = products.find((product) => product.id === currentProductId);
  const filtered = filterProducts(products, query);

  useEffect(() => {
    function onPointerDown(event: PointerEvent) {
      if (!rootRef.current?.contains(event.target as Node)) setOpen(false);
    }
    function onKeyDown(event: KeyboardEvent) {
      if (event.key === "Escape") setOpen(false);
    }
    document.addEventListener("pointerdown", onPointerDown);
    document.addEventListener("keydown", onKeyDown);
    return () => {
      document.removeEventListener("pointerdown", onPointerDown);
      document.removeEventListener("keydown", onKeyDown);
    };
  }, []);

  function close() {
    setOpen(false);
    setQuery("");
  }

  return (
    <div className="product-switcher" ref={rootRef}>
      <div className="switcher-label">当前产品</div>
      <button
        className="switcher-trigger"
        type="button"
        aria-expanded={open}
        aria-controls="product-switcher-menu"
        onClick={() => setOpen((value) => !value)}
      >
        <span>
          <strong>{current?.name || "选择产品"}</strong>
          <small>{current ? zhLabel(current.status) : `${products.length} 个产品`}</small>
        </span>
        <ChevronDown className="switcher-chevron" size={15} aria-hidden="true" />
      </button>
      {open && (
        <div className="switcher-menu" id="product-switcher-menu">
          {products.length > 6 && <>
            <label className="switcher-search-label" htmlFor="product-search">搜索产品</label>
            <input
              id="product-search"
              className="switcher-search"
              value={query}
              onChange={(event) => setQuery(event.target.value)}
              placeholder="输入产品名称"
              autoFocus
            />
          </>}
          <div className="switcher-list">
            {filtered.map((product) => (
              <Link
                key={product.id}
                className={`switcher-product${product.id === currentProductId ? " current" : ""}`}
                href={`/products/${product.id}`}
                onClick={close}
              >
                <span>{product.name}</span>
                <small>{zhLabel(product.status)}</small>
              </Link>
            ))}
            {!filtered.length && <div className="switcher-empty">没有匹配的产品</div>}
          </div>
          <Link className="switcher-create" href="/products/new" onClick={close}>
            <Plus size={16} aria-hidden="true" /> 新建产品
          </Link>
        </div>
      )}
    </div>
  );
}
