const fs = require('fs');
const path = require('path');
const Handlebars = require('handlebars');

// 手动注册 'ne' helper
Handlebars.registerHelper('ne', function(v1, v2, options) {
  return v1 !== v2 ? options.fn(this) : options.inverse(this);
});

// 引入并注册所有 helpers（可选）
const helpers = require('handlebars-helpers')({
  handlebars: Handlebars
});

// 打印已注册的 helpers
console.log('Registered helpers:', Object.keys(Handlebars.helpers));

// 当前脚本所在目录
const currentDir = __dirname;

// 模板文件路径
const templatePath = path.resolve(currentDir, 'templates/All-in-One-2.x.sgmodule.hbs');

// 数据文件路径
const dataPath = path.resolve(currentDir, 'data/sgmodules_data.json');

// 输出文件路径（上一级目录的 sgmodule 文件夹）
const outputPath = path.resolve(currentDir, '../sgmodule/All-in-One-2.x.sgmodule');

// 调试输出路径
console.log(`模板路径：${templatePath}`);
console.log(`数据路径：${dataPath}`);
console.log(`输出路径：${outputPath}`);

// 读取模板文件
const templateContent = fs.readFileSync(templatePath, 'utf-8');
const template = Handlebars.compile(templateContent);

// 读取数据文件
const dataContent = fs.readFileSync(dataPath, 'utf-8');
const data = JSON.parse(dataContent);

// 渲染模板
const output = template(data);

// 确保输出目录存在
const outputDir = path.dirname(outputPath);
if (!fs.existsSync(outputDir)) {
  fs.mkdirSync(outputDir, { recursive: true });
}

// 写入输出文件
fs.writeFileSync(outputPath, output, 'utf-8');

console.log(`模板已成功渲染并保存到 ${outputPath}`);
