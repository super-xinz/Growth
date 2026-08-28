import assert from "node:assert/strict";
import test from "node:test";
import {
  filterProducts,
  isNavActive,
  moveProduct,
  parseProductId,
  summarizeProducts,
  summarizeOpportunityWorkflow,
  filterOpportunities,
  retentionDays,
} from "../lib/navigation.ts";

const products = [
  {id: "alpha", name: "Alpha Pilot", status: "READY"},
  {id: "beta", name: "Beta Lab", status: "ANALYSIS_FAILED"},
  {id: "gamma", name: "Gamma", status: "SHADOW_RUNNING"},
];

test("parses a real product id but excludes the new route", () => {
  assert.equal(parseProductId("/products/alpha/opportunities"), "alpha");
  assert.equal(parseProductId("/products/new"), null);
  assert.equal(parseProductId("/dashboard"), null);
});

test("moves a product without mutating the source order", () => {
  const ids = ["a", "b", "c"];
  assert.deepEqual(moveProduct(ids, 0, 2), ["b", "c", "a"]);
  assert.deepEqual(ids, ["a", "b", "c"]);
  assert.deepEqual(moveProduct(ids, -1, 2), ids);
  assert.deepEqual(moveProduct(ids, 1, 9), ids);
});

test("rounds remaining retention up to whole days", () => {
  const now = new Date("2026-07-12T00:00:00Z");
  assert.equal(retentionDays("2026-07-18T12:00:00Z", now), 7);
  assert.equal(retentionDays("2026-07-11T00:00:00Z", now), 0);
});

test("filters products case-insensitively without changing source order", () => {
  assert.deepEqual(
    filterProducts(products, "PILOT").map((product) => product.id),
    ["alpha"],
  );
  assert.deepEqual(
    filterProducts(products, "").map((product) => product.id),
    ["alpha", "beta", "gamma"],
  );
});

test("summarizes all product statuses", () => {
  assert.deepEqual(summarizeProducts(products), {
    total: 3,
    ready: 1,
    running: 1,
    attention: 1,
  });
});

test("marks only the exact product section active", () => {
  assert.equal(isNavActive("/products/alpha", "/products/alpha"), true);
  assert.equal(
    isNavActive("/products/alpha/opportunities", "/products/alpha"),
    false,
  );
  assert.equal(
    isNavActive(
      "/products/alpha/opportunities",
      "/products/alpha/opportunities",
    ),
    true,
  );
});

test("returns zero metrics for an empty product list", () => {
  assert.deepEqual(summarizeProducts([]), {
    total: 0,
    ready: 0,
    running: 0,
    attention: 0,
  });
});

test("summarizes opportunity workflow states", () => {
  const rows = [
    {opportunity_score: 0.82, generated_reply: "这个思路可以试试", publish_status: null},
    {opportunity_score: 0.74, generated_reply: null, publish_status: null},
    {opportunity_score: 0.61, generated_reply: "低分但合格草稿", publish_status: null},
    {opportunity_score: 0.9, generated_reply: "已发布", publish_status: "COMMENTED"},
    {opportunity_score: 0.88, generated_reply: "这是一条来自旧版本并且明显超过二十五个字符的长草稿所以必须冻结", publish_status: null},
  ];
  assert.deepEqual(summarizeOpportunityWorkflow(rows), {
    total: 5,
    highIntent: 3,
    ready: 2,
    published: 1,
  });
});

test("filters opportunities by workflow view", () => {
  const rows = [
    {opportunity_score: 0.8, generated_reply: "草稿", publish_status: null},
    {opportunity_score: 0.5, generated_reply: null, publish_status: null},
    {opportunity_score: 0.9, generated_reply: "完成", publish_status: "COMMENTED"},
  ];
  assert.equal(filterOpportunities(rows, "qualified").length, 2);
  assert.equal(filterOpportunities(rows, "attention").length, 0);
  assert.equal(filterOpportunities(rows, "published").length, 1);
});
