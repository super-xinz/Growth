import assert from "node:assert/strict";
import test from "node:test";
import {inferProductName} from "../lib/product-source.ts";

test("infers a usable product name when the user only supplies one URL",()=>{
  assert.equal(inferProductName("https://growthagent.example.com/pricing"),"growthagent");
  assert.equal(inferProductName("https://github.com/super-xinz/Growth"),"Growth");
  assert.equal(inferProductName("not a URL"),"我的产品");
});
