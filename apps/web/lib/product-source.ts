export function inferProductName(rawUrl:string){
  try{
    const url=new URL(rawUrl);
    const hostname=url.hostname.toLowerCase().replace(/^www\./,"");
    const pathParts=url.pathname.split("/").filter(Boolean);
    const source=hostname==="github.com"&&pathParts.length>=2
      ? pathParts[1]
      : hostname.split(".")[0];
    const decoded=decodeURIComponent(source).replace(/[-_]+/g," ").trim();
    return decoded.slice(0,200)||"我的产品";
  }catch{
    return "我的产品";
  }
}
