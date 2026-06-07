# TagTranslate

TagTranslate 是一个用于生成 Stable Diffusion 提示词补全词表的小工具。项目主要用于获取 Danbooru 英文 tag 词表，并通过 NVIDIA API 调用大语言模型进行中文分类翻译，最终生成适用于 ComfyUI-Custom-Scripts 和 A1111 WebUI TagComplete 的提示词补全文件。

## 功能简介

本项目主要完成以下工作：

1. 从 Danbooru 获取最新英文 tag 及对应热度数量；
2. 调用 NVIDIA API 对英文 tag 进行中文翻译和分类；
3. 生成 ComfyUI-Custom-Scripts 可直接读取的 `autocomplete.txt`；
4. 将 ComfyUI 格式转换为 A1111 TagComplete 可用的主词表和中文翻译表；
5. 使用 `translation_cache.jsonl` 缓存已翻译内容，支持中断后继续运行。

## 项目文件说明

```text
TagTranslate/
├── .gitignore
├── get_tags.py
├── main.py
├── convert_to_a1111_tagcomplete.py
├── tags_input.csv
├── translation_cache.jsonl
├── autocomplete.txt
├── danbooru_custom.csv
└── danbooru_custom_zh.csv
```

### 文件作用

| 文件名                               | 说明                                                     |
| --------------------------------- | ------------------------------------------------------ |
| `get_tags.py`                     | 从 Danbooru 获取英文 tag 列表，生成 `tags_input.csv`             |
| `main.py`                         | 调用 NVIDIA API 翻译 tag，生成 ComfyUI 使用的 `autocomplete.txt` |
| `convert_to_a1111_tagcomplete.py` | 将 `autocomplete.txt` 转换为 A1111 TagComplete 可用格式        |
| `tags_input.csv`                  | 原始英文 tag 输入文件，格式为 `tag,count`                          |
| `translation_cache.jsonl`         | 翻译缓存文件，避免重复请求 API                                      |
| `autocomplete.txt`                | ComfyUI-Custom-Scripts 使用的补全词表                         |
| `danbooru_custom.csv`             | A1111 TagComplete 使用的英文主词表                             |
| `danbooru_custom_zh.csv`          | A1111 TagComplete 使用的中文翻译表                             |
| `.gitignore`                      | Git 忽略规则                                               |

## 环境要求

建议使用 Python 3.10 或更高版本。

需要安装以下依赖：

```bash
pip install openai tqdm requests
```

如果使用虚拟环境，可以执行：

```powershell
python -m venv .venv
.\.venv\Scripts\activate
pip install openai tqdm requests
```

## NVIDIA API Key 配置

项目通过 NVIDIA API 调用大语言模型进行翻译。运行前需要配置环境变量：

```powershell
[Environment]::SetEnvironmentVariable("NVIDIA_API_KEY", "你的API_KEY", "User")
```

设置后需要重新打开终端或重启 VS Code。

可以用下面命令检查是否读取成功：

```powershell
python -c "import os; print('OK' if os.getenv('NVIDIA_API_KEY') else 'NO KEY')"
```

显示 `OK` 即表示配置成功。

## 使用方法

### 1. 获取英文 tag 词表

运行：

```powershell
python get_tags.py
```

该脚本会生成：

```text
tags_input.csv
```

格式示例：

```csv
1girl,4114588
solo,3426446
highres,3008413
long_hair,2898315
```

其中第一列是英文 tag，第二列是该 tag 的热度数量。

### 2. 翻译 tag 并生成 ComfyUI 补全词表

运行：

```powershell
python main.py
```

脚本会读取：

```text
tags_input.csv
```

并生成：

```text
autocomplete.txt
```

输出格式示例：

```csv
1girl,1girl 人物-一个女孩,4114588
solo,solo 人物-单人,3426446
highres,highres 质量-高分辨率,3008413
long_hair,long_hair 发型-长发,2898315
```

该格式适用于 `ComfyUI-Custom-Scripts` 的自定义补全功能。

### 3. 在 ComfyUI 中使用

将生成的 `autocomplete.txt` 复制到：

```text
ComfyUI/custom_nodes/ComfyUI-Custom-Scripts/user/autocomplete.txt
```

然后重启 ComfyUI，并在浏览器中使用 `Ctrl + F5` 强制刷新页面。

之后在正负面提示词输入框中输入英文或中文关键词，即可出现补全候选。

例如输入：

```text
1gir
```

或：

```text
女孩
```

都可以匹配到：

```text
1girl 人物-一个女孩
```

点击后插入的是英文 tag：

```text
1girl
```

## 转换为 A1111 TagComplete 格式

A1111 WebUI 的 `a1111-sd-webui-tagcomplete` 插件不能直接读取本项目生成的 `autocomplete.txt`，需要转换为主词表和翻译表。

运行：

```powershell
python convert_to_a1111_tagcomplete.py
```

会生成：

```text
danbooru_custom.csv
danbooru_custom_zh.csv
```

其中：

```text
danbooru_custom.csv
```

是 A1111 TagComplete 使用的英文主词表，格式类似：

```csv
1girl,0,4114588,""
solo,0,3426446,""
highres,0,3008413,""
```

```text
danbooru_custom_zh.csv
```

是中文翻译表，格式类似：

```csv
1girl,人物-一个女孩
solo,人物-单人
highres,质量-高分辨率
```

将这两个文件放入：

```text
stable-diffusion-webui/extensions/a1111-sd-webui-tagcomplete/tags/
```

然后在 WebUI 中进入：

```text
Settings → Tag Autocomplete
```

设置对应的 tag 文件和 translation 文件即可。

## 缓存与断点续跑

`main.py` 会使用：

```text
translation_cache.jsonl
```

保存已经翻译过的 tag。重新运行脚本时，程序会自动跳过缓存中已有的 tag，只翻译缺失部分。

因此，如果运行过程中手动按下：

```text
Ctrl + C
```

中断程序，下次重新运行时仍然可以继续翻译，不需要从头开始。

判断逻辑如下：

```text
tags_input.csv 中存在
但 translation_cache.jsonl 中不存在
→ 需要继续翻译

translation_cache.jsonl 中已经存在
→ 跳过，不重复请求 API
```

## 输出顺序说明

最终生成的 `autocomplete.txt` 会按照 `tags_input.csv` 的原始顺序输出。

即使 `translation_cache.jsonl` 因为多次运行导致缓存顺序不连续，也不会影响最终输出顺序。

## 失败批次说明

如果翻译请求失败，脚本可能会生成：

```text
failed_batches.jsonl
```

该文件只用于记录失败日志，不会直接影响主流程。

重新运行脚本时，程序仍然以 `translation_cache.jsonl` 为准：只要失败的 tag 没有进入缓存，下次运行就会重新翻译。

## 常用配置

可以在 `main.py` 中调整以下参数：

```python
MODEL = "qwen/qwen3.5-397b-a17b"
BATCH_SIZE = 20
MAX_WORKERS = 3
```

含义如下：

| 参数            | 说明                |
| ------------- | ----------------- |
| `MODEL`       | 使用的 NVIDIA API 模型 |
| `BATCH_SIZE`  | 每次请求翻译的 tag 数量    |
| `MAX_WORKERS` | 同时发送的 API 请求数量    |

如果经常出现 JSON 解析失败或请求超时，可以适当降低：

```python
BATCH_SIZE = 10
MAX_WORKERS = 1
```

如果运行稳定，可以提高并发数，但过高可能触发限流。

## 注意事项

1. 不要把 NVIDIA API Key 写入代码文件；
2. 不建议将 `translation_cache.jsonl` 删除，否则会导致已经翻译过的 tag 重新请求 API；
3. 如果修改了某个 tag 的错误翻译，需要手动删除 `translation_cache.jsonl` 中对应行，或者在 `main.py` 的 `MANUAL_OVERRIDES` 中添加手动覆盖；
4. `autocomplete.txt` 适用于 ComfyUI-Custom-Scripts；
5. `danbooru_custom.csv` 和 `danbooru_custom_zh.csv` 适用于 A1111 TagComplete。

## 推荐工作流

完整流程如下：

```powershell
python get_tags.py
python main.py
python convert_to_a1111_tagcomplete.py
```

然后：

* ComfyUI 用户使用 `autocomplete.txt`
* A1111 WebUI 用户使用 `danbooru_custom.csv` 和 `danbooru_custom_zh.csv`
