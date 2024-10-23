import os
import re
import requests
import json
from datetime import datetime

# 配置要下载的 .sgmodule 文件的 URL 列表和对应的模块标识（用于注释）
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
    },
    # 可以在这里添加更多的模块信息
]

# 定义要提取的部分
sections_to_extract = ['URL Rewrite', 'Script', 'Map Local']

# 获取当前日期，格式为 MM/DD/YYYY
current_date = datetime.now().strftime('%m/%d/%Y')

# 存储合并的部分内容
merged_sections = {section: [] for section in sections_to_extract}

# 下载并解析每个 .sgmodule 文件
for module in sgmodule_info:
    url = module['url']
    header = module['header']
    print(f'Downloading {url}')
    response = requests.get(url)
    if response.status_code == 200:
        content = response.text

        # 提取指定的部分
        pattern = re.compile(r'\[(.*?)\]\n((?:.|\n)*?)(?=\n\[|$)')
        matches = pattern.findall(content)

        for section_name, section_body in matches:
            section_name = section_name.strip()
            if section_name in sections_to_extract:
                lines = section_body.strip().split('\n')
                # 在合并的部分中添加模块来源的注释
                merged_sections[section_name].append(f'# -------------------------------------- {header} --------------------------------------')
                merged_sections[section_name].extend(lines)
                merged_sections[section_name].append('')  # 添加空行，便于阅读
    else:
        print(f'Failed to download {url}')

# 去重处理（可选，根据需要）
for section in merged_sections:
    # 去除空字符串
    merged_sections[section] = [line for line in merged_sections[section] if line.strip() != '']
    # 去重并保持顺序
    seen = set()
    unique_lines = []
    for line in merged_sections[section]:
        if line not in seen:
            seen.add(line)
            unique_lines.append(line)
    merged_sections[section] = unique_lines

# 准备传递给模板的数据
template_data = {
    'currentDate': current_date,
    'mergedSections': merged_sections
}

# 将数据写入 JSON 文件
output_file = 'data/sgmodules_data.json'
os.makedirs(os.path.dirname(output_file), exist_ok=True)
with open(output_file, 'w', encoding='utf-8') as f:
    json.dump(template_data, f, ensure_ascii=False, indent=2)

print(f'Data has been saved to {output_file}')
