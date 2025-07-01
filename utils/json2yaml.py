# import json
# import yaml
# import os
# from pathlib import Path
# import copy

# # 保持列表在 YAML 中一行输出
# class SingleLineListDumper(yaml.SafeDumper):
#     pass

# def represent_list_as_single_line(dumper, data):
#     return dumper.represent_sequence('tag:yaml.org,2002:seq', data, flow_style=True)

# yaml.add_representer(list, represent_list_as_single_line, Dumper=SingleLineListDumper)

# # === 配置 ===
# source_dir = Path("utils/ss01/")     # 替换成你的源 JSON 文件夹路径
# dest_dir = Path("src/application/config/machines/")    # 替换成你的目标输出 YAML 文件夹路径
# template_yaml_path = Path("utils/ss01/cus_machine_1.yaml")  # 模板 YAML 文件

# # 创建目标目录
# dest_dir.mkdir(parents=True, exist_ok=True)

# # 读取模板 YAML
# with open(template_yaml_path, "r") as f:
#     template_yaml = yaml.safe_load(f)

# # 遍历 JSON 文件夹
# for json_file in source_dir.glob("*.json"):
#     try:
#         with open(json_file, "r") as jf:
#             json_data = json.load(jf)

#         game_id = json_data.get("id", json_file.stem)
#         base_reels = json_data["data"]["base"]
#         free_reels = json_data["data"]["free"]

#         if not (len(base_reels) == 5 and len(free_reels) == 5):
#             raise ValueError("base/free reels count not equal to 5")

#         # 构建新 YAML 数据
#         new_yaml = copy.deepcopy(template_yaml)
#         new_yaml["machine_id"] = game_id
#         new_yaml["reels"]["normal"] = {
#             f"reel{i+1}": base_reels[i]["reel"] for i in range(5)
#         }
#         new_yaml["reels"]["bonus"] = {
#             f"reel{i+1}": free_reels[i]["reel"] for i in range(5)
#         }

#         # 保存 YAML 文件
#         output_path = dest_dir / f"{game_id}.yaml"
#         with open(output_path, "w") as outf:
#             yaml.dump(new_yaml, outf, width=float('inf'), Dumper=SingleLineListDumper, sort_keys=False, allow_unicode=True)

#         print(f"[OK] Converted: {json_file.name} -> {output_path.name}")

#     except Exception as e:
#         print(f"[ERROR] Skipped {json_file.name}: {e}")


import json
import re
from pathlib import Path

def format_reels(reels: list, label: str) -> str:
    lines = [f"  {label}:"]
    for i in range(5):
        line = f"    reel{i+1}: {reels[i]['reel']}"
        lines.append(line)
    return "\n".join(lines)

source_dir = Path("utils/ss01/")
dest_dir = Path("src/application/config/machines/")
template_path = source_dir / "cus_machine_1.yaml"

dest_dir.mkdir(parents=True, exist_ok=True)

template_text = template_path.read_text(encoding="utf-8")

for json_file in source_dir.glob("*.json"):
    try:
        json_data = json.loads(json_file.read_text(encoding="utf-8"))
        game_id = json_data["id"]
        base = json_data["data"]["base"]
        free = json_data["data"]["free"]

        # 构建新的 reels 替换段
        new_reels = f"reels:\n{format_reels(base, 'normal')}\n{format_reels(free, 'bonus')}"

        # 正则找 reels 区域
        replaced_text = re.sub(
            r"reels:\n(?:  .+\n)+?(?=^[^\s])",  # reels:\n 后跟任意缩进行，直到下一个非缩进顶格字段
            new_reels + "\n",
            template_text,
            flags=re.MULTILINE
        )

        # 替换 machine_id
        replaced_text = re.sub(
            r'^machine_id:.*',
            f'machine_id: "{game_id}"',
            replaced_text,
            flags=re.MULTILINE
        )

        output_file = dest_dir / f"{game_id}.yaml"
        output_file.write_text(replaced_text, encoding="utf-8")
        print(f"[OK] {json_file.name} -> {output_file.name}")

    except Exception as e:
        print(f"[ERROR] {json_file.name}: {e}")

