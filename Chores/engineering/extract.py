import os
import re
import requests
import json

# 配置要下载的 .sgmodule 文件的 URL 列表
sgmodule_urls = [
    'https://raw.githubusercontent.com/bunizao/Mirrored/main/Chores/sgmodule/Zhihu_remove_ads.sgmodule',

]

# 定义要提取的部分
sections = ['URL Rewrite', 'Map Local', 'Script', 'Rule', 'Host', 'Header Rewrite']

# 存储所有模块的数据
modules_data = []

# 下载并解析每个 .sgmodule 文件
for url in sgmodule_urls:
    print(f'Downloading {url}')
    response = requests.get(url)
    if response.status_code == 200:
        content = response.text

        module_info = {
            'url': url,
            'name': '',
            'desc': '',
            'sections': {}
        }

        # 提取模块元信息（如 #!name, #!desc）
        name_match = re.search(r'^#!name=(.*)$', content, re.MULTILINE)
        desc_match = re.search(r'^#!desc=(.*)$', content, re.MULTILINE)
        if name_match:
            module_info['name'] = name_match.group(1).strip()
        if desc_match:
            module_info['desc'] = desc_match.group(1).strip()

        # 按部分拆分
        pattern = re.compile(r'\[(.*?)\]\n((?:.|\n)*?)(?=\n\[|$)')
        matches = pattern.findall(content)

        for section_name, section_content in matches:
            section_name = section_name.strip()
            if section_name in sections:
                lines = section_content.strip().split('\n')
                module_info['sections'][section_name] = lines

        modules_data.append(module_info)
    else:
        print(f'Failed to download {url}')

# 将数据写入 JSON 文件
output_file = 'data/sgmodules_data.json'
os.makedirs(os.path.dirname(output_file), exist_ok=True)
with open(output_file, 'w', encoding='utf-8') as f:
    json.dump(modules_data, f, ensure_ascii=False, indent=2)

print(f'Data has been saved to {output_file}')
