import type {NextRequest} from "next/server";

type RouteContext = {params:Promise<{path:string[]}>};

const HOP_BY_HOP_HEADERS = [
  "connection",
  "content-length",
  "host",
  "keep-alive",
  "proxy-authenticate",
  "proxy-authorization",
  "te",
  "trailer",
  "transfer-encoding",
  "upgrade",
];

async function proxy(request:NextRequest,{params}:RouteContext){
  const {path}=await params;
  const baseUrl=(process.env.API_URL||"http://api:8000").replace(/\/$/,"");
  const target=new URL(`${baseUrl}/${path.map(encodeURIComponent).join("/")}`);
  target.search=request.nextUrl.search;

  const headers=new Headers(request.headers);
  for(const name of HOP_BY_HOP_HEADERS)headers.delete(name);
  headers.set("x-forwarded-host",request.nextUrl.host);
  headers.set("x-forwarded-proto",request.nextUrl.protocol.replace(":",""));

  const init:RequestInit={
    method:request.method,
    headers,
    redirect:"manual",
    cache:"no-store",
  };
  if(request.method!=="GET"&&request.method!=="HEAD")init.body=await request.arrayBuffer();

  try{
    const response=await fetch(target,init);
    const responseHeaders=new Headers(response.headers);
    for(const name of HOP_BY_HOP_HEADERS)responseHeaders.delete(name);
    return new Response(response.body,{
      status:response.status,
      statusText:response.statusText,
      headers:responseHeaders,
    });
  }catch{
    return Response.json({detail:"后端服务暂时不可用，请稍后重试"},{status:502});
  }
}

export const dynamic="force-dynamic";
export const GET=proxy;
export const POST=proxy;
export const PUT=proxy;
export const PATCH=proxy;
export const DELETE=proxy;
export const OPTIONS=proxy;
