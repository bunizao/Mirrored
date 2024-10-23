import os
import re
import requests
import json
from datetime import datetime
from urllib.parse import quote

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

# 生成合并链接
base_url = 'https://script-hub.tutuis.me/file/_start_/'
end_url = '/_end_/Zhihu_remove_ads.sgmodule?type=surge-module&target=surge-module&del=true'
separator = '😂'

# 提取 URL 列表
module_urls = [module['url'] for module in sgmodule_info]

# 将 URL 使用分隔符连接
combined_urls = separator.join(module_urls)

# 对合并的 URL 进行编码
encoded_combined_urls = quote(combined_urls, safe=':/')

# 构建最终的合并链接
combined_link = f"{base_url}{encoded_combined_urls}{end_url}"

print(f"生成的合并链接：\n{combined_link}")

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
    print(f'正在下载 {url}')
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
        print(f'下载失败 {url}')

# 从合并链接中获取 [MITM] 部分
response = requests.get(combined_link)
if response.status_code == 200:
    content = response.text
    # 提取 [MITM] 部分
    mitm_pattern = re.compile(r'\[MITM\]\n((?:.|\n)*?)(?=\n\[|$)')
    mitm_match = mitm_pattern.search(content)
    if mitm_match:
        mitm_content = mitm_match.group(1).strip()
        # 将 MITM 主机名列表转换为列表，并去除空行
        mitm_hosts = [line.strip() for line in mitm_content.split(',') if line.strip()]
        # 去重处理
        mitm_hosts = list(dict.fromkeys(mitm_hosts))
        # 添加到 merged_sections
        merged_sections['MITM'] = mitm_hosts
    else:
        print('未找到 [MITM] 部分')
else:
    print('无法获取合并链接的内容')

# 去重处理（可选，根据需要）
for section in merged_sections:
    if section != 'MITM':
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
output_file = 'Chores/engineering/data/sgmodules_data.json'
os.makedirs(os.path.dirname(output_file), exist_ok=True)
with open(output_file, 'w', encoding='utf-8') as f:
    json.dump(template_data, f, ensure_ascii=False, indent=2)

print(f'数据已保存到 {output_file}')
