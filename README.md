# ollama-Image-tags
# 麻瓜打标器

欢迎来到ollama-Image-tags项目！🎉

## 项目简介

ollama-Image-tags 是一个利用 Ollama 模型为图像打标的工具，专为那些需要为大量图片进行批量打标和处理的炼丹师们设计。无论你是为了 Stable Diffusion 模型进行 DreamBooth 微调，还是 Lora 训练，这个工具都能大大提升你的工作效率。

## 百度网盘
链接：https://pan.baidu.com/s/14GeXObLmLGA6g3AsPCBTkw?pwd=AIDV 
提取码：AIDV 
--来自百度网盘超级会员V7的分享



## 项目背景

作为一个完全不会写代码的初学者，我第一次尝试用 AI 搓了一个功能比较完整的提示词反推助手。起因是兔狲大佬的打标工具，用 GPT-4 打标非常心痛，免费的模型又只有几个，开源模型效果也差强人意。每次打标完成的结果，由于开源模型的本身能力问题，总是出现各种各样的问题，直接影响到 SD 模型训练的结果。

自己下载几万张图片也没有这么多时间一张一张手搓提示词，就一直想用 Ollama 的模型来帮我进行反推。直到最近开始尝试用 GPT 来写代码，研究了一整天，终于到晚上有了一个基础可以运行的框架，我才再一次感受到 AI 的强大。

之后的几天，我就每次提一个需求，让 AI 来进行优化和修改代码，确保每次都可以正常运行后，才开始提下一个需求。直到现在的版本，他已经可以做到以下几个功能：

## 功能介绍
### 视频教程：
https://www.bilibili.com/video/BV1MP8MeMEbB/

1. **使用 Ollama 的任何图像识别模型进行反推**：无论你选择哪种 Ollama 模型，都可以轻松实现图像打标。

![image](https://github.com/user-attachments/assets/195ac2cf-8246-423f-9f86-2af26bbaf856)

2. **双模型推理工具**：为了保证结果的标签的准确性和格式正确性，我加入了双模型推理工具——多图处理 Plus。可以通过图像识别模型进行初步打标，再用其他的语言模型，对其结果进行处理和润色。
![image](https://github.com/user-attachments/assets/1cb2e6b0-f19e-4509-ae1a-f876ddaf864c)

3. **Multi-Tag 工具**：为了保证识别足够的丰富，我加入了 Multi-Tag 工具，可以使用 4 组 AI 图像大模型，对图像进行识别，再用一个语言模型来对结果进行处理。可以大幅度增强对图像的识别丰富度，但也会影响识别速度。
![image](https://github.com/user-attachments/assets/c6339bce-8e14-450f-a806-00fd1332a736)

## 如何使用
###视频地址：
https://www.bilibili.com/video/BV1YR8Te5EJp/?spm_id_from=333.999.0.0

1. 克隆本仓库到本地：
    ```bash
    git clone https://github.com/EasonYinY/ollama-Image-tags.git
    ```
2. 安装所需依赖：
    安装Ollama 及 模型，推荐LLava
    安装python3.10
    使用以下命令安装所需的Python库：
    pip install -r requirements.txt
3. 运行install_and_run.bat

## 测试：
![image](https://github.com/user-attachments/assets/300da54e-1088-4fdb-a767-b956ae2eacfd)


## 贡献指南

我们非常欢迎任何形式的贡献！无论是代码改进、功能建议还是 Bug 报告，都可以通过提交 Issue 或 Pull Request 的方式告诉我们。
（但是我也是第一次用GitHub，我估计都不知道怎么操作。）

## 支持与反馈

如果你在使用过程中遇到任何问题，或者有任何建议，请随时通过 GitHub Issue 联系我们。我会尽快回复并解决你的问题。（不一定，因为我不懂代码，只能用AI来调试）

## 结语

感谢大家的支持！希望 ollama-Image-tags 能够帮助到你们。如果你觉得这个项目对你有帮助，请不要忘记给我们一个 ⭐️ Star！你的支持是我们前进的最大动力！

一起让图像打标变得更加简单、高效！💪

---

**作者**: Eason
