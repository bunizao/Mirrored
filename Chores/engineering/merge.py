import requests
import re
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
    "MITM": []  # 将所有的 hostname 收集到这里
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

# 生成合并的 hostname 列表并格式化
unique_hostnames = list(dict.fromkeys(sections["MITM"]))  # 去重主机名
hostname_append_content = ", ".join(unique_hostnames)  # 合并后的 hostname 列表

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

# 替换 `{hostname_append}` 占位符
template_content = template_content.replace("{hostname_append}", hostname_append_content)

# 将合并内容写入输出文件
with open(output_path, 'w') as output_file:
    output_file.write(template_content)

print(f"文件已合并并保存为: {output_path}")
