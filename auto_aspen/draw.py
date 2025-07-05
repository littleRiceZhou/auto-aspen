from PIL import Image, ImageDraw, ImageFont
import os

def draw_one_level(outer_size=(550, 300), net_power=654, fill_canvas=True):
    """
    绘制天然气压差发电机组示意图
    
    参数:
    outer_size: 外层矩形尺寸 (width, height) 单位像素，对应实际5.5m x 3m
    net_power: 净发电功率数值 (kW)
    fill_canvas: 是否铺满整个画布 (True: 完全铺满, False: 留边距)
    """
    outer_size = list(outer_size)
    
    # 从像素尺寸计算实际尺寸（除以100）
    actual_width = outer_size[0] / 100
    actual_height = outer_size[1] / 100
    
    # 创建图像，白色背景 - 根据内容自适应大小
    if fill_canvas:
        # 铺满画布，只留最小边距用于标注
        margin = 50
    else:
        # 保留较大边距
        margin = 80

    if outer_size[0] < 550:
        outer_size[0] = 550
    if outer_size[1] < 350:
        outer_size[1] = 350
    
    img_width = outer_size[0] + margin * 2
    img_height = outer_size[1] + margin * 2
    img = Image.new('RGB', (img_width, img_height), 'white')
    draw = ImageDraw.Draw(img)
    
    # 尝试加载字体，如果失败则使用默认字体
    try:
        # Windows系统中文字体
        font_large = ImageFont.truetype("simhei.ttf", 20)
        font_medium = ImageFont.truetype("simhei.ttf", 16)
        font_small = ImageFont.truetype("simhei.ttf", 12)
    except:
        try:
            # 尝试其他字体
            font_large = ImageFont.truetype("arial.ttf", 20)
            font_medium = ImageFont.truetype("arial.ttf", 16)
            font_small = ImageFont.truetype("arial.ttf", 12)
        except:
            # 使用默认字体
            font_large = ImageFont.load_default()
            font_medium = ImageFont.load_default()
            font_small = ImageFont.load_default()
    
    # 外层矩形位置 - 居中显示
    rect_x = margin
    rect_y = margin  
    rect_width = outer_size[0]
    rect_height = outer_size[1]
    
    # 绘制外层矩形
    draw.rectangle([rect_x, rect_y, rect_x + rect_width, rect_y + rect_height], 
                  outline='black', width=3)
    
    # 绘制尺寸标注
    # 上方尺寸标注
    draw.line([rect_x, rect_y - 20, rect_x + rect_width, rect_y - 20], fill='blue', width=2)
    draw.line([rect_x, rect_y - 25, rect_x, rect_y - 15], fill='blue', width=2)
    draw.line([rect_x + rect_width, rect_y - 25, rect_x + rect_width, rect_y - 15], fill='blue', width=2)
    draw.text((rect_x + rect_width//2 - 20, rect_y - 40), f"{actual_width}m", fill='blue', font=font_medium)
    
    # 左侧尺寸标注
    draw.line([rect_x - 20, rect_y, rect_x - 20, rect_y + rect_height], fill='blue', width=2)
    draw.line([rect_x - 25, rect_y, rect_x - 15, rect_y], fill='blue', width=2)
    draw.line([rect_x - 25, rect_y + rect_height, rect_x - 15, rect_y + rect_height], fill='blue', width=2)
    draw.text((rect_x - 45, rect_y + rect_height//2 - 10), f"{actual_height}m", fill='blue', font=font_medium)
    
    # 内部组件位置计算
    # 压差发电透平 (左侧三角形)
    turbine_x = rect_x + 80
    turbine_y = rect_y + rect_height//2
    turbine_points = [
        (turbine_x, turbine_y - 40),      # 左顶点
        (turbine_x + 80, turbine_y - 20), # 右上
        (turbine_x + 80, turbine_y + 20), # 右下
        (turbine_x, turbine_y + 40)       # 左下
    ]
    draw.polygon(turbine_points, outline='black', fill='lightblue', width=2)
    draw.text((turbine_x - 20, turbine_y - 70), "压差发电", fill='black', font=font_medium)
    draw.text((turbine_x - 50, turbine_y - 10), "透平", fill='black', font=font_medium)
    
    # 齿轮箱 (中间矩形)
    gearbox_x = turbine_x + 100
    gearbox_y = rect_y + rect_height//2 - 60
    gearbox_width = 80
    gearbox_height = 150
    
    # 绘制齿轮箱主体
    draw.rectangle([gearbox_x, gearbox_y, gearbox_x + gearbox_width, gearbox_y + gearbox_height],
                  outline='black', fill='lightgray', width=2)
    
    # 齿轮箱标签
    draw.text((gearbox_x + 10, gearbox_y - 25), "齿轮箱", fill='black', font=font_medium)
    
    # 防爆发电机 (右侧圆形)
    motor_x = gearbox_x + gearbox_width + 60
    motor_y = rect_y + rect_height//1.6
    motor_radius = 40
    
    # 绘制发电机圆形
    draw.ellipse([motor_x - motor_radius, motor_y - motor_radius, 
                 motor_x + motor_radius, motor_y + motor_radius],
                outline='black', fill='lightgreen', width=2)
    
    # 绘制M标识
    draw.text((motor_x - 10, motor_y - 10), "M", fill='black', font=font_large)
    
    # 发电机标签
    draw.text((motor_x + 50, motor_y - 10), "防爆发电机", fill='black', font=font_medium)
    
    # 绘制皮带连接
    belt_width = 8  # 皮带宽度
    belt_gap = 4    # 两根皮带之间的间隔
    
    # 透平到齿轮箱的皮带
    belt1_start_x = turbine_x + 80
    belt1_end_x = gearbox_x
    belt1_y = turbine_y
    
    # 上皮带
    draw.rectangle([belt1_start_x, belt1_y - belt_gap//2 - belt_width, 
                   belt1_end_x, belt1_y - belt_gap//2], 
                  fill='gray', outline='black', width=1)
    # 下皮带
    draw.rectangle([belt1_start_x, belt1_y + belt_gap//2, 
                   belt1_end_x, belt1_y + belt_gap//2 + belt_width], 
                  fill='gray', outline='black', width=1)
    
    # 齿轮箱到发电机的皮带
    belt2_start_x = gearbox_x + gearbox_width
    belt2_end_x = motor_x - motor_radius
    belt2_y = motor_y
    
    # 上皮带
    draw.rectangle([belt2_start_x, belt2_y - belt_gap//2 - belt_width, 
                   belt2_end_x, belt2_y - belt_gap//2], 
                  fill='gray', outline='black', width=1)
    # 下皮带
    draw.rectangle([belt2_start_x, belt2_y + belt_gap//2, 
                   belt2_end_x, belt2_y + belt_gap//2 + belt_width], 
                  fill='gray', outline='black', width=1)
    
    # 净发电功率标注
    power_text = f"净发电功率：{net_power}kW"
    draw.text((motor_x - 20, motor_y + motor_radius + 20), power_text, fill='red', font=font_medium)
    
    # 标题
    title = "天然气压差发电机组"
    title_x = rect_x + rect_width//2 - 80
    title_y = rect_y + rect_height + 30
    draw.text((title_x, title_y), title, fill='black', font=font_large)
    
    return img


def draw_two_level(outer_size=(450, 350), net_power=486, one_power=237, fill_canvas=True):
    """
    绘制双级天然气压差发电机组示意图
    
    参数:
    outer_size: 外层矩形尺寸 (width, height) 单位像素
    net_power: 总净发电功率数值 (kW)
    one_power: 1#透平净发电功率 (kW)
    fill_canvas: 是否铺满整个画布 (True: 铺满, False: 留边距)
    """
    outer_size = list(outer_size)
    # 从像素尺寸计算实际尺寸（除以100）
    actual_width = outer_size[0] / 100
    actual_height = outer_size[1] / 100
    
    two_power = net_power - one_power  # 2#透平功率
    
    # 创建图像，白色背景 - 根据内容自适应大小
    if fill_canvas:
        # 铺满画布，只留最小边距用于标注
        margin = 50
    else:
        # 保留较大边距
        margin = 80
    if outer_size[0] < 550:
        outer_size[0] = 550
    if outer_size[1] < 350:
        outer_size[1] = 350
    img_width = outer_size[0] + margin * 2
    img_height = outer_size[1] + margin * 2
    
    img = Image.new('RGB', (img_width, img_height), 'white')
    draw = ImageDraw.Draw(img)
    
    # 尝试加载字体，如果失败则使用默认字体
    try:
        # Windows系统中文字体
        font_large = ImageFont.truetype("simhei.ttf", 20)
        font_medium = ImageFont.truetype("simhei.ttf", 16)
        font_small = ImageFont.truetype("simhei.ttf", 12)
    except:
        try:
            # 尝试其他字体
            font_large = ImageFont.truetype("arial.ttf", 20)
            font_medium = ImageFont.truetype("arial.ttf", 16)
            font_small = ImageFont.truetype("arial.ttf", 12)
        except:
            # 使用默认字体
            font_large = ImageFont.load_default()
            font_medium = ImageFont.load_default()
            font_small = ImageFont.load_default()
    
    # 外层矩形位置 - 居中显示
    rect_x = margin
    rect_y = margin
    rect_width = outer_size[0]
    rect_height = outer_size[1]
    
    # 绘制外层矩形
    draw.rectangle([rect_x, rect_y, rect_x + rect_width, rect_y + rect_height], 
                  outline='black', width=3)
    
    # 绘制尺寸标注
    # 上方尺寸标注
    draw.line([rect_x, rect_y - 20, rect_x + rect_width, rect_y - 20], fill='blue', width=2)
    draw.line([rect_x, rect_y - 25, rect_x, rect_y - 15], fill='blue', width=2)
    draw.line([rect_x + rect_width, rect_y - 25, rect_x + rect_width, rect_y - 15], fill='blue', width=2)
    draw.text((rect_x + rect_width//2 - 20, rect_y - 40), f"{actual_width}m", fill='blue', font=font_medium)
    
    # 左侧尺寸标注
    draw.line([rect_x - 20, rect_y, rect_x - 20, rect_y + rect_height], fill='blue', width=2)
    draw.line([rect_x - 25, rect_y, rect_x - 15, rect_y], fill='blue', width=2)
    draw.line([rect_x - 25, rect_y + rect_height, rect_x - 15, rect_y + rect_height], fill='blue', width=2)
    draw.text((rect_x - 45, rect_y + rect_height//2 - 10), f"{actual_height}m", fill='blue', font=font_medium)
    
    # 齿轮箱 (中间竖直矩形条)
    gearbox_x = rect_x + rect_width//2 - 25
    gearbox_y = rect_y + 60
    gearbox_width = 50
    gearbox_height = rect_height - 180
    
    # 绘制齿轮箱主体
    draw.rectangle([gearbox_x, gearbox_y, gearbox_x + gearbox_width, gearbox_y + gearbox_height],
                  outline='black', fill='lightgray', width=2)
    
    # 齿轮箱标签
    draw.text((gearbox_x - 10, gearbox_y - 25), "齿轮箱", fill='black', font=font_medium)
    
    # 1#透平 (左侧三角形)
    turbine1_x = rect_x + 80
    turbine1_y = rect_y + 120
    turbine1_points = [
        (turbine1_x, turbine1_y - 30),        # 左顶点
        (turbine1_x + 60, turbine1_y - 15),   # 右上
        (turbine1_x + 60, turbine1_y + 15),   # 右下
        (turbine1_x, turbine1_y + 30)         # 左下
    ]
    draw.polygon(turbine1_points, outline='black', fill='lightblue', width=2)
    draw.text((turbine1_x - 20, turbine1_y - 50), "1#透平", fill='black', font=font_medium)
    
    # 1#透平功率标注
    power1_text = f"净发电功率：{one_power}kW"
    draw.text((turbine1_x - 40, turbine1_y - 70), power1_text, fill='black', font=font_small)
    
    # 2#透平 (右侧三角形)
    turbine2_x = rect_x + rect_width - 120
    turbine2_y = rect_y + 120
    turbine2_points = [
        (turbine2_x, turbine2_y - 15),        # 左上
        (turbine2_x, turbine2_y + 15),        # 左下
        (turbine2_x + 60, turbine2_y + 30),   # 右下
        (turbine2_x + 60, turbine2_y - 30)    # 右顶点
    ]
    draw.polygon(turbine2_points, outline='black', fill='lightblue', width=2)
    draw.text((turbine2_x + 10, turbine2_y - 50), "2#透平", fill='black', font=font_medium)
    
    # 2#透平功率标注
    power2_text = f"净发电功率：{two_power}kW"
    draw.text((turbine2_x - 10, turbine2_y - 70), power2_text, fill='black', font=font_small)
    
    # 发电机 (右下方圆形)
    motor_x = gearbox_x + gearbox_width + 60
    motor_y = rect_y + rect_height - 160
    motor_radius = 35
    
    # 绘制发电机圆形
    draw.ellipse([motor_x - motor_radius, motor_y - motor_radius, 
                 motor_x + motor_radius, motor_y + motor_radius],
                outline='black', fill='lightgreen', width=2)
    
    # 绘制M标识
    draw.text((motor_x - 10, motor_y - 10), "M", fill='black', font=font_large)
    
    # 发电机标签
    draw.text((motor_x + 45, motor_y - 10), "发电机", fill='black', font=font_medium)
    
    # 绘制皮带连接
    belt_width = 6  # 皮带宽度
    belt_gap = 3    # 两根皮带之间的间隔
    
    # 1#透平到齿轮箱的皮带
    belt1_start_x = turbine1_x + 60
    belt1_end_x = gearbox_x
    belt1_y = turbine1_y
    
    # 上皮带
    draw.rectangle([belt1_start_x, belt1_y - belt_gap//2 - belt_width, 
                   belt1_end_x, belt1_y - belt_gap//2], 
                  fill='blue', outline='black', width=1)
    # 下皮带
    draw.rectangle([belt1_start_x, belt1_y + belt_gap//2, 
                   belt1_end_x, belt1_y + belt_gap//2 + belt_width], 
                  fill='blue', outline='black', width=1)
    
    # 2#透平到齿轮箱的皮带
    belt2_start_x = gearbox_x + gearbox_width
    belt2_end_x = turbine2_x
    belt2_y = turbine2_y
    
    # 上皮带
    draw.rectangle([belt2_start_x, belt2_y - belt_gap//2 - belt_width, 
                   belt2_end_x, belt2_y - belt_gap//2], 
                  fill='blue', outline='black', width=1)
    # 下皮带
    draw.rectangle([belt2_start_x, belt2_y + belt_gap//2, 
                   belt2_end_x, belt2_y + belt_gap//2 + belt_width], 
                  fill='blue', outline='black', width=1)
    
    # 齿轮箱到发电机的皮带
    belt3_start_x = gearbox_x + gearbox_width
    belt3_end_x = motor_x - motor_radius
    belt3_y = motor_y
    
    # 上皮带
    draw.rectangle([belt3_start_x, belt3_y - belt_gap//2 - belt_width, 
                   belt3_end_x, belt3_y - belt_gap//2], 
                  fill='blue', outline='black', width=1)
    # 下皮带
    draw.rectangle([belt3_start_x, belt3_y + belt_gap//2, 
                   belt3_end_x, belt3_y + belt_gap//2 + belt_width], 
                  fill='blue', outline='black', width=1)
    
    # 总净发电功率标注
    total_power_text = f"总净发电功率：{net_power}kW"
    draw.text((rect_x + 20, rect_y + rect_height - 30), total_power_text, fill='red', font=font_medium)
    
    return img

def draw(outer_size=(550, 300), net_power=654, fill_canvas=True):
    if net_power > 1000:
        return draw_two_level(outer_size, net_power=net_power, one_power=1000, fill_canvas=fill_canvas)
    else:
        return draw_one_level(outer_size, net_power=net_power, fill_canvas=fill_canvas)

def main():
    """示例用法"""
    # 创建单级发电机组图像 - 铺满画布
    img1 = draw(outer_size=(300, 250), net_power=654, fill_canvas=True)
    img1.save("gas_generator_one_level_filled.png")
    print("已保存单级图像(铺满): gas_generator_one_level_filled.png")
    
    # 创建单级发电机组图像 - 留边距
    # img2 = draw(fill_canvas=False)
    # img2.save("gas_generator_one_level_margin.png")
    # print("已保存单级图像(留边距): gas_generator_one_level_margin.png")
    
    # # 创建自定义参数的双级图像 - 铺满画布
    # img3 = draw(outer_size=(500, 400), net_power=1600, fill_canvas=True)
    # img3.save("gas_generator_two_level_filled.png")
    # print("已保存双级图像(铺满): gas_generator_two_level_filled.png")
    
    # # 创建自定义参数的双级图像 - 留边距
    # img4 = draw(outer_size=(500, 400), net_power=1600, fill_canvas=False)
    # img4.save("gas_generator_two_level_margin.png")
    # print("已保存双级图像(留边距): gas_generator_two_level_margin.png")
    

if __name__ == "__main__":
    main()
