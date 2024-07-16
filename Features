# Ollama-Image-Tags

## 📢 介绍 Introduction

欢迎使用 **Ollama-Image-Tags**，一个强大且灵活的图像打标工具，旨在帮助Stable Diffusion模型的炼丹师们高效地为大量图片进行批量打标和处理。这个工具利用Ollama的图像识别模型，通过多种方式对图像进行反推和润色，确保打标结果的准确性和格式的正确性。

Welcome to **Ollama-Image-Tags**, a powerful and flexible image tagging tool designed to help Stable Diffusion model enthusiasts efficiently batch tag and process large volumes of images. This tool leverages Ollama's image recognition models to reverse-engineer and refine images in various ways, ensuring the accuracy and proper formatting of tagging results.

## ✨ 功能说明 Features

### 1. 单图处理 Single Image Processing

使用Ollama的图像识别模型对单张图片进行反推打标。用户可以选择模型、输入Prompt，并上传图片，工具将返回处理结果。

Use Ollama's image recognition model to reverse-engineer and tag a single image. Users can select a model, input a prompt, and upload an image, and the tool will return the processed result.

### 2. 单图处理PLUS Single Image Processing PLUS

在单图处理的基础上，增加了双模型推理功能。初步打标后，可以选择启用精炼模型对结果进行进一步处理和润色，提升标签的准确性和格式的正确性。

In addition to single image processing, this feature adds dual-model inference. After initial tagging, you can choose to enable a refinement model to further process and refine the results, enhancing the accuracy and proper formatting of tags.

### 3. 多图处理 Batch Image Processing

支持对文件夹内的多张图片进行批量打标。用户可以选择打标方式（忽略、覆盖、加入前面、加入后面），并发数量和硬件配置（GPU/CPU）。工具将遍历文件夹中的图片，按设定方式进行打标并保存结果。

Supports batch tagging of multiple images within a folder. Users can select the tagging method (ignore, overwrite, prepend, append), concurrency, and hardware configuration (GPU/CPU). The tool will traverse the folder and tag images as per the settings, saving the results accordingly.

### 4. 多图处理PLUS Batch Image Processing PLUS

在多图处理的基础上，增加了双模型推理功能。初步打标后，可以选择启用精炼模型对结果进行进一步处理和润色，提升标签的准确性和格式的正确性。

In addition to batch image processing, this feature adds dual-model inference. After initial tagging, you can choose to enable a refinement model to further process and refine the results, enhancing the accuracy and proper formatting of tags.

### 5. AI-Multi-Tag

支持使用多组AI图像大模型对图像进行识别，再用语言模型对结果进行处理。可以显著增强对图像的识别丰富度，但也会影响识别速度。用户可以选择启用的模型组，并设置打标方式和硬件配置。

Supports using multiple sets of AI image models to recognize images, followed by a language model to process the results. This significantly enhances the richness of image recognition but may affect processing speed. Users can choose the enabled model sets and configure tagging methods and hardware.

### 6. 文字处理 Text Processing

提供了多种文字处理功能，包括：
- 添加文字：在TXT文件中插入指定文字（前面或后面）。
- 文字替换：查找并替换TXT文件中的指定文字。
- 删除文件：根据包含的文字删除TXT文件或其同名图片。
- 转移文件：将符合条件的TXT文件或其同名图片转移到指定文件夹。

Provides various text processing functions, including:
- Add Text: Insert specified text into TXT files (at the front or end).
- Replace Text: Find and replace specified text in TXT files.
- Delete Files: Delete TXT files or their corresponding images based on contained text.
- Move Files: Move qualifying TXT files or their corresponding images to a specified folder.

### 7. 打标后AI润色 Post-Tagging AI Refinement

对已有标签的图片，通过通用AI模型对其标签文字进行重新润色处理或二次加工。用户可以输入文件夹地址，系统将遍历该文件夹及其子文件夹中的图片文件和TXT文件，对包含TXT文件的图片进行处理。

For images with existing tags, this feature uses a general AI model to refine or reprocess the tag text. Users can input a folder path, and the system will traverse the folder and its subfolders, processing images with corresponding TXT files.

## 📚 使用说明 User Guide

### 1. 安装 Installation

首先，确保您已经安装了所有必要的依赖项。您可以使用以下命令安装所需的Python库：

First, ensure you have installed all necessary dependencies. You can install the required Python libraries using the following command:

```bash
pip install -r requirements.txt
```

### 2. 启动服务 Start the Service

启动Ollama服务，并确保其在运行状态。然后，运行以下命令启动Gradio界面：

Start the Ollama service and ensure it is running. Then, run the following command to start the Gradio interface:

```bash
python ollama_interface.py
```

### 3. 使用界面 Using the Interface

打开浏览器，访问 `http://localhost:7888`，您将看到Ollama-Image-Tags的用户界面。

Open your browser and visit `http://localhost:7888`, where you will see the Ollama-Image-Tags user interface.

### 4. 单图处理 Single Image Processing

1. 选择模型。
2. 输入Prompt。
3. 上传图片。
4. 点击“执行”按钮，查看处理结果。

1. Select a model.
2. Enter a prompt.
3. Upload an image.
4. Click the "Execute" button to see the processing result.

### 5. 多图处理 Batch Image Processing

1. 选择模型。
2. 输入Prompt。
3. 输入文件夹路径。
4. 选择打标方式（忽略、覆盖、加入前面、加入后面）。
5. 选择硬件配置（GPU/CPU）。
6. 设置并发数量。
7. 点击“执行”按钮，查看处理结果。

1. Select a model.
2. Enter a prompt.
3. Enter the folder path.
4. Choose the tagging method (ignore, overwrite, prepend, append).
5. Select hardware configuration (GPU/CPU).
6. Set concurrency.
7. Click the "Execute" button to see the processing result.

### 6. 文字处理 Text Processing

1. 输入TXT文件夹路径。
2. 根据需要选择添加文字、文字替换、删除文件或转移文件功能。
3. 输入相关参数。
4. 点击相应的按钮执行操作。

1. Enter the TXT folder path.
2. Choose the desired function: Add Text, Replace Text, Delete Files, or Move Files.
3. Enter the relevant parameters.
4. Click the corresponding button to execute the operation.

### 7. 打标后AI润色 Post-Tagging AI Refinement

1. 选择模型。
2. 输入Prompt 1。
3. 输入文件夹路径。
4. 选择打标方式（忽略、覆盖、加入前面、加入后面）。
5. 选择硬件配置（GPU/CPU）。
6. 输入Prompt 2。
7. 点击“执行”按钮，查看处理结果。

1. Select a model.
2. Enter Prompt 1.
3. Enter the folder path.
4. Choose the tagging method (ignore, overwrite, prepend, append).
5. Select hardware configuration (GPU/CPU).
6. Enter Prompt 2.
7. Click the "Execute" button to see the processing result.

## 🌟 可能的使用场景 Potential Use Cases

- **Stable Diffusion模型训练 Stable Diffusion Model Training**：为大量图片进行高效、准确的批量打标，提升模型训练效果。
- **图像数据集管理 Image Dataset Management**：对图像数据集进行分类和标签管理，方便后续的数据处理和分析。
- **图像识别和分析 Image Recognition and Analysis**：利用多组AI模型对图像进行深度识别和分析，获取更丰富的标签信息。

## 📝 结语 Conclusion

我们诚挚地希望 **Ollama-Image-Tags** 能够帮助到每一位炼丹师，让大家在Stable Diffusion模型的训练和图像处理过程中更加高效和便捷。如果您有任何建议或反馈，欢迎随时与我们联系。感谢大家的支持，让我们一起让这个工具变得更加完善和强大！

We sincerely hope that **Ollama-Image-Tags** can assist every model enthusiast, making the training of Stable Diffusion models and image processing more efficient and convenient. If you have any suggestions or feedback, please feel free to contact us. Thank you for your support, and let's make this tool even more perfect and powerful together!

[GitHub仓库链接 GitHub Repository Link](https://github.com/your-repo/ollama-image-tags)
