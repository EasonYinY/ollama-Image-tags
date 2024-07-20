import os
import time
import requests
import base64
import csv
from datetime import datetime
import logging
import threading
import concurrent.futures
import gradio as gr
import psutil
import subprocess
import shutil

# 配置日志记录
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# 配置文件路径和API URL
CONFIG = {
    "OLLAMA_API_URL": "http://localhost:11434/api",
    "PROMPT_TEMPLATES_FILE": "prompt_templates.csv",
    "HISTORY_PROMPTS_FILE": "history_prompts.csv",
    "OLLAMA_EXECUTABLE": "C:/Users/Eason/AppData/Local/Programs/Ollama/ollama app.exe",  # 修改为 Ollama 可执行文件的路径
    "LOG_FILE": "app.log"
}

# 禁用Gradio的分析功能
os.environ["GRADIO_ANALYTICS_ENABLED"] = "False"

# 全局变量
stop_flag = False

# 获取本地模型列表
def get_models():
    try:
        response = requests.get(f"{CONFIG['OLLAMA_API_URL']}/tags", timeout=120)
        response.raise_for_status()
        models = response.json().get("models", [])
        return [model["name"] for model in models]
    except requests.RequestException as e:
        logging.error(f"Error fetching models: {e}")
        return []

# 获取Prompt模板列表
def get_prompt_templates():
    templates = []
    try:
        with open(CONFIG["PROMPT_TEMPLATES_FILE"], "r") as file:
            reader = csv.reader(file)
            for row in reader:
                if len(row) >= 2:
                    templates.append({"title": row[0], "prompt": row[1]})
    except FileNotFoundError:
        logging.warning(f"{CONFIG['PROMPT_TEMPLATES_FILE']} 文件未找到")
    return templates

# 保存历史记录prompt
def save_prompt(prompt1, prompt2, model, source):
    file_exists = os.path.isfile(CONFIG["HISTORY_PROMPTS_FILE"])
    with open(CONFIG["HISTORY_PROMPTS_FILE"], "a", newline='') as file:
        writer = csv.writer(file)
        if not file_exists:
            writer.writerow(["日期", "模型", "来源", "Prompt 1", "Prompt 2"])
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        writer.writerow([now, model, source, prompt1, prompt2])

# 重启 Ollama 软件
def restart_ollama():
    try:
        logging.info("重启 Ollama 软件...")
        
        # 停止 Ollama 软件
        for proc in psutil.process_iter():
            if proc.name() in ["ollama app.exe", "ollama.exe", "ollama_llama_server.exe"]:  # 修改为 Ollama 可执行文件的名称
                proc.kill()
        
        # 启动 Ollama 软件
        subprocess.Popen([CONFIG["OLLAMA_EXECUTABLE"]])
        
        time.sleep(10)  # 等待 10 秒
        logging.info("Ollama 软件已重启")
    except Exception as e:
        logging.error(f"重启 Ollama 软件失败: {e}")

# 处理单张图片
def process_single_image(model, prompt, image, hardware, retry_count=5):
    if not model:
        return "请选择一个模型。"

    image_path = image

    try:
        with open(image_path, "rb") as img_file:
            img_base64 = base64.b64encode(img_file.read()).decode('utf-8')

        payload = {
            "model": model,
            "prompt": prompt,
            "images": [img_base64],
            "stream": False,
            "hardware": hardware  # 添加硬件参数
        }

        start_time = time.time()
        response = requests.post(f"{CONFIG['OLLAMA_API_URL']}/generate", json=payload, timeout=120)
        response.raise_for_status()
        elapsed_time = time.time() - start_time
        result = response.json().get("response", "")
        return result, elapsed_time
    except requests.RequestException as e:
        logging.error(f"Error processing image: {e}")
        if "Read timed out" in str(e):
            if retry_count > 0:
                restart_ollama()
                return process_single_image(model, prompt, image, hardware, retry_count - 1)
            else:
                return "处理失败，请检查API连接。", 0
        return "处理失败，请检查API连接。", 0

# 处理单张图片并保存结果
def process_single_image_with_save(model, prompt, image, action, hardware):
    if not model:
        return "请选择一个模型。"

    image_path = image
    image_dir = os.path.dirname(image_path)
    image_name = os.path.basename(image_path)
    txt_path = os.path.join(image_dir, f"{os.path.splitext(image_name)[0]}.txt")

    result, elapsed_time = process_single_image(model, prompt, image, hardware)

    if "处理失败，请检查API连接。" in result:
        return result

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
    return f"打标结果: {result}", elapsed_time

# 遍历文件夹，获取所有图片文件及其同名txt文件的存在情况
def get_files_and_txt_status(folder_path):
    files = []
    txt_status = {}
    for root, _, filenames in os.walk(folder_path):
        for filename in filenames:
            if filename.lower().endswith(('.png', '.jpg', '.jpeg', '.bmp', '.gif')):
                file_path = os.path.join(root, filename)
                txt_path = os.path.join(root, f"{os.path.splitext(filename)[0]}.txt")
                files.append(file_path)
                txt_status[file_path] = os.path.exists(txt_path)
    return files, txt_status

# 获取第一个Prompt模板作为默认值
prompt_templates = get_prompt_templates()
default_prompt = prompt_templates[0]["prompt"] if prompt_templates else "Describe this picture in detail"

# 计算剩余时间
def format_remaining_time(seconds):
    hours, remainder = divmod(seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    return f"{int(hours)}小时 {int(minutes)}分钟 {int(seconds)}秒"

# 处理文件夹中的图片
def process_folder_images(model, prompt, folder_path, action, hardware, concurrency, refine_model=None, prompt2=None, use_image=False):
    global stop_flag
    stop_flag = False

    if not model or not prompt or not folder_path:
        return "请选择一个模型并输入Prompt和文件夹路径。"
    save_prompt(prompt, prompt2 or "", model, "多图处理")

    if not os.path.isdir(folder_path):
        return "无效的文件夹路径。"

    files, txt_status = get_files_and_txt_status(folder_path)
    results = []

    start_time = time.time()
    if action == "忽略":
        files = [file for file in files if not txt_status[file]]  # 只处理没有同名txt文件的图片
    total_files = len(files)
    processed_files = 0
    last_10_times = []
    previous_time = time.time()

    def process_file(file):
        nonlocal previous_time
        if stop_flag:
            return f"{file}: 处理被停止。"
        result, elapsed_time = process_single_image_with_save(model, prompt, file, action, hardware)
        current_time = time.time()
        elapsed_time = current_time - previous_time
        previous_time = current_time
        return result, elapsed_time

    with concurrent.futures.ThreadPoolExecutor(max_workers=int(concurrency)) as executor:
        future_to_file = {executor.submit(process_file, file): file for file in files}
        for future in concurrent.futures.as_completed(future_to_file):
            file = future_to_file[future]
            try:
                result, elapsed_time = future.result()
            except Exception as e:
                result = f"{file}: 处理失败，错误: {e}"
                elapsed_time = 0
            results.append(result)

            processed_files += 1
            last_10_times.append(elapsed_time)
            if len(last_10_times) > 10:
                last_10_times.pop(0)
            avg_time_per_file = sum(last_10_times) / len(last_10_times) if last_10_times else 0
            remaining_time = avg_time_per_file * (total_files - processed_files)
            logging.info(f"当前任务耗时: {elapsed_time:.2f}秒, 进度 {processed_files}/{total_files} files. 预计剩余时间: {format_remaining_time(remaining_time)}.")

    if refine_model and prompt2:
        txt_files = [os.path.join(os.path.dirname(file), f"{os.path.splitext(os.path.basename(file))[0]}.txt") for file in files]

        def refine_file(txt_file):
            nonlocal previous_time
            if stop_flag:
                return f"{txt_file}: 处理被停止。"

            with open(txt_file, "r") as file:
                txt_content = file.read()

            combined_prompt = prompt2.format(txt_content) if "{}" in prompt2 else f"{prompt2}\n{txt_content}"

            payload = {
                "model": refine_model,
                "prompt": combined_prompt,
                "stream": False,
                "hardware": hardware
            }

            try:
                response = requests.post(f"{CONFIG['OLLAMA_API_URL']}/generate", json=payload, timeout=120)
                response.raise_for_status()
                result = response.json().get("response", "")

                with open(txt_file, "w") as file:
                    file.write(result)

                current_time = time.time()
                elapsed_time = current_time - previous_time
                previous_time = current_time
                return f"{txt_file}: 处理完成", elapsed_time

            except requests.RequestException as e:
                logging.error(f"Error processing txt: {e}")
                if "Read timed out" in str(e):
                    restart_ollama()
                return f"{txt_file}: 处理失败，请检查API连接。", 0

        with concurrent.futures.ThreadPoolExecutor(max_workers=int(concurrency)) as executor:
            future_to_file = {executor.submit(refine_file, txt_file): txt_file for txt_file in txt_files}
            for future in concurrent.futures.as_completed(future_to_file):
                txt_file = future_to_file[future]
                try:
                    result, elapsed_time = future.result()
                except Exception as e:
                    result = f"{txt_file}: 处理失败，错误: {e}"
                    elapsed_time = 0
                results.append(result)

                processed_files += 1
                last_10_times.append(elapsed_time)
                if len(last_10_times) > 10:
                    last_10_times.pop(0)
                avg_time_per_file = sum(last_10_times) / len(last_10_times) if last_10_times else 0
                remaining_time = avg_time_per_file * (total_files - processed_files)
                logging.info(f"当前任务耗时: {elapsed_time:.2f}秒, 进度 {processed_files}/{total_files} files. 预计剩余时间: {format_remaining_time(remaining_time)}.")

    return "\n".join(results)

# 创建Gradio界面
with gr.Blocks(css="""
    .gradio-container { font-family: 'Helvetica Neue', Helvetica, Arial, sans-serif; }
    #title { text-align: center; font-size: 24px; font-weight: bold; margin-bottom: 20px; }
    #model-dropdown, #prompt-input, #template-dropdown, #folder-input, #folder-txt-input, #text-input { margin-bottom: 10px; }
    #process-folder-button, #insert-front-button, #insert-end-button { background-color: orange; color: white; border: none; padding: 10px 20px; border-radius: 5px; }
    #process-folder-button:hover, #insert-front-button:hover, #insert-end-button:hover { background-color: #ff8c00; }
    #tabs { margin-top: 20px; }
    #progress-info { margin-top: 20px; }
    .red-button { background-color: red; color: white; }
    .red-button:hover { background-color: darkred; }
    .template-preview { color: gray; font-size: 0.9em; }
    .template-preview:hover { color: black; }
""") as demo:
    gr.Markdown("# Ollama AI图像反推", elem_id="title")
    gr.Markdown("### 麻瓜打标器，利用丰富的开源模型进行AI全自动打标的工具，打标偷懒作者：Eason", elem_id="title2")
    
    with gr.Row():
        model_dropdown = gr.Dropdown(label="选择打标模型", choices=get_models(), elem_id="model-dropdown")

    with gr.Row():
        prompt_template_dropdown = gr.Dropdown(label="Prompt模板选择", choices=[template["title"] for template in prompt_templates], elem_id="template-dropdown")

    with gr.Row():
        load_template_button = gr.Button("加载到打标模型提示词", size="sm", elem_id="load-template-button")
        load_to_refine_button = gr.Button("加载到精炼模型提示词", size="sm", elem_id="load-to-refine-button")

    with gr.Row():
        prompt_input = gr.Textbox(label="打标提示词", value=default_prompt, elem_id="prompt-input")
        prompt_input2 = gr.Textbox(label="精炼提示词", elem_id="prompt-input2")
       
    with gr.Row():
        concurrency_input = gr.Number(label="并发数量", value=4, precision=0, elem_id="concurrency-input")

    def load_template(template_title):
        for template in prompt_templates:
            if template["title"] == template_title:
                return template["prompt"]
        return ""

    load_template_button.click(lambda title: gr.update(value=load_template(title)), inputs=prompt_template_dropdown, outputs=prompt_input)
    load_to_refine_button.click(lambda title: gr.update(value=load_template(title)), inputs=prompt_template_dropdown, outputs=prompt_input2)

    with gr.Tabs(elem_id="tabs"):
        with gr.TabItem("单图处理PLUS", elem_id="single-plus-tab"):
            gr.Markdown("该功能允许用户上传一张图片，并通过选择的AI模型生成描述。用户可以选择启用精炼模型对生成的描述进行进一步处理。", elem_id="single-plus-description")

            image_input_plus = gr.Image(type="filepath", label="上传图片", elem_id="image-input-plus")
            
            with gr.Row() :
                enable_refine_model = gr.Checkbox(label="启用精炼模型", elem_id="enable-refine-model")
            with gr.Row() :
                refine_model_dropdown = gr.Dropdown(label="选择精炼模型", choices=get_models(), elem_id="refine-model-dropdown")
                hardware_dropdown = gr.Dropdown(label="选择硬件", choices=["GPU", "CPU"], value="GPU", elem_id="hardware-dropdown")
            with gr.Row() :
                use_image_checkbox = gr.Checkbox(label="是否识别图像", elem_id="use-image-checkbox")
            
            process_button_plus = gr.Button("执行", elem_id="process-button-plus")
            stop_button_plus = gr.Button("停止", elem_id="stop-button-plus")
            single_output1 = gr.Textbox(label="处理结果 1", elem_id="single-output1")
            single_output2 = gr.Textbox(label="处理结果 2", elem_id="single-output2")

            def handle_single_image_plus(model, prompt1, prompt2, image, enable_refine, refine_model, use_image, hardware):
                global stop_flag
                stop_flag = False

                if not model or not prompt1 or not image:
                    return "请选择一个模型并输入Prompt和图片。", ""
                save_prompt(prompt1, prompt2, model, "单图处理PLUS")
                result1, elapsed_time1 = process_single_image(model, prompt1, image, hardware)

                if enable_refine:
                    combined_prompt = prompt2.format(result1)
                    if use_image:
                        with open(image, "rb") as img_file:
                            img_base64 = base64.b64encode(img_file.read()).decode('utf-8')
                        payload = {
                            "model": refine_model,
                            "prompt": combined_prompt,
                            "images": [img_base64],
                            "stream": False,
                            "hardware": hardware
                        }
                    else:
                        payload = {
                            "model": refine_model,
                            "prompt": combined_prompt,
                            "stream": False,
                            "hardware": hardware
                        }

                    try:
                        response = requests.post(f"{CONFIG['OLLAMA_API_URL']}/generate", json=payload, timeout=120)
                        response.raise_for_status()
                        result2 = response.json().get("response", "")
                        return result1, result2
                    except requests.RequestException as e:
                        logging.error(f"Error processing image: {e}")
                        if "Read timed out" in str(e):
                            restart_ollama()
                        return result1, "处理失败，请检查API连接。"
                else:
                    return result1, ""

            def stop_task():
                global stop_flag
                stop_flag = True

            process_button_plus.click(handle_single_image_plus, inputs=[model_dropdown, prompt_input, prompt_input2, image_input_plus, enable_refine_model, refine_model_dropdown, use_image_checkbox, hardware_dropdown], outputs=[single_output1, single_output2])
            stop_button_plus.click(stop_task)

        with gr.TabItem("多图处理", elem_id="multi-tab"):
            gr.Markdown("该功能允许用户选择一个文件夹，系统会遍历该文件夹中的所有图片文件，并通过选择的AI模型生成描述。用户可以选择不同的打标方式（忽略、覆盖、加入前面、加入后面）来处理已存在的同名txt文件。", elem_id="multi-description")

            folder_input = gr.Textbox(label="文件夹路径", elem_id="folder-input")
            action_dropdown_folder = gr.Dropdown(label="选择打标方式", choices=["忽略", "覆盖", "加入前面", "加入后面"], value="忽略", elem_id="action-dropdown-folder")
            process_folder_button = gr.Button("执行", elem_id="process-folder-button")
            stop_button_folder = gr.Button("停止", elem_id="stop-button-folder")
            folder_output = gr.Textbox(label="处理结果", elem_id="folder-output", interactive=False)

            process_folder_button.click(process_folder_images, inputs=[model_dropdown, prompt_input, folder_input, action_dropdown_folder, gr.State("GPU"), concurrency_input], outputs=folder_output)
            stop_button_folder.click(stop_task)

        with gr.TabItem("多图处理PLUS", elem_id="multi-plus-tab"):
            gr.Markdown("选择一个文件夹，会遍历该文件夹中的所有图片文件，执行后，先通过选择的AI模型整体生成一遍描述，存在本地目录，再将该描述返回给精炼模型进行二次处理，对文本精度进行多一轮的保证。", elem_id="multi-plus-description")

            folder_input_plus = gr.Textbox(label="文件夹路径", elem_id="folder-input-plus")
            action_dropdown_folder_plus = gr.Dropdown(label="选择打标方式", choices=["忽略", "覆盖", "加入前面", "加入后面"], elem_id="action-dropdown-folder-plus")
            refine_model_dropdown_plus = gr.Dropdown(label="选择精炼模型", choices=get_models(), elem_id="refine-model-dropdown-plus")
            use_image_checkbox_plus = gr.Checkbox(label="是否识别图像", elem_id="use-image-checkbox-plus")
            hardware_dropdown_plus = gr.Dropdown(label="选择硬件", choices=["GPU", "CPU"], value="GPU", elem_id="hardware-dropdown-plus")
            process_folder_button_plus = gr.Button("执行", elem_id="process-folder-button-plus")
            stop_button_folder_plus = gr.Button("停止", elem_id="stop-button-folder-plus")
            folder_output_plus = gr.Textbox(label="处理结果", elem_id="folder-output-plus", interactive=False)

            process_folder_button_plus.click(process_folder_images, inputs=[model_dropdown, prompt_input, folder_input_plus, action_dropdown_folder_plus, hardware_dropdown_plus, concurrency_input, refine_model_dropdown_plus, prompt_input2, use_image_checkbox_plus], outputs=folder_output_plus)
            stop_button_folder_plus.click(stop_task)

        with gr.TabItem("AI-Multi-Tag", elem_id="ai-multiple-tab"):
            gr.Markdown("该功能为实现性功能，选择一个文件夹，并通过多个选择的AI模型生成描述，再将其给到精炼模型对结果进行进一步处理，增加描述的丰富度。", elem_id="ai-multiple-description")

            folder_input_multiple = gr.Textbox(label="文件夹路径", elem_id="folder-input-multiple")
            action_dropdown_multiple = gr.Dropdown(label="选择打标方式", choices=["忽略", "覆盖", "加入前面", "加入后面"], elem_id="action-dropdown-multiple")

            with gr.Row():
                multi_tag_model_1 = gr.Dropdown(label="Multi-Tag 1 模型", choices=get_models(), elem_id="multi-tag-model-1")
                enable_multi_tag_model_1 = gr.Checkbox(label="启用", value=True, elem_id="enable-multi-tag-model-1")

            with gr.Row():
                multi_tag_model_2 = gr.Dropdown(label="Multi-Tag 2 模型", choices=get_models(), elem_id="multi-tag-model-2")
                enable_multi_tag_model_2 = gr.Checkbox(label="启用", value=False, elem_id="enable-multi-tag-model-2")

            with gr.Row():
                multi_tag_model_3 = gr.Dropdown(label="Multi-Tag 3 模型", choices=get_models(), elem_id="multi-tag-model-3")
                enable_multi_tag_model_3 = gr.Checkbox(label="启用", value=False, elem_id="enable-multi-tag-model-3")

            enable_refine_model_multiple = gr.Checkbox(label="启用精炼模型", elem_id="enable-refine-model-multiple")
            refine_model_dropdown_multiple = gr.Dropdown(label="选择精炼模型", choices=get_models(), elem_id="refine-model-dropdown-multiple")
            use_image_checkbox_multiple = gr.Checkbox(label="是否识别图像", elem_id="use-image-checkbox-multiple")
            hardware_dropdown_multiple = gr.Dropdown(label="选择硬件", choices=["GPU", "CPU"], value="GPU", elem_id="hardware-dropdown-multiple")
            process_folder_button_multiple = gr.Button("执行", elem_id="process-folder-button-multiple")
            stop_button_folder_multiple = gr.Button("停止", elem_id="stop-button-folder-multiple")
            folder_output_multiple = gr.Textbox(label="处理结果", elem_id="folder-output-multiple", interactive=False)

            def process_folder_multiple(model, prompt1, folder_path, action, multi_tag_model_1, enable_multi_tag_model_1, multi_tag_model_2, enable_multi_tag_model_2, multi_tag_model_3, enable_multi_tag_model_3, refine_model, enable_refine, use_image, hardware, prompt2, concurrency):
                global stop_flag
                stop_flag = False

                multi_tag_models = [(multi_tag_model_1, enable_multi_tag_model_1), (multi_tag_model_2, enable_multi_tag_model_2), (multi_tag_model_3, enable_multi_tag_model_3)]
                if not model or not prompt1 or not folder_path or not any(enable for _, enable in multi_tag_models):
                    return "请选择一个模型并输入Prompt和文件夹路径。"
                save_prompt(prompt1, prompt2, model, "AI-Multiple")

                if not os.path.isdir(folder_path):
                    return "无效的文件夹路径。"

                files, txt_status = get_files_and_txt_status(folder_path)
                results = []

                start_time = time.time()
                if action == "忽略":
                    files = [file for file in files if not txt_status[file]]  # 只处理没有同名txt文件的图片
                total_files = len(files)
                processed_files = 0
                last_10_times = []
                previous_time = time.time()

                def process_file(file):
                    nonlocal previous_time
                    if stop_flag:
                        return f"{file}: 处理被停止。"
                    if txt_status[file] and action == "忽略":
                        return f"{file}: 文件已存在，选择忽略。"

                    # 处理第一步，使用选择的模型
                    result1, elapsed_time1 = process_single_image(model, prompt1, file, hardware)
                    combined_results = [result1]

                    # 处理 Multi-Tag 模型
                    for multi_tag_model, enable in multi_tag_models:
                        if enable:
                            multi_tag_result, elapsed_time_multi = process_single_image(multi_tag_model, prompt1, file, hardware)
                            combined_results.append(multi_tag_result)

                    # 将所有结果合并到 Prompt 2
                    combined_prompt = prompt2.format("\n————————————————\n".join(combined_results))

                    if enable_refine:
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
                            response = requests.post(f"{CONFIG['OLLAMA_API_URL']}/generate", json=payload, timeout=120)
                            response.raise_for_status()
                            result2 = response.json().get("response", "")

                            txt_path = os.path.join(os.path.dirname(file), f"{os.path.splitext(os.path.basename(file))[0]}.txt")
                            if os.path.exists(txt_path):
                                if action == "忽略":
                                    return f"{file}: 文件已存在，选择忽略。", elapsed_time1
                                elif action == "覆盖":
                                    with open(txt_path, "w") as txt_file:
                                        txt_file.write(result2)
                                    return f"{file}: 处理完成，结果已覆盖到 {txt_path}", elapsed_time1
                                elif action == "加入前面":
                                    with open(txt_path, "r+") as txt_file:
                                        content = txt_file.read()
                                        txt_file.seek(0, 0)
                                        txt_file.write(result2 + ", " + content)
                                    return f"{file}: 处理完成，结果已加入前面到 {txt_path}", elapsed_time1
                                elif action == "加入后面":
                                    with open(txt_path, "a") as txt_file:
                                        txt_file.write(", " + result2)
                                    return f"{file}: 处理完成，结果已加入后面到 {txt_path}", elapsed_time1
                            else:
                                with open(txt_path, "w") as txt_file:
                                    txt_file.write(result2)
                                return f"{file}: 处理完成，结果已保存到 {txt_path}", elapsed_time1

                        except requests.RequestException as e:
                            logging.error(f"Error processing image: {e}")
                            if "Read timed out" in str(e):
                                restart_ollama()
                            return f"{file}: 处理失败，请检查API连接。", elapsed_time1

                    else:
                        txt_path = os.path.join(os.path.dirname(file), f"{os.path.splitext(os.path.basename(file))[0]}.txt")
                        if os.path.exists(txt_path):
                            if action == "忽略":
                                return f"{file}: 文件已存在，选择忽略。", elapsed_time1
                            elif action == "覆盖":
                                with open(txt_path, "w") as txt_file:
                                    txt_file.write("\n————————————————\n".join(combined_results))
                                return f"{file}: 处理完成，结果已覆盖到 {txt_path}", elapsed_time1
                            elif action == "加入前面":
                                with open(txt_path, "r+") as txt_file:
                                    content = txt_file.read()
                                    txt_file.seek(0, 0)
                                    txt_file.write("\n————————————————\n".join(combined_results) + ", " + content)
                                return f"{file}: 处理完成，结果已加入前面到 {txt_path}", elapsed_time1
                            elif action == "加入后面":
                                with open(txt_path, "a") as txt_file:
                                    txt_file.write(", " + "\n————————————————\n".join(combined_results))
                                return f"{file}: 处理完成，结果已加入后面到 {txt_path}", elapsed_time1
                        else:
                            with open(txt_path, "w") as txt_file:
                                txt_file.write("\n————————————————\n".join(combined_results))
                            return f"{file}: 处理完成，结果已保存到 {txt_path}", elapsed_time1

                    current_time = time.time()
                    elapsed_time = current_time - previous_time
                    previous_time = current_time
                    return result1, elapsed_time

                with concurrent.futures.ThreadPoolExecutor(max_workers=int(concurrency)) as executor:
                    future_to_file = {executor.submit(process_file, file): file for file in files if not txt_status[file]}
                    for future in concurrent.futures.as_completed(future_to_file):
                        file = future_to_file[future]
                        try:
                            result, elapsed_time = future.result()
                        except Exception as e:
                            result = f"{file}: 处理失败，错误: {e}"
                            elapsed_time = 0
                        results.append(result)

                        processed_files += 1
                        last_10_times.append(elapsed_time)
                        if len(last_10_times) > 10:
                            last_10_times.pop(0)
                        avg_time_per_file = sum(last_10_times) / len(last_10_times) if last_10_times else 0
                        remaining_time = avg_time_per_file * (total_files - processed_files)
                        logging.info(f"当前任务耗时: {elapsed_time:.2f}秒, 进度 {processed_files}/{total_files} files. 预计剩余时间: {format_remaining_time(remaining_time)}.")

                return "\n".join(results)

            process_folder_button_multiple.click(
                process_folder_multiple,
                inputs=[
                    model_dropdown,
                    prompt_input,
                    folder_input_multiple,
                    action_dropdown_multiple,
                    multi_tag_model_1,
                    enable_multi_tag_model_1,
                    multi_tag_model_2,
                    enable_multi_tag_model_2,
                    multi_tag_model_3,
                    enable_multi_tag_model_3,
                    refine_model_dropdown_multiple,
                    enable_refine_model_multiple,
                    use_image_checkbox_multiple,
                    hardware_dropdown_multiple,
                    prompt_input2,
                    concurrency_input
                ],
                outputs=folder_output_multiple
            )
            stop_button_folder_multiple.click(stop_task)

        with gr.TabItem("文字处理", elem_id="post-process-tab"):
            with gr.Tabs():
                with gr.TabItem("添加文字"):
                    gr.Markdown("该功能允许用户在指定文件夹中的所有txt文件中添加指定的文字。用户可以选择将文字插入到文件的最前面或最后面。", elem_id="add-text-description")

                    folder_txt_input = gr.Textbox(label="TXT 文件夹路径", elem_id="folder-txt-input")
                    text_input = gr.Textbox(label="输入文字", elem_id="text-input")
                    with gr.Row():
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
                    gr.Markdown("该功能允许用户在指定文件夹中的所有txt文件中查找并替换指定的文字。用户可以输入查找的文字和替换的文字。", elem_id="replace-text-description")

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

                with gr.TabItem("删除文件"):
                    gr.Markdown("该功能允许用户在指定文件夹中查找包含指定文字的txt文件，并删除这些文件。用户可以选择是否区分大小写进行查找。", elem_id="delete-files-description")

                    folder_delete_input = gr.Textbox(label="文件夹地址输入", elem_id="folder-delete-input")
                    delete_text_input = gr.Textbox(label="包含文字", elem_id="delete-text-input")
                    case_sensitive_checkbox = gr.Checkbox(label="区分大小写", elem_id="case-sensitive-checkbox")
                    search_button = gr.Button("搜索", elem_id="search-button")
                    with gr.Row():
                        delete_txt_button = gr.Button("删除TXT", elem_id="delete-txt-button")
                        delete_txt_image_button = gr.Button("删除txt+同名图片", elem_id="delete-txt-image-button", elem_classes="red-button")
                    file_count_output = gr.Textbox(label="文件数量显示栏", elem_id="file-count-output", interactive=False)

                    with gr.Row():
                        non_utf8_search_button = gr.Button("非UTF-8查找", elem_id="non-utf8-search-button")
                        delete_non_utf8_button = gr.Button("查找并删除非UTF-8.TXT", elem_id="delete-non-utf8-button")

                    delete_empty_txt_button = gr.Button("删除空TXT文件", elem_id="delete-empty-txt-button")

                    def search_files(folder_path, search_text, case_sensitive):
                        global txt_files_global
                        if not os.path.isdir(folder_path):
                            return "无效的文件夹路径。"

                        txt_files = []
                        all_txt_files = 0
                        all_image_files = 0
                        for root, _, files in os.walk(folder_path):
                            for file in files:
                                if file.lower().endswith('.txt'):
                                    all_txt_files += 1
                                    txt_path = os.path.join(root, file)
                                    with open(txt_path, "r", encoding="utf-8", errors="ignore") as txt_file:
                                        content = txt_file.read()
                                        if (case_sensitive and search_text in content) or (not case_sensitive and search_text.lower() in content.lower()):
                                            txt_files.append(txt_path)
                                elif file.lower().endswith(('.png', '.jpg', '.jpeg', '.bmp', '.gif')):
                                    all_image_files += 1

                        txt_files_global = txt_files
                        result = f"符合文件的数量: {len(txt_files)}\n"
                        result += f"已打标签图片总数: {all_txt_files}\n"
                        result += f"图片文件总数: {all_image_files}\n"
                        result += "符合要求的文件名称:\n" + "\n".join(txt_files)
                        return result

                    def delete_files(txt_files, delete_images=False):
                        deleted_files = []
                        for txt_file in txt_files:
                            os.remove(txt_file)
                            deleted_files.append(txt_file)
                            if delete_images:
                                image_file = os.path.splitext(txt_file)[0] + os.path.splitext(txt_file)[1]
                                if os.path.exists(image_file):
                                    os.remove(image_file)
                                    deleted_files.append(image_file)
                        return f"已删除文件: {', '.join(deleted_files)}"

                    def search_non_utf8_files(folder_path):
                        global non_utf8_files_global
                        if not os.path.isdir(folder_path):
                            return "无效的文件夹路径。"

                        non_utf8_files = []
                        for root, _, files in os.walk(folder_path):
                            for file in files:
                                if file.lower().endswith('.txt'):
                                    txt_path = os.path.join(root, file)
                                    try:
                                        with open(txt_path, "r", encoding="utf-8") as txt_file:
                                            txt_file.read()
                                    except UnicodeDecodeError:
                                        non_utf8_files.append(txt_path)
                        non_utf8_files_global = non_utf8_files
                        return f"符合非UTF-8文件的数量: {len(non_utf8_files)}\n非UTF-8文件名称:\n" + "\n".join(non_utf8_files)

                    def delete_non_utf8_files(non_utf8_files):
                        deleted_files = []
                        for txt_file in non_utf8_files:
                            os.remove(txt_file)
                            deleted_files.append(txt_file)
                        return f"已删除非UTF-8文件: {', '.join(deleted_files)}"

                    def delete_empty_txt_files(folder_path):
                        if not os.path.isdir(folder_path):
                            return "无效的文件夹路径。"

                        deleted_files = []
                        for root, _, files in os.walk(folder_path):
                            for file in files:
                                if file.lower().endswith('.txt'):
                                    txt_path = os.path.join(root, file)
                                    if os.path.getsize(txt_path) == 0:
                                        os.remove(txt_path)
                                        deleted_files.append(txt_path)
                        return f"已删除空TXT文件: {', '.join(deleted_files)}"

                    search_button.click(search_files, inputs=[folder_delete_input, delete_text_input, case_sensitive_checkbox], outputs=file_count_output)
                    delete_txt_button.click(lambda: delete_files(txt_files_global, delete_images=False), outputs=file_count_output)
                    delete_txt_image_button.click(lambda: delete_files(txt_files_global, delete_images=True), outputs=file_count_output)

                    non_utf8_search_button.click(search_non_utf8_files, inputs=folder_delete_input, outputs=file_count_output)
                    delete_non_utf8_button.click(lambda: delete_non_utf8_files(non_utf8_files_global), outputs=file_count_output)
                    delete_empty_txt_button.click(delete_empty_txt_files, inputs=folder_delete_input, outputs=file_count_output)

                with gr.TabItem("转移文件"):
                    gr.Markdown("该功能允许用户在指定文件夹中查找包含指定文字的txt文件，并将这些文件转移到指定的目标文件夹。用户可以选择是否同时转移同名的图片文件。", elem_id="move-files-description")

                    folder_move_input = gr.Textbox(label="文件夹地址输入", elem_id="folder-move-input")
                    move_target_input = gr.Textbox(label="转移地址", elem_id="move-target-input")
                    move_text_input = gr.Textbox(label="包含文字", elem_id="move-text-input")
                    case_sensitive_move_checkbox = gr.Checkbox(label="区分大小写", elem_id="case-sensitive-move-checkbox")
                    search_move_button = gr.Button("搜索", elem_id="search-move-button")
                    with gr.Row():
                        move_txt_button = gr.Button("转移TXT", elem_id="move-txt-button")
                        move_txt_image_button = gr.Button("转移txt+同名图片", elem_id="move-txt-image-button", elem_classes="red-button")
                    file_count_move_output = gr.Textbox(label="文件数量显示栏", elem_id="file-count-move-output", interactive=False)

                    def search_move_files(folder_path, search_text, case_sensitive):
                        global txt_files_global
                        if not os.path.isdir(folder_path):
                            return "无效的文件夹路径。"

                        txt_files = []
                        for root, _, files in os.walk(folder_path):
                            for file in files:
                                if file.lower().endswith('.txt'):
                                    txt_path = os.path.join(root, file)
                                    with open(txt_path, "r", encoding="utf-8", errors="ignore") as txt_file:
                                        content = txt_file.read()
                                        if (case_sensitive and search_text in content) or (not case_sensitive and search_text.lower() in content.lower()):
                                            txt_files.append(txt_path)

                        txt_files_global = txt_files
                        return f"符合文件的数量: {len(txt_files)}\n符合要求的文件名称:\n" + "\n".join(txt_files)

                    def move_files(txt_files, target_folder, move_images=False):
                        if not os.path.isdir(target_folder):
                            return "无效的目标文件夹路径。"

                        moved_files = []
                        for txt_file in txt_files:
                            target_path = os.path.join(target_folder, os.path.basename(txt_file))
                            shutil.move(txt_file, target_path)
                            moved_files.append(target_path)
                            if move_images:
                                image_file = os.path.splitext(txt_file)[0] + os.path.splitext(txt_file)[1]
                                if os.path.exists(image_file):
                                    target_image_path = os.path.join(target_folder, os.path.basename(image_file))
                                    shutil.move(image_file, target_image_path)
                                    moved_files.append(target_image_path)
                        return f"已转移文件: {', '.join(moved_files)}"

                    search_move_button.click(search_move_files, inputs=[folder_move_input, move_text_input, case_sensitive_move_checkbox], outputs=file_count_move_output)
                    move_txt_button.click(lambda target_folder: move_files(txt_files_global, target_folder, move_images=False), inputs=[move_target_input], outputs=file_count_move_output)
                    move_txt_image_button.click(lambda target_folder: move_files(txt_files_global, target_folder, move_images=True), inputs=[move_target_input], outputs=file_count_move_output)

        with gr.TabItem("打标后AI润色", elem_id="post-refine-tab"):
            with gr.Tabs():
                with gr.TabItem("精炼标签"):
                    gr.Markdown("对已近有标签的图片进行文字精炼或润色，比如WD14或者“多图处理”等打完一次标的文件。但是仅对文字进行优化，不会再次识别图片。选择一个文件夹，系统会遍历该文件夹及其子文件夹中的所有txt文件，并将txt文件的内容插入到精炼提示词的{}内，然后使用选择的精炼模型处理，结果将覆盖原txt文件。", elem_id="refine-description")

                    folder_input_refine = gr.Textbox(label="文件夹路径", elem_id="folder-input-refine")
                    refine_model_dropdown_refine = gr.Dropdown(label="选择精炼模型", choices=get_models(), elem_id="refine-model-dropdown-refine")
                    hardware_dropdown_refine = gr.Dropdown(label="选择硬件", choices=["GPU", "CPU"], value="GPU", elem_id="hardware-dropdown-refine")
                    process_refine_button = gr.Button("执行", elem_id="process-refine-button")
                    stop_button_refine = gr.Button("停止", elem_id="stop-button-refine")
                    refine_output = gr.Textbox(label="处理结果", elem_id="refine-output", interactive=False)

                    def process_refine(folder_path, refine_model, prompt2, hardware, concurrency):
                        global stop_flag
                        stop_flag = False

                        if not refine_model or not prompt2 or not folder_path:
                            return "请选择一个精炼模型并输入Prompt和文件夹路径。"

                        if not os.path.isdir(folder_path):
                            return "无效的文件夹路径。"

                        txt_files = []
                        for root, _, files in os.walk(folder_path):
                            for file in files:
                                if file.lower().endswith('.txt'):
                                    txt_files.append(os.path.join(root, file))

                        results = []

                        start_time = time.time()
                        total_files = len(txt_files)
                        processed_files = 0
                        last_10_times = []
                        previous_time = time.time()

                        def process_file(txt_file):
                            nonlocal previous_time
                            if stop_flag:
                                return f"{txt_file}: 处理被停止。"

                            with open(txt_file, "r") as file:
                                txt_content = file.read()

                            combined_prompt = prompt2.format(txt_content) if "{}" in prompt2 else f"{prompt2}\n{txt_content}"

                            payload = {
                                "model": refine_model,
                                "prompt": combined_prompt,
                                "stream": False,
                                "hardware": hardware  # 使用指定的硬件参数
                            }

                            try:
                                response = requests.post(f"{CONFIG['OLLAMA_API_URL']}/generate", json=payload, timeout=120)
                                response.raise_for_status()
                                result = response.json().get("response", "")

                                with open(txt_file, "w") as file:
                                    file.write(result)

                                current_time = time.time()
                                elapsed_time = current_time - previous_time
                                previous_time = current_time
                                return f"{txt_file}: 处理完成", elapsed_time

                            except requests.RequestException as e:
                                logging.error(f"Error processing txt: {e}")
                                if "Read timed out" in str(e):
                                    restart_ollama()
                                return f"{txt_file}: 处理失败，请检查API连接。", 0

                        with concurrent.futures.ThreadPoolExecutor(max_workers=int(concurrency)) as executor:
                            future_to_file = {executor.submit(process_file, txt_file): txt_file for txt_file in txt_files}
                            for future in concurrent.futures.as_completed(future_to_file):
                                txt_file = future_to_file[future]
                                try:
                                    result, elapsed_time = future.result()
                                except Exception as e:
                                    result = f"{txt_file}: 处理失败，错误: {e}"
                                    elapsed_time = 0
                                results.append(result)

                                processed_files += 1
                                last_10_times.append(elapsed_time)
                                if len(last_10_times) > 10:
                                    last_10_times.pop(0)
                                avg_time_per_file = sum(last_10_times) / len(last_10_times) if last_10_times else 0
                                remaining_time = avg_time_per_file * (total_files - processed_files)
                                logging.info(f"当前任务耗时: {elapsed_time:.2f}秒, 进度 {processed_files}/{total_files} files. 预计剩余时间: {format_remaining_time(remaining_time)}.")

                        return "\n".join(results)

                    process_refine_button.click(process_refine, inputs=[folder_input_refine, refine_model_dropdown_refine, prompt_input2, hardware_dropdown_refine, concurrency_input], outputs=refine_output)
                    stop_button_refine.click(stop_task)

                with gr.TabItem("多模态标签润色"):
                    gr.Markdown("与精炼标签功能不同，该功能可以对已有标签的图片，通过通用AI模型对其标签文字和图片同时识别并进行重新润色处理或二次加工。用户可以输入文件夹地址，系统将遍历该文件夹及其子文件夹中的图片文件和txt文件，对包含txt文件的图片进行处理。", elem_id="post-refine-description")

                    folder_input_multimodal_refine = gr.Textbox(label="文件夹路径", elem_id="folder-input-multimodal-refine")
                    action_dropdown_multimodal_refine = gr.Dropdown(label="选择打标方式", choices=["忽略", "覆盖", "加入前面", "加入后面"], value="覆盖", elem_id="action-dropdown-multimodal-refine")
                    enable_refine_model_multimodal = gr.Checkbox(label="启用精炼模型", elem_id="enable-refine-model-multimodal")
                    refine_model_dropdown_multimodal_refine = gr.Dropdown(label="选择精炼模型", choices=get_models(), elem_id="refine-model-dropdown-multimodal-refine")
                    use_image_checkbox_multimodal_refine = gr.Checkbox(label="是否识别图像", elem_id="use-image-checkbox-multimodal-refine")
                    hardware_dropdown_multimodal_refine = gr.Dropdown(label="选择硬件", choices=["GPU", "CPU"], value="GPU", elem_id="hardware-dropdown-multimodal-refine")
                    process_multimodal_refine_button = gr.Button("执行", elem_id="process-multimodal-refine-button")
                    stop_button_multimodal_refine = gr.Button("停止", elem_id="stop-button-multimodal-refine")
                    multimodal_refine_output = gr.Textbox(label="处理结果", elem_id="multimodal-refine-output", interactive=False)

                    def process_multimodal_refine(model, prompt1, folder_path, action, refine_model, enable_refine, use_image, hardware, prompt2, concurrency):
                        global stop_flag
                        stop_flag = False

                        if not model or not prompt1 or not folder_path:
                            return "请选择一个模型并输入Prompt和文件夹路径。"
                        save_prompt(prompt1, prompt2, model, "多模态标签润色")

                        if not os.path.isdir(folder_path):
                            return "无效的文件夹路径。"

                        files, txt_status = get_files_and_txt_status(folder_path)
                        results = []

                        start_time = time.time()
                        total_files = len([file for file in files if txt_status[file]])  # 只计算需要润色的文件数量
                        processed_files = 0
                        last_10_times = []
                        previous_time = time.time()

                        def process_file(file):
                            nonlocal previous_time
                            if stop_flag:
                                return f"{file}: 处理被停止。"
                            if not txt_status[file]:
                                return f"{file}: 未找到对应的txt文件，跳过。"

                            with open(txt_status[file], "r") as txt_file:
                                txt_content = txt_file.read()

                            combined_prompt = prompt1.format(txt_content) if "{}" in prompt1 else f"{prompt1}\n{txt_content}"

                            result1, elapsed_time1 = process_single_image(model, combined_prompt, file, hardware)

                            if enable_refine:
                                if use_image:
                                    with open(file, "rb") as img_file:
                                        img_base64 = base64.b64encode(img_file.read()).decode('utf-8')
                                    payload = {
                                        "model": refine_model,
                                        "prompt": f"{prompt2}\n{result1}",
                                        "images": [img_base64],
                                        "stream": False,
                                        "hardware": hardware  # 添加硬件参数
                                    }
                                else:
                                    payload = {
                                        "model": refine_model,
                                        "prompt": f"{prompt2}\n{result1}",
                                        "stream": False,
                                        "hardware": hardware  # 添加硬件参数
                                    }

                                try:
                                    response = requests.post(f"{CONFIG['OLLAMA_API_URL']}/generate", json=payload, timeout=120)
                                    response.raise_for_status()
                                    result2 = response.json().get("response", "")

                                    txt_path = os.path.join(os.path.dirname(file), f"{os.path.splitext(os.path.basename(file))[0]}.txt")
                                    if os.path.exists(txt_path):
                                        if action == "忽略":
                                            return f"{file}: 文件已存在，选择忽略。", elapsed_time1
                                        elif action == "覆盖":
                                            with open(txt_path, "w") as txt_file:
                                                txt_file.write(result2)
                                            return f"{file}: 处理完成，结果已覆盖到 {txt_path}", elapsed_time1
                                        elif action == "加入前面":
                                            with open(txt_path, "r+") as txt_file:
                                                content = txt_file.read()
                                                txt_file.seek(0, 0)
                                                txt_file.write(result2 + ", " + content)
                                            return f"{file}: 处理完成，结果已加入前面到 {txt_path}", elapsed_time1
                                        elif action == "加入后面":
                                            with open(txt_path, "a") as txt_file:
                                                txt_file.write(", " + result2)
                                            return f"{file}: 处理完成，结果已加入后面到 {txt_path}", elapsed_time1
                                    else:
                                        with open(txt_path, "w") as txt_file:
                                            txt_file.write(result2)
                                        return f"{file}: 处理完成，结果已保存到 {txt_path}", elapsed_time1

                                except requests.RequestException as e:
                                    logging.error(f"Error processing image: {e}")
                                    if "Read timed out" in str(e):
                                        restart_ollama()
                                    return f"{file}: 处理失败，请检查API连接。", elapsed_time1

                            else:
                                txt_path = os.path.join(os.path.dirname(file), f"{os.path.splitext(os.path.basename(file))[0]}.txt")
                                if os.path.exists(txt_path):
                                    if action == "忽略":
                                        return f"{file}: 文件已存在，选择忽略。", elapsed_time1
                                    elif action == "覆盖":
                                        with open(txt_path, "w") as txt_file:
                                            txt_file.write(result1)
                                        return f"{file}: 处理完成，结果已覆盖到 {txt_path}", elapsed_time1
                                    elif action == "加入前面":
                                        with open(txt_path, "r+") as txt_file:
                                            content = txt_file.read()
                                            txt_file.seek(0, 0)
                                            txt_file.write(result1 + ", " + content)
                                        return f"{file}: 处理完成，结果已加入前面到 {txt_path}", elapsed_time1
                                    elif action == "加入后面":
                                        with open(txt_path, "a") as txt_file:
                                            txt_file.write(", " + result1)
                                        return f"{file}: 处理完成，结果已加入后面到 {txt_path}", elapsed_time1
                                else:
                                    with open(txt_path, "w") as txt_file:
                                        txt_file.write(result1)
                                    return f"{file}: 处理完成，结果已保存到 {txt_path}", elapsed_time1

                            current_time = time.time()
                            elapsed_time = current_time - previous_time
                            previous_time = current_time
                            return result1, elapsed_time

                        with concurrent.futures.ThreadPoolExecutor(max_workers=int(concurrency)) as executor:
                            future_to_file = {executor.submit(process_file, file): file for file in files if txt_status[file]}
                            for future in concurrent.futures.as_completed(future_to_file):
                                file = future_to_file[future]
                                try:
                                    result, elapsed_time = future.result()
                                except Exception as e:
                                    result = f"{file}: 处理失败，错误: {e}"
                                    elapsed_time = 0
                                results.append(result)

                                processed_files += 1
                                last_10_times.append(elapsed_time)
                                if len(last_10_times) > 10:
                                    last_10_times.pop(0)
                                avg_time_per_file = sum(last_10_times) / len(last_10_times) if last_10_times else 0
                                remaining_time = avg_time_per_file * (total_files - processed_files)
                                logging.info(f"当前任务耗时: {elapsed_time:.2f}秒, 进度 {processed_files}/{total_files} files. 预计剩余时间: {format_remaining_time(remaining_time)}.")

                        return "\n".join(results)

                    process_multimodal_refine_button.click(
                        process_multimodal_refine,
                        inputs=[
                            model_dropdown,
                            prompt_input,
                            folder_input_multimodal_refine,
                            action_dropdown_multimodal_refine,
                            refine_model_dropdown_multimodal_refine,
                            enable_refine_model_multimodal,
                            use_image_checkbox_multimodal_refine,
                            hardware_dropdown_multimodal_refine,
                            prompt_input2,
                            concurrency_input
                        ],
                        outputs=multimodal_refine_output
                    )
                    stop_button_multimodal_refine.click(stop_task)

demo.launch(server_port=7888)