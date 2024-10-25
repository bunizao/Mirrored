import requests
import re
from urllib.parse import quote
import os

# 定义 URL 和 header 别名信息
sgmodule_info = [
    {
        'url': 'https://github.com/bunizao/Mirrored/raw/main/Chores/sgmodule/Zhihu_remove_ads.sgmodule',
        'header': 'Zhihu'
    },
    {
        'url': 'https://github.com/bunizao/Mirrored/raw/main/Chores/sgmodule/Amap_remove_ads.sgmodule',
        'header': 'Amap'
    },
    {
        'url': 'https://github.com/bunizao/Mirrored/raw/main/Chores/sgmodule/Weibo_remove_ads.sgmodule',
        'header': 'Weibo'
    },
    {
        'url': 'https://github.com/bunizao/Mirrored/raw/main/Chores/sgmodule/Tieba_remove_ads.sgmodule',
        'header': 'Tieba'
    },
    {
        'url': 'https://github.com/bunizao/Mirrored/raw/main/Chores/sgmodule/PinDuoDuo_remove_ads.sgmodule',
        'header': 'PinDuoDuo'
    },
    {
        'url': 'https://github.com/bunizao/Mirrored/raw/main/Chores/sgmodule/JD_remove_ads.sgmodule',
        'header': 'JD'
    }
]

# 定义区块
sections = {
    "URL Rewrite": [],
    "Map Local": [],
    "Script": [],
    "MITM": ""  # 将 MITM 部分直接作为一个完整的字符串存储
}

# 定义正则表达式来匹配区块内容
section_pattern = re.compile(r'\[(.*?)\]\n(.*?)(?=\n\[|$)', re.DOTALL)

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
                divider = f"# ------------------------------------- {info['header']} --------------------------------------"
                sections[section].append(f"{divider}\n{text.strip()}")
        
        print(f"成功合并: {info['header']}")
        
    except requests.exceptions.RequestException as e:
        print(f"无法下载 {info['header']} 文件: {e}")

# 生成合并链接
base_url = 'https://script-hub.tutuis.me/file/_start_/'
end_url = '/_end_/Zhihu_remove_ads.sgmodule?type=surge-module&target=surge-module&del=true'
separator = '😂'

# 提取 URL 列表并编码为合并链接
module_urls = [module['url'] for module in sgmodule_info]
combined_urls = separator.join(module_urls)
encoded_combined_urls = quote(combined_urls, safe=':/')
combined_link = f"{base_url}{encoded_combined_urls}{end_url}"

# 从合并链接中获取 [MITM] 部分
try:
    response = requests.get(combined_link)
    response.raise_for_status()
    
    # 匹配 [MITM] 部分内容
    content = response.text
    mitm_pattern = re.compile(r'\[MITM\]\n((?:.|\n)*?)(?=\n\[|$)')
    mitm_match = mitm_pattern.search(content)
    
    if mitm_match:
        # 将完整的 [MITM] 内容直接存入 sections["MITM"]
        sections["MITM"] = "[MITM]\n" + mitm_match.group(1).strip()
        print("成功提取 [MITM] 部分")
    else:
        print('未找到 [MITM] 部分')
        
except requests.exceptions.RequestException as e:
    print(f"无法获取合并链接的内容: {e}")

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
        section_content = "\n\n".join(contents)  # 其他区块内容合并为字符串
    template_content = template_content.replace(placeholder, section_content)

# 将合并内容写入输出文件
with open(output_path, 'w') as output_file:
    output_file.write(template_content)

print(f"文件已合并并保存为: {output_path}")
