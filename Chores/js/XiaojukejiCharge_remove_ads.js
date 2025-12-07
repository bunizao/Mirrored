/*
移除 ID 为 73482 的 Webpack 模块（包含会员、营销权益、活动入口等逻辑），净化页面卡片。
*/
let body = $response.body;

// 需要屏蔽的模块ID列表 (根据之前的分析，73482 是核心营销模块)
const targetModules = ["73482"];

if (body) {
    let modified = false;

    targetModules.forEach(id => {
        // 正则表达式详解：
        // 1. (["']?)       -> 捕获可能存在的引号 (兼容 "73482": 或 73482:)
        // 2. ${id}         -> 目标模块ID
        // 3. \1            -> 确保引号闭合匹配
        // 4. \s*:\s* -> 匹配冒号及周围可能存在的空白
        // 5. function      -> 匹配 function 关键字
        // 6. \s*\([^)]*\)  -> 匹配参数列表，如 (e) 或 (t,n,r)
        // 7. \s*\{         -> 匹配函数体开始的大括号
        const regex = new RegExp(`(["']?)${id}\\1\\s*:\\s*function\\s*\\([^)]*\\)\\s*\\{`, 'g');

        if (regex.test(body)) {
            // 替换策略：在函数体 { 后直接插入 "return;"
            // 效果：模块被加载时，直接返回 undefined (即 module.exports 保持默认空对象 {})
            // Vue 渲染空对象组件时会忽略，从而达到隐藏卡片的效果，且不破坏 JS 语法结构。
            body = body.replace(regex, (match) => {
                console.log(`[Didicharging] 成功屏蔽模块 ID: ${id}`);
                return match + "return;";
            });
            modified = true;
        }
    });

    if (modified) {
        $done({ body });
    } else {
        // 如果没找到目标ID，原样返回，避免不必要的开销
        console.log(`[Didicharging] 未找到目标模块，脚本未执行修改`);
        $done({});
    }
} else {
    $done({});
}