import os
from pptx import Presentation
from pathlib import Path
import re

# 导入现有的配置
try:
    from auto_aspen.docx_pdf import create_replacement_dict, sort_auto_aspen_keys_reverse, file_dir
except ImportError:
    # 备选方案，如果无法从 docx_pdf 导入
    file_dir = "static/re"
    def create_replacement_dict(parameter_values=None):
        return parameter_values or {}
    def sort_auto_aspen_keys_reverse(replacements):
        return sorted(replacements.keys(), key=len, reverse=True)

def replace_text_in_shape(shape, replacements):
    """
    在 PPT 形状中替换文本
    """
    replaced_count = 0
    
    # 获取文本框对象
    text_frame = None
    if hasattr(shape, 'has_text_frame') and shape.has_text_frame:
        text_frame = shape.text_frame
    elif hasattr(shape, 'text_frame'): # 处理表格单元格等直接拥有 text_frame 的对象
        text_frame = shape.text_frame
    
    if not text_frame:
        return 0
    
    # 排序键以避免子字符串冲突
    sorted_keys = sort_auto_aspen_keys_reverse(replacements)
    
    for paragraph in text_frame.paragraphs:
        for run in paragraph.runs:
            for old_text in sorted_keys:
                if old_text in run.text:
                    new_text = str(replacements[old_text])
                    # 精确匹配检查（类似于 docx 中的逻辑）
                    if old_text.startswith('auto_aspen_'):
                        escaped_text = re.escape(old_text)
                        pattern = escaped_text + r'(?=\D|$)'
                        if re.search(pattern, run.text):
                            run.text = run.text.replace(old_text, new_text)
                            replaced_count += 1
                    else:
                        run.text = run.text.replace(old_text, new_text)
                        replaced_count += 1
    return replaced_count

def replace_text_in_pptx(pptx_path, replacements, output_pptx_path=None, image_replacements=None):
    """
    读取 pptx 文件，替换指定文本和图片并保存
    """
    print(f"正在读取 PPT 模板: {pptx_path}")
    
    if not os.path.exists(pptx_path):
        raise FileNotFoundError(f"找不到模板文件: {pptx_path}")
        
    prs = Presentation(pptx_path)
    total_replaced = 0
    images_replaced = 0
    
    # 遍历所有幻灯片
    for slide in prs.slides:
        # 遍历幻灯片中的所有形状
        for shape in slide.shapes:
            # 处理图片替换 (通过占位符文本所在的形状位置插入图片)
            if image_replacements:
                for placeholder_text, img_info in image_replacements.items():
                    # 检查形状是否包含占位符文本
                    if hasattr(shape, "has_text_frame") and shape.has_text_frame:
                        if placeholder_text in shape.text_frame.text:
                            img_path = img_info.get("image_path")
                            if img_path and os.path.exists(img_path):
                                # 获取原形状的位置和大小
                                left = shape.left
                                top = shape.top
                                width = shape.width
                                height = shape.height
                                
                                # 在相同位置插入新图片
                                slide.shapes.add_picture(img_path, left, top, width, height)
                                
                                # 移除原来的占位符形状
                                sp = shape._element
                                sp.getparent().remove(sp)
                                
                                images_replaced += 1
                                print(f"成功在 PPT 中替换图片: {placeholder_text} -> {img_path}")
                                continue # 形状已被删除，跳过后续处理

            # 处理普通文本形状
            total_replaced += replace_text_in_shape(shape, replacements)
            
            # 处理表格
            if shape.has_table:
                for row in shape.table.rows:
                    for cell in row.cells:
                        total_replaced += replace_text_in_shape(cell, replacements)
            
            # 处理组合形状
            if shape.shape_type == 6:  # Group shape
                for sub_shape in shape.shapes:
                    total_replaced += replace_text_in_shape(sub_shape, replacements)

    # 确定输出路径
    if output_pptx_path is None:
        pptx_file = Path(pptx_path)
        output_pptx_path = os.path.join(file_dir, f"{pptx_file.stem}_generated.pptx")
    
    os.makedirs(os.path.dirname(output_pptx_path), exist_ok=True)
    prs.save(output_pptx_path)
    print(f"PPT 文档处理完成，共替换 {total_replaced} 处文本，{images_replaced} 处图片，已保存至: {output_pptx_path}")
    
    return output_pptx_path

def generate_pptx_document(parameters=None, text_to_images=None, output_name=None):
    """
    封装的 PPT 生成函数，供外部调用
    """
    template_path = "models/production-template.pptx"
    
    if not os.path.exists(template_path):
        return {
            "success": False,
            "error": f"PPT 模板文件不存在: {template_path}",
            "pptx_path": None
        }
    
    # 创建替换字典
    replacements = create_replacement_dict(parameters)
    
    # 确定输出文件名
    if output_name is None:
        output_name = "production_report_generated"
    
    output_pptx_path = f"{file_dir}/{output_name}.pptx"
    
    try:
        final_path = replace_text_in_pptx(
            template_path, 
            replacements, 
            output_pptx_path, 
            image_replacements=text_to_images
        )
        return {
            "success": True,
            "pptx_path": final_path,
            "parameters_replaced": len(replacements),
            "images_replaced": 1 if text_to_images else 0 # 简化统计
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "pptx_path": None
        }
