import requests
import re
import os
from datetime import datetime
import yaml

with open('Chores/engineering/data/adb-sgmodules.yaml', 'r') as f:
    sgmodule_info = yaml.safe_load(f)

sections = {
    "URL Rewrite": [],
    "Map Local": [],
    "Script": [],
    "MITM": [],
    "Rule": []
}

section_pattern = re.compile(r'\[(.*?)\]\s*\n(.*?)(?=\n\[|$)', re.DOTALL)
hostname_pattern = re.compile(r'hostname\s*=\s*(.*)', re.IGNORECASE)
headers = []

max_divider_length = 30

for info in sgmodule_info:
    try:
        response = requests.get(info['url'])
        response.raise_for_status()
        
        content = response.text
        print(f"[Debug] Parsing content from {info['header']}")
        matches = section_pattern.findall(content)
        
        headers.append(info['header'])
        
        # 计算动态分隔线
        left_dash_count = (max_divider_length - len(info['header'])) // 2
        right_dash_count = max_divider_length - len(info['header']) - left_dash_count
        divider = f"# {'-' * left_dash_count} {info['header']} {'-' * right_dash_count}"
        
        for section, text in matches:
            if section in sections and section != "MITM":
                if section == "Rule":
                    cleaned_text = re.sub(r'(?:,\s*|-\s*)(REJECT(?:-(?:DROP|TINYGIF|NO-DROP))?|DIRECT)\b', '', text, flags=re.I).strip()
                    sections["Rule"].append(cleaned_text)
                    print(f"[Debug] Added cleaned Rule content from {info['header']}: {cleaned_text}")
                else:
                    # 删除内容中的注释行和空行，但保留 divider
                    cleaned_lines = "\n".join(
                        line for line in text.strip().splitlines() 
                        if line.strip() and not line.strip().startswith("#")
                    )
                    sections[section].append(f"{divider}\n{cleaned_lines}")
            elif section == "MITM":
                hostname_match = hostname_pattern.search(text)
                if hostname_match:
                    hostnames = hostname_match.group(1).replace("%APPEND%", "").split(',')
                    sections["MITM"].extend([hostname.strip() for hostname in hostnames if hostname.strip()])
        
        print(f"Successfully merged: {info['header']}")
        
    except requests.exceptions.RequestException as e:
        print(f"Failed to download {info['header']} file: {e}")

headers_combined = ", ".join(headers)

if sections["Rule"]:
    print(f"[Debug] Total Rule content to be saved: {len(sections['Rule'])} lines")
else:
    print("[Warning] No Rule content extracted")

os.makedirs('Chores/ruleset', exist_ok=True)
with open('Chores/ruleset/reject.list', 'w') as ruleset_file:
    ruleset_file.write("\n".join(sections["Rule"]))
print("Successfully saved [Rule] content to Chores/ruleset/reject.list")

unique_hostnames = list(dict.fromkeys(sections["MITM"]))
hostname_append_content = ", ".join(unique_hostnames)

current_date = datetime.now().strftime("%m/%d/%Y")

template_path = 'Chores/engineering/templates/All-in-One-2.x.sgmodule.template'
output_path = 'Chores/sgmodule/All-in-One-2.x.sgmodule'

with open(template_path, 'r') as template_file:
    template_content = template_file.read()

for section, contents in sections.items():
    placeholder = f"{{{section}}}"
    section_content = "\n\n".join(contents) if section != "MITM" else contents
    template_content = template_content.replace(placeholder, str(section_content))

template_content = template_content.replace("{headers}", headers_combined)
template_content = template_content.replace("{hostname_append}", hostname_append_content)
template_content = template_content.replace("{{currentDate}}", current_date)

with open(output_path, 'w') as output_file:
    output_file.write(template_content)

print(f"File successfully merged and saved to: {output_path}")
