import gradio as gr
import requests
import os
import base64
import csv
from datetime import datetime

# OLLAMA API URL
OLLAMA_API_URL = "http://localhost:11434/api"

# 获取本地模型列表
def get_models():
    try:
        response = requests.get(f"{OLLAMA_API_URL}/tags")
        response.raise_for_status()
        models = response.json().get("models", [])
        return [model["name"] for model in models]
    except requests.RequestException as e:
        print(f"Error fetching models: {e}")
        return []

# 获取Prompt模板列表
def get_prompt_templates():
    templates = []
    try:
        with open("prompt_templates.csv", "r") as file:
            reader = csv.reader(file)
            templates = [row[0] for row in reader]
    except FileNotFoundError:
        print("prompt_templates.csv 文件未找到")
    return templates

# 保存历史记录prompt
def save_prompt(prompt1, prompt2, model, source):
    file_exists = os.path.isfile("history_prompts.csv")
    with open("history_prompts.csv", "a", newline='') as file:
        writer = csv.writer(file)
        if not file_exists:
            writer.writerow(["日期", "模型", "来源", "Prompt 1", "Prompt 2"])
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        writer.writerow([now, model, source, prompt1, prompt2])

# 处理单张图片
def process_single_image(model, prompt, image):
    if not model:
        return "请选择一个模型。"

    image_path = image

    with open(image_path, "rb") as img_file:
        img_base64 = base64.b64encode(img_file.read()).decode('utf-8')

    payload = {
        "model": model,
        "prompt": prompt,
        "images": [img_base64],
        "stream": False
    }

    try:
        print(f"Sending request to {OLLAMA_API_URL}/generate with payload: {payload}")
        response = requests.post(f"{OLLAMA_API_URL}/generate", json=payload)
        response.raise_for_status()
        result = response.json().get("response", "")
        print(f"Received response: {result}")
        return f"打标结果: {result}"
    except requests.RequestException as e:
        print(f"Error processing image: {e}")
        return "处理失败，请检查API连接。"

# 处理单张图片PLUS
def process_single_image_plus(model, prompt1, prompt2, image):
    if not model:
        return "请选择一个模型。", ""

    result1 = process_single_image(model, prompt1, image)
    combined_prompt = f"{prompt2}\n{result1}"

    payload = {
        "model": model,
        "prompt": combined_prompt,
        "stream": False
    }

    try:
        print(f"Sending request to {OLLAMA_API_URL}/generate with payload: {payload}")
        response = requests.post(f"{OLLAMA_API_URL}/generate", json=payload)
        response.raise_for_status()
        result2 = response.json().get("response", "")
        print(f"Received response: {result2}")
        return result1, f"打标结果: {result2}"
    except requests.RequestException as e:
        print(f"Error processing image: {e}")
        return "处理失败，请检查API连接。", ""

# 处理文件夹中的所有图片
def process_folder(model, prompt, folder_path, action):
    if not model:
        return "请选择一个模型。"

    if not os.path.isdir(folder_path):
        return "无效的文件夹路径。"

    results = []
    files = []
    for root, _, filenames in os.walk(folder_path):
        files.extend([os.path.join(root, f) for f in filenames if f.lower().endswith(('.png', '.jpg', '.jpeg', '.bmp', '.gif'))])
    total_files = len(files)

    for idx, file in enumerate(files):
        txt_path = os.path.join(os.path.dirname(file), f"{os.path.splitext(os.path.basename(file))[0]}.txt")
        if os.path.exists(txt_path) and action == "忽略":
            results.append(f"{file}: 文件已存在，选择忽略。")
            continue  # 跳过此文件的处理

        result = process_single_image_with_save(model, prompt, file, action)
        results.append(result)

    return "\n".join(results)

# 处理单张图片并保存结果
def process_single_image_with_save(model, prompt, image, action):
    if not model:
        return "请选择一个模型。"

    image_path = image
    image_dir = os.path.dirname(image_path)
    image_name = os.path.basename(image_path)
    txt_path = os.path.join(image_dir, f"{os.path.splitext(image_name)[0]}.txt")

    with open(image_path, "rb") as img_file:
        img_base64 = base64.b64encode(img_file.read()).decode('utf-8')

    payload = {
        "model": model,
        "prompt": prompt,
        "images": [img_base64],
        "stream": False
    }

    try:
        print(f"Sending request to {OLLAMA_API_URL}/generate with payload: {payload}")
        response = requests.post(f"{OLLAMA_API_URL}/generate", json=payload)
        response.raise_for_status()
        result = response.json().get("response", "")
        print(f"Received response: {result}")

        if os.path.exists(txt_path):
            if action == "忽略":
                return f"{image_name}: 文件已存在，选择忽略。"
            elif action == "覆盖":
                with open(txt_path, "w") as txt_file:
                    txt_file.write(result)
            elif action == "加入前面":
                with open(txt_path, "r+") as txt_file:
                    content = txt_file.read()
                    txt_file.seek(0, 0)
                    txt_file.write(result + ", " + content)
            elif action == "加入后面":
                with open(txt_path, "a") as txt_file:
                    txt_file.write(", " + result)
        else:
            with open(txt_path, "w") as txt_file:
                txt_file.write(result)
        return f"打标结果: {result}"
    except requests.RequestException as e:
        print(f"Error processing image: {e}")
        return "处理失败，请检查API连接。"

# 获取第一个Prompt模板作为默认值
prompt_templates = get_prompt_templates()
default_prompt = prompt_templates[0] if prompt_templates else "Describe this picture in detail"

# 创建Gradio界面
with gr.Blocks(css="""
    .gradio-container { font-family: 'Helvetica Neue', Helvetica, Arial, sans-serif; }
    #title { text-align: center; font-size: 24px; font-weight: bold; margin-bottom: 20px; }
    #model-dropdown, #prompt-input, #template-dropdown, #image-input, #image-input-plus, #folder-input, #folder-txt-input, #text-input { margin-bottom: 10px; }
    #process-button, #process-button-plus, #process-folder-button, #insert-front-button, #insert-end-button { background-color: #007aff; color: white; border: none; padding: 10px 20px; border-radius: 5px; }
    #process-button:hover, #process-button-plus:hover, #process-folder-button:hover, #insert-front-button:hover, #insert-end-button:hover { background-color: #005bb5; }
    #tabs { margin-top: 20px; }
    #progress-info { margin-top: 20px; }
""") as demo:
    gr.Markdown("# Ollama AI图像反推", elem_id="title")

    with gr.Row():
        model_dropdown = gr.Dropdown(label="选择模型", choices=get_models(), elem_id="model-dropdown")

    with gr.Row():
        prompt_input = gr.Textbox(label="Prompt 1", value=default_prompt, elem_id="prompt-input")

    with gr.Row():
        prompt_template_dropdown = gr.Dropdown(label="Prompt模板选择", choices=prompt_templates, elem_id="template-dropdown")
        load_template_button = gr.Button("加载模板", size="sm", elem_id="load-template-button")

        def load_template(template):
            return template

        load_template_button.click(load_template, inputs=prompt_template_dropdown, outputs=prompt_input)

    with gr.Tabs(elem_id="tabs"):
        with gr.TabItem("单图处理", elem_id="single-tab"):
            image_input = gr.Image(type="filepath", label="上传图片", elem_id="image-input")
            process_button = gr.Button("执行", elem_id="process-button")
            single_output = gr.Textbox(label="处理结果", elem_id="single-output")

            def handle_single_image(model, prompt, image):
                if not model or not prompt or not image:
                    return "请选择一个模型并输入Prompt和图片。"
                save_prompt(prompt, "", model, "单图处理")
                return process_single_image(model, prompt, image)

            process_button.click(handle_single_image, inputs=[model_dropdown, prompt_input, image_input], outputs=single_output)

        with gr.TabItem("单图处理PLUS", elem_id="single-plus-tab"):
            image_input_plus = gr.Image(type="filepath", label="上传图片", elem_id="image-input-plus")
            prompt_input2 = gr.Textbox(label="Prompt 2", elem_id="prompt-input2")
            process_button_plus = gr.Button("执行", elem_id="process-button-plus")
            single_output1 = gr.Textbox(label="处理结果 1", elem_id="single-output1")
            single_output2 = gr.Textbox(label="处理结果 2", elem_id="single-output2")

            def handle_single_image_plus(model, prompt1, prompt2, image):
                if not model or not prompt1 or not prompt2 or not image:
                    return "请选择一个模型并输入Prompt和图片。", ""
                save_prompt(prompt1, prompt2, model, "单图处理PLUS")
                return process_single_image_plus(model, prompt1, prompt2, image)

            process_button_plus.click(handle_single_image_plus, inputs=[model_dropdown, prompt_input, prompt_input2, image_input_plus], outputs=[single_output1, single_output2])

        with gr.TabItem("多图处理", elem_id="multi-tab"):
            folder_input = gr.Textbox(label="文件夹路径", elem_id="folder-input")
            action_dropdown_folder = gr.Dropdown(label="选择打标方式", choices=["忽略", "覆盖", "加入前面", "加入后面"], elem_id="action-dropdown-folder")
            process_folder_button = gr.Button("执行", elem_id="process-folder-button")
            folder_output = gr.Textbox(label="处理结果", elem_id="folder-output", interactive=False)

            def handle_folder(model, prompt, folder_path, action):
                if not model or not prompt or not folder_path:
                    return "请选择一个模型并输入Prompt和文件夹路径。"
                save_prompt(prompt, "", model, "多图处理")
                return process_folder(model, prompt, folder_path, action)

            process_folder_button.click(handle_folder, inputs=[model_dropdown, prompt_input, folder_input, action_dropdown_folder], outputs=folder_output)

        with gr.TabItem("多图处理PLUS", elem_id="multi-plus-tab"):
            folder_input_plus = gr.Textbox(label="文件夹路径", elem_id="folder-input-plus")
            action_dropdown_folder_plus = gr.Dropdown(label="选择打标方式", choices=["忽略", "覆盖", "加入前面", "加入后面"], elem_id="action-dropdown-folder-plus")
            refine_model_dropdown = gr.Dropdown(label="选择精炼模型", choices=get_models(), elem_id="refine-model-dropdown")
            use_image_checkbox = gr.Checkbox(label="是否识别图像", elem_id="use-image-checkbox")
            hardware_dropdown = gr.Dropdown(label="选择硬件", choices=["GPU", "CPU"], value="CPU", elem_id="hardware-dropdown")
            prompt_input2_plus = gr.Textbox(label="Prompt 2", elem_id="prompt-input2-plus")
            process_folder_button_plus = gr.Button("执行", elem_id="process-folder-button-plus")
            folder_output_plus = gr.Textbox(label="处理结果", elem_id="folder-output-plus", interactive=False)

            def process_folder_plus(model, prompt1, prompt2, folder_path, action, refine_model, use_image, hardware):
                if not model or not refine_model or not prompt1 or not prompt2 or not folder_path:
                    return "请选择一个模型并输入Prompt和文件夹路径。"
                save_prompt(prompt1, prompt2, model, "多图处理PLUS")

                if not os.path.isdir(folder_path):
                    return "无效的文件夹路径。"

                results = []
                files = []
                for root, _, filenames in os.walk(folder_path):
                    files.extend([os.path.join(root, f) for f in filenames if f.lower().endswith(('.png', '.jpg', '.jpeg', '.bmp', '.gif'))])
                total_files = len(files)

                for idx, file in enumerate(files):
                    txt_path = os.path.join(os.path.dirname(file), f"{os.path.splitext(os.path.basename(file))[0]}.txt")
                    if os.path.exists(txt_path) and action == "忽略":
                        results.append(f"{file}: 文件已存在，选择忽略。")
                        continue  # 跳过此文件的处理

                    result1 = process_single_image(model, prompt1, file)
                    combined_prompt = f"{prompt2}\n{result1}"

                    if use_image:
                        with open(file, "rb") as img_file:
                            img_base64 = base64.b64encode(img_file.read()).decode('utf-8')
                        payload = {
                            "model": refine_model,
                            "prompt": combined_prompt,
                            "images": [img_base64],
                            "stream": False,
                            "hardware": hardware  # 添加硬件参数
                        }
                    else:
                        payload = {
                            "model": refine_model,
                            "prompt": combined_prompt,
                            "stream": False,
                            "hardware": hardware  # 添加硬件参数
                        }

                    try:
                        print(f"Sending request to {OLLAMA_API_URL}/generate with payload: {payload}")
                        response = requests.post(f"{OLLAMA_API_URL}/generate", json=payload)
                        response.raise_for_status()
                        result2 = response.json().get("response", "")
                        print(f"Received response: {result2}")

                        if os.path.exists(txt_path):
                            if action == "忽略":
                                results.append(f"{file}: 文件已存在，选择忽略。")
                            elif action == "覆盖":
                                with open(txt_path, "w") as txt_file:
                                    txt_file.write(result2)
                                results.append(f"{file}: 处理完成，结果已覆盖到 {txt_path}")
                            elif action == "加入前面":
                                with open(txt_path, "r+") as txt_file:
                                    content = txt_file.read()
                                    txt_file.seek(0, 0)
                                    txt_file.write(result2 + ", " + content)
                                results.append(f"{file}: 处理完成，结果已加入前面到 {txt_path}")
                            elif action == "加入后面":
                                with open(txt_path, "a") as txt_file:
                                    txt_file.write(", " + result2)
                                results.append(f"{file}: 处理完成，结果已加入后面到 {txt_path}")
                        else:
                            with open(txt_path, "w") as txt_file:
                                txt_file.write(result2)
                            results.append(f"{file}: 处理完成，结果已保存到 {txt_path}")

                    except requests.RequestException as e:
                        print(f"Error processing image: {e}")
                        results.append(f"{file}: 处理失败，请检查API连接。")

                return "\n".join(results)

            process_folder_button_plus.click(process_folder_plus, inputs=[model_dropdown, prompt_input, prompt_input2_plus, folder_input_plus, action_dropdown_folder_plus, refine_model_dropdown, use_image_checkbox, hardware_dropdown], outputs=folder_output_plus)

        with gr.TabItem("文字处理", elem_id="post-process-tab"):
            with gr.Tabs():
                with gr.TabItem("添加文字"):
                    folder_txt_input = gr.Textbox(label="TXT 文件夹路径", elem_id="folder-txt-input")
                    text_input = gr.Textbox(label="输入文字", elem_id="text-input")
                    insert_front_button = gr.Button("插入最前面", elem_id="insert-front-button")
                    insert_end_button = gr.Button("插入最后面", elem_id="insert-end-button")
                    txt_output = gr.Textbox(label="处理结果", elem_id="txt-output")

                    def handle_txt_folder(folder_path, text, insert_position):
                        if not os.path.isdir(folder_path):
                            return "无效的文件夹路径。"

                        results = []
                        for root, _, files in os.walk(folder_path):
                            txt_files = [f for f in files if f.lower().endswith('.txt')]
                            for txt_file in txt_files:
                                txt_path = os.path.join(root, txt_file)
                                with open(txt_path, "r") as file:
                                    content = file.read()

                                if insert_position == "front":
                                    with open(txt_path, "w") as file:
                                        file.write(text + content)
                                    results.append(f"{txt_file}: 插入最前面")
                                elif insert_position == "end":
                                    with open(txt_path, "a") as file:
                                        file.write(", " + text)
                                    results.append(f"{txt_file}: 插入最后面")

                        return "\n".join(results)

                    insert_front_button.click(handle_txt_folder, inputs=[folder_txt_input, text_input, gr.State("front")], outputs=txt_output)
                    insert_end_button.click(handle_txt_folder, inputs=[folder_txt_input, text_input, gr.State("end")], outputs=txt_output)

                with gr.TabItem("文字替换"):
                    folder_txt_replace_input = gr.Textbox(label="TXT 文件夹路径", elem_id="folder-txt-replace-input")
                    find_text_input = gr.Textbox(label="查找文字", elem_id="find-text-input")
                    replace_text_input = gr.Textbox(label="替换为", elem_id="replace-text-input")
                    replace_button = gr.Button("替换", elem_id="replace-button")
                    replace_output = gr.Textbox(label="处理结果", elem_id="replace-output")

                    def handle_txt_replace(folder_path, find_text, replace_text):
                        if not os.path.isdir(folder_path):
                            return "无效的文件夹路径。"

                        results = []
                        for root, _, files in os.walk(folder_path):
                            txt_files = [f for f in files if f.lower().endswith('.txt')]
                            for txt_file in txt_files:
                                txt_path = os.path.join(root, txt_file)
                                with open(txt_path, "r") as file:
                                    content = file.read()

                                new_content = content.replace(find_text, replace_text)

                                with open(txt_path, "w") as file:
                                    file.write(new_content)

                                results.append(f"{txt_file}: 替换完成")

                        return "\n".join(results)

                    replace_button.click(handle_txt_replace, inputs=[folder_txt_replace_input, find_text_input, replace_text_input], outputs=replace_output)

        # 新增 AI-Multiple 标签页
        with gr.TabItem("AI-Multiple", elem_id="ai-multiple-tab"):
            folder_input_multiple = gr.Textbox(label="文件夹路径", elem_id="folder-input-multiple")
            action_dropdown_multiple = gr.Dropdown(label="选择打标方式", choices=["忽略", "覆盖", "加入前面", "加入后面"], elem_id="action-dropdown-multiple")
            multi_tag_model_1 = gr.Dropdown(label="Multi-Tag 1 模型", choices=get_models(), elem_id="multi-tag-model-1")
            multi_tag_model_2 = gr.Dropdown(label="Multi-Tag 2 模型", choices=get_models(), elem_id="multi-tag-model-2")
            multi_tag_model_3 = gr.Dropdown(label="Multi-Tag 3 模型", choices=get_models(), elem_id="multi-tag-model-3")
            add_multi_tag_button = gr.Button("添加Multi-Tag", elem_id="add-multi-tag-button")
            refine_model_dropdown_multiple = gr.Dropdown(label="选择精炼模型", choices=get_models(), elem_id="refine-model-dropdown-multiple")
            use_image_checkbox_multiple = gr.Checkbox(label="是否识别图像", elem_id="use-image-checkbox-multiple")
            hardware_dropdown_multiple = gr.Dropdown(label="选择硬件", choices=["GPU", "CPU"], value="CPU", elem_id="hardware-dropdown-multiple")
            prompt_input2_multiple = gr.Textbox(label="Prompt 2", elem_id="prompt-input2-multiple")
            process_folder_button_multiple = gr.Button("执行", elem_id="process-folder-button-multiple")
            folder_output_multiple = gr.Textbox(label="处理结果", elem_id="folder-output-multiple", interactive=False)

            multi_tag_models = [multi_tag_model_1, multi_tag_model_2, multi_tag_model_3]

            def add_multi_tag():
                new_tag_index = len(multi_tag_models) + 1
                new_tag = gr.Dropdown(label=f"Multi-Tag {new_tag_index} 模型", choices=get_models(), elem_id=f"multi-tag-model-{new_tag_index}")
                multi_tag_models.append(new_tag)
                return gr.update(visible=True), new_tag

            def process_folder_multiple(model, prompt1, folder_path, action, multi_tag_model_1, multi_tag_model_2, multi_tag_model_3, refine_model, use_image, hardware, prompt2):
                multi_tag_models = [multi_tag_model_1, multi_tag_model_2, multi_tag_model_3]
                if not model or not refine_model or not prompt1 or not prompt2 or not folder_path or not any(multi_tag_models):
                    return "请选择一个模型并输入Prompt和文件夹路径。"
                save_prompt(prompt1, prompt2, model, "AI-Multiple")

                if not os.path.isdir(folder_path):
                    return "无效的文件夹路径。"

                results = []
                files = []
                for root, _, filenames in os.walk(folder_path):
                    files.extend([os.path.join(root, f) for f in filenames if f.lower().endswith(('.png', '.jpg', '.jpeg', '.bmp', '.gif'))])
                total_files = len(files)

                for idx, file in enumerate(files):
                    txt_path = os.path.join(os.path.dirname(file), f"{os.path.splitext(os.path.basename(file))[0]}.txt")
                    if os.path.exists(txt_path) and action == "忽略":
                        results.append(f"{file}: 文件已存在，选择忽略。")
                        continue  # 跳过此文件的处理

                    result1 = process_single_image(model, prompt1, file)
                    combined_prompt = f"{prompt2}\n{result1}"

                    multi_tag_results = []
                    for multi_tag_model in multi_tag_models:
                        if multi_tag_model:
                            multi_tag_result = process_single_image(multi_tag_model, prompt1, file)
                            multi_tag_results.append(multi_tag_result)

                    combined_prompt += "\n" + "\n".join(multi_tag_results)

                    if use_image:
                        with open(file, "rb") as img_file:
                            img_base64 = base64.b64encode(img_file.read()).decode('utf-8')
                        payload = {
                            "model": refine_model,
                            "prompt": combined_prompt,
                            "images": [img_base64],
                            "stream": False,
                            "hardware": hardware  # 添加硬件参数
                        }
                    else:
                        payload = {
                            "model": refine_model,
                            "prompt": combined_prompt,
                            "stream": False,
                            "hardware": hardware  # 添加硬件参数
                        }

                    try:
                        print(f"Sending request to {OLLAMA_API_URL}/generate with payload: {payload}")
                        response = requests.post(f"{OLLAMA_API_URL}/generate", json=payload)
                        response.raise_for_status()
                        result2 = response.json().get("response", "")
                        print(f"Received response: {result2}")

                        if os.path.exists(txt_path):
                            if action == "忽略":
                                results.append(f"{file}: 文件已存在，选择忽略。")
                            elif action == "覆盖":
                                with open(txt_path, "w") as txt_file:
                                    txt_file.write(result2)
                                results.append(f"{file}: 处理完成，结果已覆盖到 {txt_path}")
                            elif action == "加入前面":
                                with open(txt_path, "r+") as txt_file:
                                    content = txt_file.read()
                                    txt_file.seek(0, 0)
                                    txt_file.write(result2 + ", " + content)
                                results.append(f"{file}: 处理完成，结果已加入前面到 {txt_path}")
                            elif action == "加入后面":
                                with open(txt_path, "a") as txt_file:
                                    txt_file.write(", " + result2)
                                results.append(f"{file}: 处理完成，结果已加入后面到 {txt_path}")
                        else:
                            with open(txt_path, "w") as txt_file:
                                txt_file.write(result2)
                            results.append(f"{file}: 处理完成，结果已保存到 {txt_path}")

                    except requests.RequestException as e:
                        print(f"Error processing image: {e}")
                        results.append(f"{file}: 处理失败，请检查API连接。")

                return "\n".join(results)

            add_multi_tag_button.click(add_multi_tag, [], [gr.Column(visible=False)])

            process_folder_button_multiple.click(
                process_folder_multiple,
                inputs=[
                    model_dropdown,
                    prompt_input,
                    folder_input_multiple,
                    action_dropdown_multiple,
                    multi_tag_model_1,
                    multi_tag_model_2,
                    multi_tag_model_3,
                    refine_model_dropdown_multiple,
                    use_image_checkbox_multiple,
                    hardware_dropdown_multiple,
                    prompt_input2_multiple
                ],
                outputs=folder_output_multiple
            )

demo.launch(server_port=7888)