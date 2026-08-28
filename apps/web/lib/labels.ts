const labels:Record<string,string>={
  DRAFT:"草稿",INGESTED:"资料已抓取",READY:"分析完成",ANALYSIS_FAILED:"分析失败",SHADOW_RUNNING:"安全模拟中",PAUSED:"已暂停",
  DEVELOPMENT_ONLY:"仅开发环境",API_APPLICATION_PENDING:"API 申请审核中",API_APPROVED_NON_COMMERCIAL:"非商业 API 已批准",COMMERCIAL_APPROVED:"商业 API 已批准",
  ALLOW_AUTOREPLY:"允许自动回复",ALLOW_READ_ONLY:"仅允许读取",BLOCKED:"已禁止",
  SHADOW_ONLY:"仅模拟记录",ALLOW_REPLY:"允许回复",SKIP:"跳过",BLOCK:"禁止参与",ESCALATE_STOP:"停止并升级处理",
  SHADOW_RECORDED:"已保存模拟记录",PUBLISHED_MOCK:"模拟完成",PUBLISHED:"已发布",
  RECALLED:"已召回",POSTED:"已发布记录",USER_ENGAGED:"用户已互动",LINK_SHARED:"已分享链接",CLOSED:"已关闭",
  NONE:"无",PROTECTED:"受保护",HIGH:"高风险",INFO:"提示",WARNING:"警告",CRITICAL:"严重",
  ASKING_FOR_ALTERNATIVE:"寻找替代方案",SEEKING_RECOMMENDATION:"寻求推荐",ASKING_HOW_TO_SOLVE:"询问解决方法",GENERAL_DISCUSSION:"一般讨论",
  ASK_LINK:"索要链接",ASK_PRICE:"询问价格",ASK_FEATURE:"询问功能",ASK_COMPARISON:"请求对比",REPORT_BUG:"反馈问题",THANKS_ONLY:"仅表示感谢",EXPRESS_INTEREST:"表达兴趣",NEGATIVE_REACTION:"负面反馈",MOD_WARNING:"版主警告",
  HELP_AND_DISCLOSE:"帮助并披露关系",NONE_REPLY:"不回复",NO_LINK_UNLESS_REQUESTED:"仅在用户索要时提供链接",
  AUTOPUBLISH_BLOCKED:"自动发布已拦截",MANUAL_STOP:"人工停止",AUDIT_ONLY:"仅记录审计",
};

export function zhLabel(value:string|null|undefined,fallback="待处理"){
  if(!value)return fallback;
  return labels[value]||value.replaceAll("_"," ");
}
