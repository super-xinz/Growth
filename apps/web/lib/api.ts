export const API=typeof window==="undefined"
  ? process.env.API_URL||"http://api:8000"
  : process.env.NEXT_PUBLIC_API_URL||"http://localhost:8000";

export async function responseDetail(response:Response){
  const text=await response.text();
  if(!text)return `${response.status} ${response.statusText}`;
  try{const body=JSON.parse(text);return body.detail||body.message||JSON.stringify(body)}
  catch{return text}
}

async function apiJson(path:string,{allow404=false}:{allow404?:boolean}={}){
  const response=await fetch(`${API}${path}`,{cache:"no-store"});
  if(allow404&&response.status===404)return null;
  if(!response.ok)throw new Error(await responseDetail(response));
  return response.json();
}

export const getHealth=()=>apiJson("/health");
export const getProducts=()=>apiJson("/v1/products");
export const getProduct=(id:string)=>apiJson(`/v1/products/${id}`,{allow404:true});
export const getBrain=(id:string)=>apiJson(`/v1/products/${id}/brain`,{allow404:true});
export const getOpportunities=(id:string)=>apiJson(`/v1/products/${id}/opportunities`);
export const getTrashedProducts=()=>apiJson("/v1/products/trash");

async function mutateJson(path:string,method:string,body?:unknown){
  const response=await fetch(`${API}${path}`,{
    method,
    headers:body?{"Content-Type":"application/json"}:undefined,
    body:body?JSON.stringify(body):undefined,
  });
  if(!response.ok)throw new Error(await responseDetail(response));
  return response.json();
}

export const reorderProducts=(productIds:string[])=>mutateJson("/v1/products/order","PUT",{product_ids:productIds});
export const trashProduct=(id:string)=>mutateJson(`/v1/products/${id}`,"DELETE");
export const restoreProduct=(id:string)=>mutateJson(`/v1/products/${id}/restore`,"POST");
export const permanentlyDeleteProduct=(id:string)=>mutateJson(`/v1/products/${id}/permanent`,"DELETE");
export const getXiaohongshuStatus=()=>apiJson("/v1/xiaohongshu/status");
export const getXiaohongshuQrcode=()=>apiJson("/v1/xiaohongshu/login/qrcode");
