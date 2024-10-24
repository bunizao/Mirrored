const fs = require('fs');
const path = require('path');
const Handlebars = require('handlebars');

// 当前脚本所在目录
const currentDir = __dirname;

// 模板文件路径
const templatePath = path.resolve(currentDir, '../../templates/All-in-One-2.x.sgmodule.hbs');

// 数据文件路径
const dataPath = path.resolve(currentDir, 'data/sgmodules_data.json');

// 输出文件路径
const outputPath = path.resolve(currentDir, '../../sgmodule/All-in-One-2.x.sgmodule');

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

// 写入输出文件
fs.writeFileSync(outputPath, output, 'utf-8');

console.log(`Render success and saved in ${outputPath}`);
