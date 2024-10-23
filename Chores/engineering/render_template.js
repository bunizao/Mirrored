const fs = require('fs');
const path = require('path');
const Handlebars = require('handlebars');

// 读取模板文件
const templatePath = path.resolve(__dirname, 'Chores/engineering/templetes/All-in-One-2.x.sgmodule.hbs');
const templateContent = fs.readFileSync(templatePath, 'utf-8');
const template = Handlebars.compile(templateContent);

// 读取数据文件
const dataPath = path.resolve(__dirname, 'Chores/engineering/data/sgmodules_data.json');
const dataContent = fs.readFileSync(dataPath, 'utf-8');
const data = JSON.parse(dataContent);

// 渲染模板
const output = template(data);

// 写入输出文件
const outputPath = path.resolve(__dirname, 'Chores/sgmodule/All-in-One-2.x.sgmodule');
fs.writeFileSync(outputPath, output, 'utf-8');

console.log(`模板已成功渲染并保存到 ${outputPath}`);
