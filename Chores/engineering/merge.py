import requests
import re
import os
from datetime import datetime
import yaml

# 从 YAML 文件中加载 sgmodule_info
with open('CChores/engineering/data/sgmodules.yaml', 'r') as f:
    sgmodule_info = yaml.safe_load(f)

# 定义区块
sections = {
    "URL Rewrite": [],
    "Map Local": [],
    "Script": [],
    "MITM": [],   # 将所有的 hostname 收集到这里
    "Rules": []   # 新增一个区块用于收集 Rules 部分内容
}

# 定义正则表达式来匹配区块内容和 hostname 行
section_pattern = re.compile(r'\[(.*?)\]\n(.*?)(?=\n\[|$)', re.DOTALL)
hostname_pattern = re.compile(r'hostname\s*=\s*(.*)', re.IGNORECASE)

# 下载并解析每个文件的内容
for info in sgmodule_info:
    try:
        # 下载文件内容
        response = requests.get(info['url'])
        response.raise_for_status()
        
        # 匹配区块并提取内容
        content = response.text
        matches = section_pattern.findall(content)
        
        # 将内容按区块插入到相应部分
        for section, text in matches:
            if section in sections and section != "MITM":  # 排除 MITM，稍后处理
                if section == "Rules":
                    # 将 Rules 内容存储到 sections["Rules"] 列表中
                    sections["Rules"].append(text.strip())
                else:
                    divider = f"# ------------------------------------- {info['header']} --------------------------------------\n"
                    sections[section].append(f"{divider}\n{text.strip()}")
            elif section == "MITM":
                # 查找 hostname 行并提取主机名
                hostname_match = hostname_pattern.search(text)
                if hostname_match:
                    # 去掉每个 hostname 中的 %APPEND% 标记
                    hostnames = hostname_match.group(1).replace("%APPEND%", "").split(',')
                    sections["MITM"].extend([hostname.strip() for hostname in hostnames if hostname.strip()])
        
        print(f"成功合并: {info['header']}")
        
    except requests.exceptions.RequestException as e:
        print(f"无法下载 {info['header']} 文件: {e}")

# 保存 Rules 部分内容到 reject.list 文件
os.makedirs('Chores/ruleset', exist_ok=True)
with open('Chores/ruleset/reject.list', 'w') as ruleset_file:
    ruleset_file.write("\n".join(sections["Rules"]))
print("成功保存 [Rules] 内容到 Chores/ruleset/reject.list")

# 生成合并的 hostname 列表并格式化
unique_hostnames = list(dict.fromkeys(sections["MITM"]))  # 去重主机名
hostname_append_content = ", ".join(unique_hostnames)  # 合并后的 hostname 列表

# 获取当前日期并格式化为 mm/dd/yyyy
current_date = datetime.now().strftime("%m/%d/%Y")

# 读取模板文件
template_path = 'Chores/engineering/templates/All-in-One-2.x.sgmodule.template'
output_path = 'Chores/sgmodule/All-in-One-2.x.sgmodule'

with open(template_path, 'r') as template_file:
    template_content = template_file.read()

# 替换模板中的占位符
for section, contents in sections.items():
    placeholder = f"{{{section}}}"  # 例如 {URL Rewrite}
    if section == "MITM":
        section_content = contents  # 插入完整的 MITM 区块内容
    else:
        section_content = "\n\n".join(contents)  # 将其他区块内容合并成字符串
    template_content = template_content.replace(placeholder, str(section_content))

# 替换 `{hostname_append}` 占位符和 `{{currentDate}}`
template_content = template_content.replace("{hostname_append}", hostname_append_content)
template_content = template_content.replace("{{currentDate}}", current_date)

# 下载和替换 JS 链接
# (可选择的代码)

# 将合并内容写入输出文件
with open(output_path, 'w') as output_file:
    output_file.write(template_content)

print(f"文件已合并并保存为: {output_path}")
