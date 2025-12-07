/*
移除“权益与营销活动类”（邀请有礼、福利兑换、借钱等）及“会员相关”（会员价、专属券等）卡片。
*/
let body = $response.body;

// ==============================================================================
// 1. 移除会员相关卡片 (来自模块 73482 - MemberCard)
// ==============================================================================
// 将判断会员入口展示的逻辑条件强制设为 false
// 原代码: e.isShowMemberEntrance||e.showModuleSkeleton&&...
const memberCardCondition = /e\.isShowMemberEntrance\|\|e\.showModuleSkeleton&&e\.showModuleSkeleton\.member&&e\.checkLogin/g;
body = body.replace(memberCardCondition, 'false');

// ==============================================================================
// 2. 移除“低碳家园” (来自模块 73482 - BenifitCard - carbon-card)
// ==============================================================================
// 原代码: n("carbon-card", ...
// 替换为: e._e("carbon-card", ...  (Vue的空节点渲染函数)
body = body.replace(/n\("carbon-card",/g, 'e._e("carbon-card",');

// ==============================================================================
// 3. 移除其他权益与营销活动图标 (来自模块 73482 - BenifitCard)
// ==============================================================================
// 定义需要移除的功能函数名列表
const marketingFuncs = [
    "handleLinkInvite",   // 邀请有礼
    "toRedeemExchange",   // 福利兑换
    "toJumpGun",          // 跳枪赔付
    "toYouxuan",          // 优选站
    "toAccChargePage",    // 加速充
    "toAds",              // 借钱
    "toActCenter",        // 活动中心
    "toChargeLowCarbon"   // 低碳家园(备用入口)
];

// 使用循环遍历替换，避免复杂正则导致的语法错误
// 目标模式: n("ThanosView",{staticClass:["item-wrapper"],attrs:{prismFunctionName:"函数名"
// 替换模式: e._e("ThanosView",{staticClass:["item-wrapper"],attrs:{prismFunctionName:"函数名"
marketingFuncs.forEach(funcName => {
    // 构建精确匹配的字符串片段
    const targetStr = `n("ThanosView",{staticClass:["item-wrapper"],attrs:{prismFunctionName:"${funcName}"`;
    const replaceStr = `e._e("ThanosView",{staticClass:["item-wrapper"],attrs:{prismFunctionName:"${funcName}"`;
    
    // 对目标字符串中的特殊字符进行正则转义 ( [ { . )
    // n\("ThanosView",\{staticClass:\["item-wrapper"\],attrs:\{prismFunctionName:"funcName"
    const regexSafeTarget = targetStr.replace(/([()[\]{}.])/g, '\\$1');
    
    // 创建正则并替换
    const reg = new RegExp(regexSafeTarget, 'g');
    body = body.replace(reg, replaceStr);
});

$done({ body });