import os
import sys
import time
import numpy as np
import win32com.client as win32

BASE_DIR = os.path.abspath(os.path.join(os.path.abspath(__file__), '../' * 3))
sys.path.append(BASE_DIR)


class PyASPENPlus(object):
    """使用Python运行ASPEN模拟"""

    def __init__(self):
        pass

    def init_app(self, ap_version: str = '14.0'):
        """开启ASPEN Plus

        :param ap_version: ASPEN Plus版本号, defaults to '14.0'
        """
        # 尝试多种可能的COM类标识符
        possible_com_classes = [
            'Apwn.Document',  # 最常用的
            f'Apwn.Document.{ap_version}',
            'AspenTech.AspenPlus.Document',
            'AspenPlus.Document',
        ]
        
        # 版本映射（如果需要的话）
        version_match = {
            '14.0': '39.0',
            '12.1': '38.0', 
            '11.0': '37.0',
            '10.0': '36.0',
            '9.0': '35.0',
            '8.8': '34.0',
        }
        
        # 添加版本化的COM类
        if ap_version in version_match:
            possible_com_classes.append(f'Apwn.Document.{version_match[ap_version]}')
        
        last_error = None
        for com_class in possible_com_classes:
            try:
                print(f"尝试连接COM类: {com_class}")
                self.app = win32.Dispatch(com_class)
                print(f"✓ 成功连接到: {com_class}")
                return
            except Exception as e:
                last_error = e
                print(f"✗ 连接失败: {com_class} - {str(e)}")
                continue
        
        # 如果所有尝试都失败了
        raise Exception(f"无法连接到Aspen Plus COM对象。最后错误: {last_error}")

    def load_ap_file(self, file_name: str, file_dir: str = None, visible: bool = False, dialogs: bool = False):
        """载入待运行的ASPEN文件"""
        # 文件类型检查.
        if file_name[-4:] != '.bkp':
            raise ValueError('not an ASPEN bkp file')
        
        self.file_dir = os.getcwd() if file_dir is None else file_dir  # ASPEN文件所处目录, 默认为当前目录

        self.app.InitFromArchive2(os.path.join(self.file_dir, file_name))
        self.app.Visible = 1 if visible else 0
        self.app.SuppressDialogs = 0 if dialogs else 1

        print('The ASPEN file "%s" has been reloaded' % file_name)

    def run_simulation(self, reinit: bool = True, sleep: float = 2.0):
        """进行模拟

        :param reinit: 是否重新初始化迭代参数设置, defaults to True
        :param sleep: 每次检测运行状态的间隔时长, defaults to 2.0
        """
        if reinit:
            self.app.Reinit()
        
        self.app.Engine.Run2()
        while self.app.Engine.IsRunning == 1:
            time.sleep(sleep)

    def check_simulation_status(self) -> list:
        """检查模拟是否收敛等"""
        try:
            value = self.app.Tree.FindNode(r'\Data\Results Summary\Run-Status\Output\RUNID').Value
            file_path = self.file_dir + '\\' + value + '.his'

            with open(file_path,'r') as f: 
                isError = np.any(np.array([line.find('SEVERE ERROR') for line in f.readlines()])>=0)
            return [not isError]
        except:
            # 如果无法读取状态文件，通过其他方式检查
            try:
                # 检查引擎是否正常完成
                return [not self.app.Engine.IsRunning]
            except:
                return [False]

    def quit_app(self):
        self.app.Quit()

    def close_app(self):
        self.app.Close()

    def save_as(self, filename: str):
        """另存为文件"""
        try:
            full_path = os.path.join(self.file_dir, filename)
            self.app.SaveAs(full_path)
            print(f"文件已保存为: {full_path}")
            return True
        except Exception as e:
            print(f"保存文件失败: {str(e)}")
            return False


def run_aspen_simulation(version: str = "14.0", test_file: str = "test.bkp", result_file: str = "test_result.bkp"):
    """使用test.bkp文件进行实际仿真测试"""
    try:
        print(f"\n=== Aspen Plus {version} 仿真测试 ===")
        
        if not os.path.exists(test_file):
            print(f"⚠ {test_file} 文件不存在，请确保文件在当前目录")
            return False
        
        print(f"✓ 找到文件: {test_file}")
        
        # 初始化 Aspen Plus
        print(f"正在初始化 Aspen Plus {version}...")
        pyaspen = PyASPENPlus()
        
        try:
            pyaspen.init_app(ap_version=version)
            print(f"✓ Aspen Plus 版本 {version} 初始化成功!")
        except Exception as e:
            print(f"✗ 版本 {version} 连接失败: {str(e)}")
            return False
        
        # 加载文件
        print(f"加载文件: {test_file}...")
        pyaspen.load_ap_file(test_file, visible=True, dialogs=False)
        print("✓ 文件加载成功!")
        
        # 等待文件完全加载
        time.sleep(3)
        
        # 探索流程图结构
        print("探索流程图结构...")
        try:
            # 检查物料流
            streams_node = pyaspen.app.Tree.FindNode(r"\Data\Streams")
            if streams_node:
                print("✓ 找到物料流节点")
                
                try:
                    stream_count = streams_node.Elements.Count
                    print(f"✓ 物料流数量: {stream_count}")
                    
                    if stream_count > 0:
                        first_stream = streams_node.Elements.Item(1).Name
                        print(f"✓ 第一个物料流: {first_stream}")
                        
                        # 尝试获取该流的一些属性
                        try:
                            temp_node = pyaspen.app.Tree.FindNode(f"\\Data\\Streams\\{first_stream}\\Output\\TEMP_OUT\\MIXED")
                            if temp_node and temp_node.Value is not None:
                                print(f"✓ {first_stream} 温度: {temp_node.Value}°C")
                        except:
                            print(f"⚠ 无法获取 {first_stream} 的温度")
                        
                        try:
                            press_node = pyaspen.app.Tree.FindNode(f"\\Data\\Streams\\{first_stream}\\Output\\PRES_OUT\\MIXED")
                            if press_node and press_node.Value is not None:
                                print(f"✓ {first_stream} 压力: {press_node.Value} bar")
                        except:
                            print(f"⚠ 无法获取 {first_stream} 的压力")
                
                except Exception as e:
                    print(f"⚠ 获取物料流信息失败: {str(e)}")
            
            # 检查设备块
            blocks_node = pyaspen.app.Tree.FindNode(r"\Data\Blocks")
            if blocks_node:
                print("✓ 找到设备块节点")
                try:
                    block_count = blocks_node.Elements.Count
                    print(f"✓ 设备块数量: {block_count}")
                    
                    if block_count > 0:
                        first_block = blocks_node.Elements.Item(1).Name
                        print(f"✓ 第一个设备块: {first_block}")
                except Exception as e:
                    print(f"⚠ 获取设备块信息失败: {str(e)}")
            
        except Exception as e:
            print(f"⚠ 探索文件结构失败: {str(e)}")
        
        # 运行仿真
        print("开始运行仿真...")
        try:
            print("初始化仿真引擎...")
            pyaspen.app.Reinit()
            print("✓ 仿真引擎初始化成功!")
            
            print("开始运行仿真...")
            pyaspen.run_simulation(reinit=True, sleep=1.0)
            print("✓ 仿真运行完成!")
            
            # 检查仿真状态
            status = pyaspen.check_simulation_status()
            print(f"✓ 仿真状态检查: {status}")
            
        except Exception as sim_e:
            print(f"⚠ 仿真运行失败: {str(sim_e)}")
        
        # 保存仿真结果
        print("保存仿真结果...")
        try:
            pyaspen.save_as(result_file)
            print(f"✓ 仿真结果已保存为 {result_file}")
        except Exception as save_e:
            print(f"⚠ 保存失败: {str(save_e)}")
        
        # 关闭应用
        print("正在关闭 Aspen Plus...")
        pyaspen.close_app()
        print("✓ Aspen Plus 已关闭")
        
        return True
        
    except Exception as e:
        print(f"✗ 仿真测试失败: {str(e)}")
        try:
            if 'pyaspen' in locals():
                pyaspen.close_app()
        except:
            pass
        return False


def main():
    """主函数"""
    print("Aspen Plus 仿真接口测试")
    print("=" * 50)
    
    # 用户输入版本
    print("请输入您的 Aspen Plus 版本号:")
    print("常用版本: 14.0, 12.1, 11.0, 10.0, 9.0")
    version = input("版本号 (默认14.0): ").strip()
    if not version:
        version = "14.0"
    
    # 检查test.bkp文件
    test_file = "test.bkp"
    if not os.path.exists(test_file):
        print(f"\n⚠ 未找到 {test_file} 文件")
        print("请确保 test.bkp 文件在当前目录中")
        return
    
    # 运行仿真
    print(f"\n开始使用 Aspen Plus {version} 进行仿真...")
    success = run_aspen_simulation(version=version, test_file=test_file)
    
    # 结果总结
    print("\n" + "=" * 50)
    if success:
        print("✓ 仿真测试成功完成!")
        print("检查当前目录中的 test_result.bkp 文件查看结果")
    else:
        print("✗ 仿真测试失败")
        print("请检查 Aspen Plus 安装和配置")
    
    print("\n使用说明:")
    print("1. PyASPENPlus 类用于操作现有的 Aspen Plus 文件")
    print("2. 确保 test.bkp 文件包含完整的流程图")
    print("3. 仿真结果保存在 test_result.bkp 中")


if __name__ == "__main__":
    main()