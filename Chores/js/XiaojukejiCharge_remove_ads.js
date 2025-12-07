/*
移除 ID 为 73482 的 Webpack 模块（包含会员、营销权益、活动入口等逻辑），净化页面卡片。
*/
let body = $response.body;

if (body) {
    // 匹配目标：73482:function(参数){
    // 兼容 key 可能带引号的情况，如 "73482":function...
    const targetModuleRegex = /("?73482"?\s*:\s*function\s*\([^)]*\)\s*\{)/g;

    // 替换策略：在函数体开头直接插入 return;
    // 结果变为：73482:function(参数){return; ...原代码...}
    // 效果：模块被加载时立即返回 undefined，内部逻辑不再执行
    body = body.replace(targetModuleRegex, '$1return;');
    
    $done({ body });
} else {
    $done({});
}