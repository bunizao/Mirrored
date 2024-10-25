# 定义输出文件路径
output_path = 'Chores/sgmodule/All-in-One-2.x.sgmodule'

# 其余部分不变
with open(template_path, 'r') as template_file:
    template_content = template_file.read()

# 替换模板中的占位符
for section, contents in sections.items():
    placeholder = f"{{{section}}}"  # 例如 {URL Rewrite}
    if section == "MITM":
        section_content = "\n".join(contents)  # MITM 主机名列表合并为字符串
    else:
        section_content = "\n\n".join(contents)  # 其他区块内容合并为字符串
    template_content = template_content.replace(placeholder, section_content)

# 将合并内容写入输出文件
with open(output_path, 'w') as output_file:
    output_file.write(template_content)

print(f"文件已合并并保存为: {output_path}")
