import docx
import os
from pathlib import Path
from docx.shared import RGBColor, Inches
from docx.oxml.shared import qn
import re

file_dir = "static/re"
os.makedirs(file_dir, exist_ok=True)

def get_auto_aspen_parameter_mapping():
    """
    根据文档中的auto_aspen参数创建完整的映射字典
    
    Returns:
        dict: 参数映射字典，键为auto_aspen参数名，值为对应的实际数值
    """
    return {
        # 接入参数 - 天然气处理机组
        "auto_aspen_1": "50000",      # 最大气量 (m³/d)
        "auto_aspen_2": "13.5",       # 进站压力 (MPaA)
        "auto_aspen_3": "25",         # 平均进气温度 (℃)
        "auto_aspen_4": "6.0",        # 出站压力 (MPaA)
        
        # 段落中的参数
        "auto_aspen_5": "654",        # 净发电功率 (kW)
        
        # 机组参数表
        "auto_aspen_6": "1",          # 透平机头数
        "auto_aspen_7": "TRT-1000",   # 机组型号
        "auto_aspen_8": "1",          # 级数
        "auto_aspen_9": "45",         # 机组排气温度 (℃)
        
        # 机组占地面积与操作重量
        "auto_aspen_10": "TRT-1000-EX", # 机组型号
        "auto_aspen_11": "8.5×3.2×3.8", # 机组整体外形尺寸 (长×宽×高 m)
        "auto_aspen_12": "12000",     # 机组整体重量/整体维修保养最大重量 (kg)
        
        # 项目整体经济效益核算
        "auto_aspen_13": "525.6",     # 年净发电量 (×10⁴kWh)
        "auto_aspen_14": "315.36",    # 年净发电收益 (万元)
        "auto_aspen_15": "184.0",     # 年节约标准煤 (吨)
        "auto_aspen_16": "505.4",     # 年减少CO₂排放 (吨)
        
        # 机组公用工程 - 电源设备参数
        "auto_aspen_17": "15",        # 辅油泵功率 (kW)
        "auto_aspen_18": "12",        # 润滑油电加热器功率 (kW)
        "auto_aspen_19": "8",         # 油雾分离器功率 (kW)
        "auto_aspen_20": "1",         # 发电机加热器=空间加热器功率 (kW)
        "auto_aspen_21": "3",         # PLC柜功率 (kW)
        
        # 机组公用工程 - 水油气参数
        "auto_aspen_22": "850",       # 油冷器流量 (m³/Hr)
        "auto_aspen_23": "45",        # 齿轮箱润滑油流量 (L/min)
        "auto_aspen_24": "120",       # 氮气-干气密封气体流量 (Nm³/h)
        "auto_aspen_25": "95",        # 压缩空气-气动阀气体流量 (Nm³/h)
    }

def create_replacement_dict(parameter_values=None):
    """
    创建用于文档替换的字典
    
    Args:
        parameter_values (dict, optional): 自定义参数值，如果不提供则使用默认值
    
    Returns:
        dict: 用于替换的字典，键为原文档中的占位符，值为新的数值
    """
    # 获取默认参数映射
    default_params = get_auto_aspen_parameter_mapping()
    
    # 如果提供了自定义值，则更新默认值
    if parameter_values:
        default_params.update(parameter_values)
    
    return default_params

def replace_text_in_paragraph(paragraph, old_text, new_text):
    """
    在段落中替换文本，保持原始格式
    
    Args:
        paragraph: docx段落对象
        old_text (str): 要替换的文本
        new_text (str): 新文本
    
    Returns:
        int: 替换次数
    """
    if old_text not in paragraph.text:
        return 0
    
    # 收集所有runs的文本和格式信息
    runs_info = []
    for run in paragraph.runs:
        runs_info.append({
            'text': run.text,
            'bold': run.bold,
            'italic': run.italic,
            'underline': run.underline,
            'font_name': run.font.name,
            'font_size': run.font.size,
            'font_color': run.font.color.rgb if run.font.color.rgb else None,
        })
    
    # 合并所有文本
    full_text = ''.join([info['text'] for info in runs_info])
    
    # 如果不包含要替换的文本，直接返回
    if old_text not in full_text:
        return 0
    
    # 执行替换
    new_full_text = full_text.replace(old_text, new_text)
    replacement_count = full_text.count(old_text)
    
    # 清空原有runs
    for run in paragraph.runs:
        run.clear()
    
    # 重新分配文本到runs，尽量保持原格式
    char_index = 0
    run_index = 0
    
    for i, char in enumerate(new_full_text):
        # 找到当前字符应该属于哪个原始run的格式
        original_char_index = 0
        target_run_info = runs_info[0]  # 默认使用第一个run的格式
        
        for j, info in enumerate(runs_info):
            if original_char_index <= char_index < original_char_index + len(info['text']):
                target_run_info = info
                break
            original_char_index += len(info['text'])
        
        # 如果是新增的字符（替换产生的），使用前一个字符的格式
        if char_index >= len(full_text):
            # 使用最后一个包含被替换文本的run的格式
            for j, info in enumerate(runs_info):
                if old_text in info['text']:
                    target_run_info = info
                    break
        
        # 创建或获取当前run
        if run_index >= len(paragraph.runs):
            run = paragraph.add_run()
        else:
            run = paragraph.runs[run_index]
        
        # 如果当前run为空或者格式不同，创建新run
        if (run.text == '' or 
            run.bold != target_run_info['bold'] or
            run.italic != target_run_info['italic'] or
            run.underline != target_run_info['underline']):
            
            if run.text != '':
                run = paragraph.add_run()
                run_index += 1
            
            # 应用格式
            run.bold = target_run_info['bold']
            run.italic = target_run_info['italic']
            run.underline = target_run_info['underline']
            if target_run_info['font_name']:
                run.font.name = target_run_info['font_name']
            if target_run_info['font_size']:
                run.font.size = target_run_info['font_size']
            if target_run_info['font_color']:
                run.font.color.rgb = target_run_info['font_color']
        
        run.text += char
        char_index += 1
    
    return replacement_count

def replace_text_in_cell(cell, old_text, new_text):
    """
    在表格单元格中替换文本，保持原始格式
    
    Args:
        cell: docx表格单元格对象
        old_text (str): 要替换的文本
        new_text (str): 新文本
    
    Returns:
        int: 替换次数
    """
    total_replacements = 0
    for paragraph in cell.paragraphs:
        total_replacements += replace_text_in_paragraph(paragraph, old_text, new_text)
    return total_replacements

def replace_text_in_docx_with_formatting(docx_path, replacements, output_docx_path=None):
    """
    读取docx文件，替换指定文本并保持格式，然后保存为新的docx文件
    
    Args:
        docx_path (str): 输入的docx文件路径
        replacements (dict): 需要替换的文本字典，格式为 {old_text: new_text}
        output_docx_path (str, optional): 输出docx文件路径，如果不指定则使用原文件名加_modified后缀
    
    Returns:
        str: 生成的docx文件路径
    """
    print(f"正在读取文档: {docx_path}")
    
    # 加载docx文档
    doc = docx.Document(docx_path)
    
    # 按auto_aspen编号倒序排序替换键
    sorted_keys = sort_auto_aspen_keys_reverse(replacements)
    print(f"替换顺序: {sorted_keys}")
    
    # 替换段落中的文本
    replaced_count = 0
    for paragraph in doc.paragraphs:
        for old_text in sorted_keys:
            new_text = replacements[old_text]
            count = replace_text_in_paragraph(paragraph, old_text, new_text)
            if count > 0:
                print(f"在段落中找到并替换: '{old_text}' -> '{new_text}' ({count}次)")
                replaced_count += count
    
    # 替换表格中的文本
    for table in doc.tables:
        for row in table.rows:
            for cell in row.cells:
                for old_text in sorted_keys:
                    new_text = replacements[old_text]
                    count = replace_text_in_cell(cell, old_text, new_text)
                    if count > 0:
                        print(f"在表格中找到并替换: '{old_text}' -> '{new_text}' ({count}次)")
                        replaced_count += count
    
    print(f"总共进行了 {replaced_count} 次替换")
    
    # 确定输出docx路径
    if output_docx_path is None:
        docx_file = Path(docx_path)
        output_docx_path = docx_file.parent / f"{docx_file.stem}_modified.docx"
    
    # 保存修改后的docx文件
    doc.save(output_docx_path)
    print(f"修改后的文档已保存: {output_docx_path}")
    
    return str(output_docx_path)

# 保留原有的简单替换函数作为备选
def replace_text_in_docx(docx_path, replacements, output_docx_path=None):
    """
    读取docx文件，替换指定文本，并保存为新的docx文件（简单模式，不保持格式）
    
    Args:
        docx_path (str): 输入的docx文件路径
        replacements (dict): 需要替换的文本字典，格式为 {old_text: new_text}
        output_docx_path (str, optional): 输出docx文件路径，如果不指定则使用原文件名加_modified后缀
    
    Returns:
        str: 生成的docx文件路径
    """
    print(f"正在读取文档: {docx_path}")
    
    # 加载docx文档
    doc = docx.Document(docx_path)
    
    # 按auto_aspen编号倒序排序替换键
    sorted_keys = sort_auto_aspen_keys_reverse(replacements)
    print(f"替换顺序: {sorted_keys}")
    
    # 替换段落中的文本
    replaced_count = 0
    for paragraph in doc.paragraphs:
        for old_text in sorted_keys:
            new_text = replacements[old_text]
            if old_text in paragraph.text:
                print(f"在段落中找到并替换: '{old_text}' -> '{new_text}'")
                paragraph.text = paragraph.text.replace(old_text, new_text)
                replaced_count += 1
    
    # 替换表格中的文本
    for table in doc.tables:
        for row in table.rows:
            for cell in row.cells:
                for old_text in sorted_keys:
                    new_text = replacements[old_text]
                    if old_text in cell.text:
                        print(f"在表格中找到并替换: '{old_text}' -> '{new_text}'")
                        cell.text = cell.text.replace(old_text, new_text)
                        replaced_count += 1
    
    print(f"总共进行了 {replaced_count} 次替换")
    
    # 确定输出docx路径
    if output_docx_path is None:
        docx_file = Path(docx_path)
        output_docx_path = docx_file.parent / f"{docx_file.stem}_modified.docx"
    
    # 保存修改后的docx文件
    doc.save(output_docx_path)
    print(f"修改后的文档已保存: {output_docx_path}")
    
    return str(output_docx_path)

def convert_to_pdf_with_libre_office(docx_path):
    """
    尝试使用LibreOffice转换docx为PDF
    """
    output_dir = Path(docx_path).parent
    cmd = f'soffice --headless --convert-to pdf --outdir "{output_dir}" "{docx_path}"'
    print(f"尝试使用LibreOffice转换: {cmd}")
    
    try:
        result = os.system(cmd)
        if result == 0:
            pdf_path = output_dir / f"{Path(docx_path).stem}.pdf"
            if pdf_path.exists():
                print(f"成功使用LibreOffice生成PDF: {pdf_path}")
                return str(pdf_path)
        print("LibreOffice转换失败或未安装")
        return None
    except Exception as e:
        print(f"LibreOffice转换出错: {e}")
        return None

def process_document_with_parameters(docx_path, custom_parameters=None, image_replacements=None, text_to_image_replacements=None, output_docx_path=None, convert_to_pdf=True, preserve_formatting=True):
    """
    使用参数映射处理文档的主函数（支持文本替换、图片替换、文字转图片）
    
    Args:
        docx_path (str): 输入的docx文件路径
        custom_parameters (dict, optional): 自定义参数值
        image_replacements (dict, optional): 图片替换字典（图片换图片）
        text_to_image_replacements (dict, optional): 文字到图片替换字典（文字换图片）
        output_docx_path (str, optional): 输出docx文件路径
        convert_to_pdf (bool): 是否转换为PDF
        preserve_formatting (bool): 是否保持原始格式
    
    Returns:
        dict: 包含处理结果的字典
    """
    try:
        # 创建替换字典
        replacements = create_replacement_dict(custom_parameters)
        
        # 选择替换方法
        if preserve_formatting:
            print("使用格式保持模式进行文本替换...")
            modified_docx_path = replace_text_in_docx_with_formatting(docx_path, replacements, output_docx_path)
        else:
            print("使用简单模式进行文本替换...")
            modified_docx_path = replace_text_in_docx(docx_path, replacements, output_docx_path)
        
        result = {
            "success": True,
            "modified_docx_path": modified_docx_path,
            "pdf_path": None,
            "replacements_made": len(replacements),
            "images_replaced": 0,
            "text_to_image_replaced": 0
        }
        
        # 处理图片替换（图片换图片）
        if image_replacements:
            print("\n开始处理图片替换（图片换图片）...")
            image_result = replace_images_in_docx(modified_docx_path, image_replacements, modified_docx_path)
            if image_result["success"]:
                result["images_replaced"] = image_result["images_replaced"]
                print(f"成功替换 {image_result['images_replaced']} 个图片")
            else:
                print(f"图片替换失败: {image_result['error']}")
        
        # 处理文字到图片替换
        if text_to_image_replacements:
            print("\n开始处理文字到图片替换...")
            text_to_image_result = replace_text_with_images_in_docx(modified_docx_path, text_to_image_replacements, modified_docx_path)
            if text_to_image_result["success"]:
                result["text_to_image_replaced"] = text_to_image_result["text_to_image_replacements"]
                print(f"成功将 {text_to_image_result['text_to_image_replacements']} 处文字替换为图片")
            else:
                print(f"文字到图片替换失败: {text_to_image_result['error']}")
        
        # 尝试转换为PDF
        if convert_to_pdf:
            print("\n尝试转换为PDF...")
            pdf_path = convert_to_pdf_with_libre_office(modified_docx_path)
            result["pdf_path"] = pdf_path
        
        return result
        
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "modified_docx_path": None,
            "pdf_path": None,
            "replacements_made": 0,
            "images_replaced": 0,
            "text_to_image_replaced": 0
        }

def main():
    """主函数：演示如何使用参数映射功能"""
    docx_path = "models/RE_template.docx"  # 使用模板文件
    
    if not os.path.exists(docx_path):
        print(f"错误：找不到文件 {docx_path}")
        return
    
    # 自定义一些参数值
    custom_parameters = {
        "auto_aspen_1": "45000",    # 最大气量
        "auto_aspen_2": "13.8",     # 进站压力
        "auto_aspen_3": "30",       # 平均进气温度
        "auto_aspen_5": "680",      # 净发电功率
    }
    
    print("开始处理文档...")
    result = process_document_with_parameters(
        docx_path, 
        custom_parameters,
        convert_to_pdf=True
    )
    
    if result["success"]:
        print(f"\n文档处理成功！")
        print(f"修改后的docx文件: {result['modified_docx_path']}")
        if result["pdf_path"]:
            print(f"PDF文件: {result['pdf_path']}")
        print(f"共进行了 {result['replacements_made']} 个参数的替换")
    else:
        print(f"\n文档处理失败: {result['error']}")

def generate_document(parameters=None, images=None, text_to_images=None, output_name=None, convert_pdf=True, preserve_formatting=True):
    """
    简化的API函数：生成带有指定参数、图片替换、文字转图片的文档
    
    Args:
        parameters (dict, optional): 自定义参数值，格式为 {"auto_aspen_1": "value", ...}
        images (dict, optional): 图片替换字典（图片换图片），格式为 {"old_image.png": {"new_path": "path", "width": w, "height": h}}
        text_to_images (dict, optional): 文字到图片替换字典，格式为 {"文字": {"image_path": "path", "width": w, "height": h}}
        output_name (str, optional): 输出文件名（不含扩展名），默认为"RE_generated"
        convert_pdf (bool): 是否同时生成PDF文件
        preserve_formatting (bool): 是否保持原始格式（字体、颜色等）
    
    Returns:
        dict: 包含生成文件路径的结果字典
    
    Example:
        # 使用默认参数生成文档，保持格式
        result = generate_document()
        
        # 使用自定义参数生成文档，保持格式
        params = {
            "auto_aspen_1": "60000",  # 最大气量
            "auto_aspen_2": "14.0",   # 进站压力
            "auto_aspen_5": "800"     # 净发电功率
        }
        result = generate_document(parameters=params, output_name="custom_report", preserve_formatting=True)
        
        # 同时替换参数和图片
        images = {
            "chart1.png": {
                "new_path": "static/re/new_chart.png",
                "width": 6.0,
                "height": 4.0
            }
        }
        result = generate_document(parameters=params, images=images, output_name="full_custom")
        
        # 将文字替换为图片
        text_to_images = {
            "[图表1]": {
                "image_path": "models/demo.png",
                "width": 5.0,
                "height": 3.0
            },
            "【插入图片】": {
                "image_path": "models/demo.png",
                "width": 4.0,
                "height": 2.5
            }
        }
        result = generate_document(parameters=params, text_to_images=text_to_images, output_name="text_to_image")
        
        # 使用简单模式（不保持格式，但速度更快）
        result = generate_document(parameters=params, preserve_formatting=False)
    """
    template_path = "models/RE_template.docx"
    
    if not os.path.exists(template_path):
        return {
            "success": False,
            "error": f"模板文件不存在: {template_path}",
            "docx_path": None,
            "pdf_path": None
        }
    
    # 确定输出文件名
    if output_name is None:
        output_name = "RE_generated"
    
    output_docx_path = f"{file_dir}/{output_name}.docx"
    
    # 处理文档
    result = process_document_with_parameters(
        template_path,
        parameters,
        images,
        text_to_images,
        output_docx_path,
        convert_pdf,
        preserve_formatting
    )
    
    return {
        "success": result["success"],
        "error": result.get("error"),
        "docx_path": result["modified_docx_path"],
        "pdf_path": result["pdf_path"],
        "parameters_replaced": result["replacements_made"],
        "images_replaced": result["images_replaced"],
        "text_to_image_replaced": result["text_to_image_replaced"]
    }

def sort_auto_aspen_keys_reverse(replacements):
    """
    对auto_aspen参数按编号倒序排序，其他参数保持原顺序
    
    Args:
        replacements (dict): 替换字典
    
    Returns:
        list: 按auto_aspen编号倒序排列的键列表
    """
    auto_aspen_keys = []
    other_keys = []
    
    for key in replacements.keys():
        if key.startswith("auto_aspen_"):
            # 提取数字部分
            match = re.search(r'auto_aspen_(\d+)', key)
            if match:
                number = int(match.group(1))
                auto_aspen_keys.append((key, number))
            else:
                other_keys.append(key)
        else:
            other_keys.append(key)
    
    # 按数字倒序排序auto_aspen参数
    auto_aspen_keys.sort(key=lambda x: x[1], reverse=True)
    sorted_auto_aspen_keys = [key for key, _ in auto_aspen_keys]
    
    # 返回排序后的完整键列表
    return sorted_auto_aspen_keys + other_keys

def find_images_in_document(doc):
    """
    查找文档中的所有图片
    
    Args:
        doc: docx文档对象
    
    Returns:
        list: 包含图片信息的列表，每个元素为 {'paragraph': paragraph, 'run': run, 'inline_shape': shape, 'image_name': name}
    """
    images = []
    
    # 遍历段落中的图片
    for paragraph in doc.paragraphs:
        for run in paragraph.runs:
            for inline_shape in run.element.xpath('.//a:blip', namespaces={'a': 'http://schemas.openxmlformats.org/drawingml/2006/main'}):
                # 获取图片的关系ID
                rId = inline_shape.get(qn('r:embed'))
                if rId:
                    try:
                        # 获取图片文件名
                        image_part = doc.part.related_parts[rId]
                        image_name = os.path.basename(image_part.partname)
                        
                        images.append({
                            'paragraph': paragraph,
                            'run': run,
                            'rId': rId,
                            'image_name': image_name,
                            'image_part': image_part
                        })
                    except:
                        continue
    
    # 遍历表格中的图片
    for table in doc.tables:
        for row in table.rows:
            for cell in row.cells:
                for paragraph in cell.paragraphs:
                    for run in paragraph.runs:
                        for inline_shape in run.element.xpath('.//a:blip', namespaces={'a': 'http://schemas.openxmlformats.org/drawingml/2006/main'}):
                            rId = inline_shape.get(qn('r:embed'))
                            if rId:
                                try:
                                    image_part = doc.part.related_parts[rId]
                                    image_name = os.path.basename(image_part.partname)
                                    
                                    images.append({
                                        'paragraph': paragraph,
                                        'run': run,
                                        'rId': rId,
                                        'image_name': image_name,
                                        'image_part': image_part
                                    })
                                except:
                                    continue
    
    return images

def replace_image_by_name(doc, old_image_name, new_image_path, width=None, height=None):
    """
    根据图片名称替换文档中的图片
    
    Args:
        doc: docx文档对象
        old_image_name (str): 要替换的图片名称（如 "image1.png"）
        new_image_path (str): 新图片的文件路径
        width (float, optional): 新图片宽度（英寸）
        height (float, optional): 新图片高度（英寸）
    
    Returns:
        int: 替换的图片数量
    """
    if not os.path.exists(new_image_path):
        print(f"错误：新图片文件不存在 {new_image_path}")
        return 0
    
    replaced_count = 0
    images = find_images_in_document(doc)
    
    for image_info in images:
        if old_image_name in image_info['image_name'] or image_info['image_name'].endswith(old_image_name):
            try:
                # 删除原有图片
                run = image_info['run']
                
                # 清除run中的所有内容
                run.clear()
                
                # 添加新图片
                if width and height:
                    run.add_picture(new_image_path, width=Inches(width), height=Inches(height))
                else:
                    run.add_picture(new_image_path)
                
                print(f"成功替换图片: {image_info['image_name']} -> {new_image_path}")
                replaced_count += 1
                
            except Exception as e:
                print(f"替换图片时出错: {e}")
    
    return replaced_count

def replace_image_by_position(doc, paragraph_index, new_image_path, width=None, height=None):
    """
    根据段落位置替换图片
    
    Args:
        doc: docx文档对象
        paragraph_index (int): 段落索引（从0开始）
        new_image_path (str): 新图片的文件路径
        width (float, optional): 新图片宽度（英寸）
        height (float, optional): 新图片高度（英寸）
    
    Returns:
        bool: 是否成功替换
    """
    if not os.path.exists(new_image_path):
        print(f"错误：新图片文件不存在 {new_image_path}")
        return False
    
    try:
        if paragraph_index >= len(doc.paragraphs):
            print(f"错误：段落索引超出范围 {paragraph_index}")
            return False
        
        paragraph = doc.paragraphs[paragraph_index]
        
        # 查找该段落中的图片
        image_found = False
        for run in paragraph.runs:
            if run.element.xpath('.//a:blip', namespaces={'a': 'http://schemas.openxmlformats.org/drawingml/2006/main'}):
                # 清除run中的所有内容
                run.clear()
                
                # 添加新图片
                if width and height:
                    run.add_picture(new_image_path, width=Inches(width), height=Inches(height))
                else:
                    run.add_picture(new_image_path)
                
                print(f"成功在段落 {paragraph_index} 位置替换图片: {new_image_path}")
                image_found = True
                break
        
        if not image_found:
            print(f"在段落 {paragraph_index} 中未找到图片")
            return False
        
        return True
        
    except Exception as e:
        print(f"替换图片时出错: {e}")
        return False

def add_image_to_paragraph(doc, paragraph_index, image_path, width=None, height=None):
    """
    在指定段落添加图片
    
    Args:
        doc: docx文档对象
        paragraph_index (int): 段落索引（从0开始）
        image_path (str): 图片文件路径
        width (float, optional): 图片宽度（英寸）
        height (float, optional): 图片高度（英寸）
    
    Returns:
        bool: 是否成功添加
    """
    if not os.path.exists(image_path):
        print(f"错误：图片文件不存在 {image_path}")
        return False
    
    try:
        if paragraph_index >= len(doc.paragraphs):
            print(f"错误：段落索引超出范围 {paragraph_index}")
            return False
        
        paragraph = doc.paragraphs[paragraph_index]
        run = paragraph.runs[0] if paragraph.runs else paragraph.add_run()
        
        # 添加图片
        if width and height:
            run.add_picture(image_path, width=Inches(width), height=Inches(height))
        else:
            run.add_picture(image_path)
        
        print(f"成功在段落 {paragraph_index} 添加图片: {image_path}")
        return True
        
    except Exception as e:
        print(f"添加图片时出错: {e}")
        return False

def create_image_replacement_dict():
    """
    创建图片替换映射字典的示例
    
    Returns:
        dict: 图片替换映射字典
    """
    return {
        # 格式: "原图片名称": {"new_path": "新图片路径", "width": 宽度, "height": 高度}
        "chart1.png": {
            "new_path": "static/re/new_chart1.png",
            "width": 6.0,  # 英寸
            "height": 4.0
        },
        "diagram1.jpg": {
            "new_path": "static/re/new_diagram1.jpg",
            "width": 5.0,
            "height": 3.5
        }
    }

def replace_images_in_docx(docx_path, image_replacements, output_docx_path=None):
    """
    批量替换docx文档中的图片
    
    Args:
        docx_path (str): 输入的docx文件路径
        image_replacements (dict): 图片替换字典，格式为 {image_name: {"new_path": path, "width": w, "height": h}}
        output_docx_path (str, optional): 输出docx文件路径
    
    Returns:
        dict: 处理结果
    """
    print(f"正在读取文档进行图片替换: {docx_path}")
    
    try:
        # 加载docx文档
        doc = docx.Document(docx_path)
        
        # 查找所有图片
        images = find_images_in_document(doc)
        print(f"文档中找到 {len(images)} 个图片")
        
        replaced_count = 0
        
        # 执行图片替换
        for old_name, replacement_info in image_replacements.items():
            new_path = replacement_info.get("new_path")
            width = replacement_info.get("width")
            height = replacement_info.get("height")
            
            if not new_path or not os.path.exists(new_path):
                print(f"跳过 {old_name}: 新图片路径无效或文件不存在")
                continue
            
            count = replace_image_by_name(doc, old_name, new_path, width, height)
            replaced_count += count
        
        # 确定输出路径
        if output_docx_path is None:
            docx_file = Path(docx_path)
            output_docx_path = docx_file.parent / f"{docx_file.stem}_images_replaced.docx"
        
        # 保存修改后的文档
        doc.save(output_docx_path)
        print(f"图片替换完成，文档已保存: {output_docx_path}")
        
        return {
            "success": True,
            "modified_docx_path": str(output_docx_path),
            "images_replaced": replaced_count,
            "total_images_found": len(images)
        }
        
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "images_replaced": 0
        }

def replace_text_with_image(paragraph, old_text, image_path, width=None, height=None):
    """
    在段落中将文字替换为图片
    
    Args:
        paragraph: docx段落对象
        old_text (str): 要替换的文字
        image_path (str): 图片路径
        width (float, optional): 图片宽度（英寸）
        height (float, optional): 图片高度（英寸）
    
    Returns:
        int: 替换次数
    """
    if old_text not in paragraph.text:
        return 0
    
    if not os.path.exists(image_path):
        print(f"错误：图片文件不存在 {image_path}")
        return 0
    
    try:
        # 获取段落的完整文本
        full_text = paragraph.text
        
        if old_text not in full_text:
            return 0
        
        # 计算替换次数
        replacement_count = full_text.count(old_text)
        
        # 清空段落中的所有runs
        for run in paragraph.runs:
            run.clear()
        
        # 按old_text分割文本
        parts = full_text.split(old_text)
        
        # 重新构建段落内容
        for i, part in enumerate(parts):
            if i > 0:  # 在每个分割点插入图片
                # 添加图片
                run = paragraph.add_run()
                if width and height:
                    run.add_picture(image_path, width=Inches(width), height=Inches(height))
                else:
                    run.add_picture(image_path)
            
            if part:  # 添加文本部分
                paragraph.add_run(part)
        
        print(f"成功将文字 '{old_text}' 替换为图片 {image_path} ({replacement_count}次)")
        return replacement_count
        
    except Exception as e:
        print(f"将文字替换为图片时出错: {e}")
        return 0

def replace_text_with_image_in_cell(cell, old_text, image_path, width=None, height=None):
    """
    在表格单元格中将文字替换为图片
    
    Args:
        cell: docx表格单元格对象
        old_text (str): 要替换的文字
        image_path (str): 图片路径
        width (float, optional): 图片宽度（英寸）
        height (float, optional): 图片高度（英寸）
    
    Returns:
        int: 替换次数
    """
    total_replacements = 0
    for paragraph in cell.paragraphs:
        total_replacements += replace_text_with_image(paragraph, old_text, image_path, width, height)
    return total_replacements

def replace_text_with_images_in_docx(docx_path, text_to_image_replacements, output_docx_path=None):
    """
    将docx文档中的指定文字替换为图片
    
    Args:
        docx_path (str): 输入的docx文件路径
        text_to_image_replacements (dict): 文字到图片的替换字典
            格式: {text: {"image_path": path, "width": w, "height": h}}
        output_docx_path (str, optional): 输出docx文件路径
    
    Returns:
        dict: 处理结果
    """
    print(f"正在读取文档进行文字到图片替换: {docx_path}")
    
    try:
        # 加载docx文档
        doc = docx.Document(docx_path)
        
        total_replacements = 0
        
        # 先按文字长度倒序排序，避免短文字被长文字影响
        sorted_texts = sorted(text_to_image_replacements.keys(), key=len, reverse=True)
        
        # 替换段落中的文字
        for paragraph in doc.paragraphs:
            for text in sorted_texts:
                replacement_info = text_to_image_replacements[text]
                image_path = replacement_info.get("image_path")
                width = replacement_info.get("width")
                height = replacement_info.get("height")
                
                if not image_path:
                    continue
                
                count = replace_text_with_image(paragraph, text, image_path, width, height)
                total_replacements += count
        
        # 替换表格中的文字
        for table in doc.tables:
            for row in table.rows:
                for cell in row.cells:
                    for text in sorted_texts:
                        replacement_info = text_to_image_replacements[text]
                        image_path = replacement_info.get("image_path")
                        width = replacement_info.get("width")
                        height = replacement_info.get("height")
                        
                        if not image_path:
                            continue
                        
                        count = replace_text_with_image_in_cell(cell, text, image_path, width, height)
                        total_replacements += count
        
        # 确定输出路径
        if output_docx_path is None:
            docx_file = Path(docx_path)
            output_docx_path = docx_file.parent / f"{docx_file.stem}_text_to_images.docx"
        
        # 保存修改后的文档
        doc.save(output_docx_path)
        print(f"文字到图片替换完成，共替换 {total_replacements} 次，文档已保存: {output_docx_path}")
        
        return {
            "success": True,
            "modified_docx_path": str(output_docx_path),
            "text_to_image_replacements": total_replacements
        }
        
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "text_to_image_replacements": 0
        }

def create_text_to_image_mapping():
    """
    创建文字到图片替换映射的示例
    
    Returns:
        dict: 文字到图片的替换字典
    """
    return {
        # 格式: "要替换的文字": {"image_path": "图片路径", "width": 宽度, "height": 高度}
        "[图表1]": {
            "image_path": "models/demo.png",
            "width": 5.0,
            "height": 3.0
        },
        "[流程图]": {
            "image_path": "models/demo.png", 
            "width": 6.0,
            "height": 4.0
        },
        "[示意图]": {
            "image_path": "models/demo.png",
            "width": 4.5,
            "height": 3.5
        },
        "【插入图片】": {
            "image_path": "models/demo.png",
            "width": 3.0,
            "height": 2.0
        }
    }

if __name__ == "__main__":
    # 运行测试
    
    print("\n" + "="*50)
    print("测试文本替换功能")
    print("="*50 + "\n")
    
    custom_params = get_auto_aspen_parameter_mapping()
    result1 = generate_document(parameters=custom_params, output_name="demo_custom_formatted", convert_pdf=False, preserve_formatting=False)
    print(f"文本替换结果: {result1}")
    
    print("\n" + "="*50)
    print("测试图片替换功能")
    print("="*50 + "\n")
    
    # 检查模板文件中的图片
    template_path = "models/RE_template.docx"
    
    # 使用demo.png作为替换图片
    demo_image = "models/demo.png"
    if os.path.exists(demo_image):
        text_to_image_replacements = {
            "auto_aspen_image_1": {
                "image_path": "models/demo.png",
                "width": 5.0,
                "height": 3.0
                },
        }
        # 测试全功能（文本+图片+文字转图片）
        print(f"\n全功能测试（文本+图片+文字转图片）:")
        full_result = generate_document(
            parameters=custom_params,
            images=[],
            text_to_images=text_to_image_replacements,
            output_name="demo_full_features",
            convert_pdf=False,
            preserve_formatting=False
        )
        print(f"全功能测试结果: {full_result}")
        
    else:
        print(f"\n警告: Demo图片不存在: {demo_image}")
        print("将跳过图片相关测试")
    
    print("\n" + "="*50)
    print("测试完成")
    print("="*50)
    
