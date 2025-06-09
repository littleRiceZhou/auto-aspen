import os
import sys
import time
import json
from datetime import datetime
import numpy as np
import win32com.client as win32
from loguru import logger

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
                logger.debug(f"尝试连接COM类: {com_class}")
                self.app = win32.Dispatch(com_class)
                logger.info(f"成功连接到: {com_class}")
                return
            except Exception as e:
                last_error = e
                logger.debug(f"连接失败: {com_class} - {str(e)}")
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

        logger.info(f'ASPEN文件 "{file_name}" 已加载完成')

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

    def get_simulation_results(self, auto_discover: bool = True) -> dict:
        """获取详细的仿真结果，返回JSON格式
        
        :param auto_discover: 是否自动发现可用的数据属性，默认为True
        """
        result = {
            "timestamp": datetime.now().isoformat(),
            "success": False,
            "errors": [],
            "warnings": [],
            "streams": {},
            "blocks": {},
            "summary": {},
            "model_info": {}
        }
        
        try:
            # 检查仿真状态
            status = self.check_simulation_status()
            result["success"] = status[0] if status else False
            
            # 获取错误信息
            try:
                value = self.app.Tree.FindNode(r'\Data\Results Summary\Run-Status\Output\RUNID').Value
                file_path = self.file_dir + '\\' + value + '.his'
                
                with open(file_path, 'r') as f:
                    lines = f.readlines()
                    for line in lines:
                        if 'SEVERE ERROR' in line:
                            result["errors"].append(line.strip())
                        elif 'WARNING' in line:
                            result["warnings"].append(line.strip())
            except Exception as e:
                logger.debug(f"无法读取历史文件: {str(e)}")
            
            # 获取物料流信息
            try:
                streams_node = self.app.Tree.FindNode(r"\Data\Streams")
                if streams_node:
                    stream_count = streams_node.Elements.Count
                    result["summary"]["stream_count"] = stream_count
                    
                    for i in range(1, min(stream_count + 1, 11)):  # 最多获取前10个流
                        try:
                            stream_element = streams_node.Elements.Item(i)
                            if stream_element is None:
                                logger.debug(f"物料流元素 {i} 为空，跳过")
                                continue
                                
                            stream_name = stream_element.Name
                            if not stream_name:
                                logger.debug(f"物料流元素 {i} 名称为空，跳过")
                                continue
                                
                            stream_data = {"name": stream_name}
                            
                            if auto_discover:
                                # 自动发现可用的输出属性
                                stream_data.update(self._get_stream_properties(stream_name))
                            else:
                                # 使用标准属性
                                stream_data.update(self._get_standard_stream_properties(stream_name))
                                
                            result["streams"][stream_name] = stream_data
                                
                        except Exception as e:
                            # 由于stream_name可能未定义，使用索引作为标识
                            stream_identifier = f"stream_{i}"
                            logger.debug(f"获取物料流 {stream_identifier} 信息失败: {str(e)}")
                            result["streams"][stream_identifier] = {"index": i, "error": str(e)}
                            
            except Exception as e:
                logger.debug(f"获取物料流信息失败: {str(e)}")
            
            # 获取设备块信息
            try:
                blocks_node = self.app.Tree.FindNode(r"\Data\Blocks")
                if blocks_node:
                    block_count = blocks_node.Elements.Count
                    result["summary"]["block_count"] = block_count
                    
                    for i in range(1, min(block_count + 1, 6)):  # 最多获取前5个设备
                        try:
                            block_element = blocks_node.Elements.Item(i)
                            if block_element is None:
                                logger.debug(f"设备块元素 {i} 为空，跳过")
                                continue
                                
                            block_name = block_element.Name
                            if not block_name:
                                logger.debug(f"设备块元素 {i} 名称为空，跳过")
                                continue
                            
                            # 使用自适应方法获取设备属性
                            block_data = self._get_block_properties(block_name, auto_discover)
                                
                            result["blocks"][block_name] = block_data
                            
                        except Exception as e:
                            # 由于block_name可能未定义，使用索引作为标识
                            block_identifier = f"block_{i}"
                            logger.debug(f"获取设备块 {block_identifier} 信息失败: {str(e)}")
                            result["blocks"][block_identifier] = {"index": i, "error": str(e)}
                            
            except Exception as e:
                logger.debug(f"获取设备块信息失败: {str(e)}")
                
            # 添加运行信息
            result["summary"]["file_directory"] = getattr(self, 'file_dir', None)
            result["summary"]["engine_running"] = False
            try:
                result["summary"]["engine_running"] = bool(self.app.Engine.IsRunning)
            except:
                pass
                
        except Exception as e:
            result["errors"].append(f"获取仿真结果时发生错误: {str(e)}")
            logger.error(f"获取仿真结果失败: {str(e)}")
        
        return result

    def _get_stream_properties(self, stream_name: str) -> dict:
        """自动发现物料流的可用属性"""
        properties = {}
        
        # 常见的物料流输出属性
        common_props = {
            "TEMP_OUT": {"paths": ["MIXED", ""], "unit": "°C", "name": "temperature"},
            "PRES_OUT": {"paths": ["MIXED", ""], "unit": "bar", "name": "pressure"}, 
            "MOLEFLOW": {"paths": ["MIXED", ""], "unit": "kmol/hr", "name": "molar_flow"},
            "MASSFLOW": {"paths": ["MIXED", ""], "unit": "kg/hr", "name": "mass_flow"},
            "VOLFLOW": {"paths": ["MIXED", ""], "unit": "l/min", "name": "volume_flow"},
            "ENTHALPY": {"paths": ["MIXED", ""], "unit": "MMBtu/hr", "name": "enthalpy"},
            "ENTROPY": {"paths": ["MIXED", ""], "unit": "MMBtu/R-hr", "name": "entropy"},
            "DENSITY": {"paths": ["MIXED", ""], "unit": "kg/cum", "name": "density"}
        }
        
        for prop_key, prop_info in common_props.items():
            for path_suffix in prop_info["paths"]:
                try:
                    full_path = f"\\Data\\Streams\\{stream_name}\\Output\\{prop_key}"
                    if path_suffix:
                        full_path += f"\\{path_suffix}"
                    
                    node = self.app.Tree.FindNode(full_path)
                    if node and node.Value is not None:
                        try:
                            value = float(node.Value)
                            properties[prop_info["name"]] = {
                                "value": value, 
                                "unit": prop_info["unit"],
                                "path": full_path
                            }
                            break  # 找到有效值就跳出
                        except (ValueError, TypeError):
                            # 如果无法转换为数值，保存原始值
                            properties[prop_info["name"]] = {
                                "value": str(node.Value), 
                                "unit": prop_info["unit"],
                                "path": full_path
                            }
                            break
                except Exception as e:
                    logger.debug(f"获取 {stream_name} 的 {prop_key} 失败: {str(e)}")
                    continue
        
        return properties

    def _get_standard_stream_properties(self, stream_name: str) -> dict:
        """获取标准的物料流属性（原有逻辑）"""
        properties = {}
        
        # 获取温度
        try:
            temp_node = self.app.Tree.FindNode(f"\\Data\\Streams\\{stream_name}\\Output\\TEMP_OUT\\MIXED")
            if temp_node and temp_node.Value is not None:
                properties["temperature"] = {"value": float(temp_node.Value), "unit": "°C"}
        except:
            pass
        
        # 获取压力
        try:
            press_node = self.app.Tree.FindNode(f"\\Data\\Streams\\{stream_name}\\Output\\PRES_OUT\\MIXED")
            if press_node and press_node.Value is not None:
                properties["pressure"] = {"value": float(press_node.Value), "unit": "bar"}
        except:
            pass
        
        # 获取流量
        try:
            flow_node = self.app.Tree.FindNode(f"\\Data\\Streams\\{stream_name}\\Output\\MOLEFLOW\\MIXED")
            if flow_node and flow_node.Value is not None:
                properties["molar_flow"] = {"value": float(flow_node.Value), "unit": "kmol/hr"}
        except:
            pass
            
        return properties

    def _get_block_properties(self, block_name: str, auto_discover: bool = True) -> dict:
        """获取设备块属性"""
        properties = {"name": block_name}
        
        # 获取设备类型
        try:
            type_node = self.app.Tree.FindNode(f"\\Data\\Blocks\\{block_name}\\Input\\TYPE")
            if type_node and type_node.Value is not None:
                properties["type"] = str(type_node.Value)
        except:
            pass
        
        if auto_discover:
            # 尝试获取更多属性
            common_block_props = {
                "DUTY": {"unit": "MMBtu/hr", "name": "duty"},
                "DELPMAX": {"unit": "bar", "name": "pressure_drop"},
                "VFRAC": {"unit": "", "name": "vapor_fraction"},
                "TEMP": {"unit": "°C", "name": "temperature"}
            }
            
            for prop_key, prop_info in common_block_props.items():
                try:
                    # 尝试不同的路径
                    possible_paths = [
                        f"\\Data\\Blocks\\{block_name}\\Output\\{prop_key}",
                        f"\\Data\\Blocks\\{block_name}\\Results\\{prop_key}",
                        f"\\Data\\Blocks\\{block_name}\\Input\\{prop_key}"
                    ]
                    
                    for path in possible_paths:
                        try:
                            node = self.app.Tree.FindNode(path)
                            if node and node.Value is not None:
                                try:
                                    value = float(node.Value)
                                    properties[prop_info["name"]] = {
                                        "value": value,
                                        "unit": prop_info["unit"],
                                        "path": path
                                    }
                                    break
                                except (ValueError, TypeError):
                                    properties[prop_info["name"]] = {
                                        "value": str(node.Value),
                                        "unit": prop_info["unit"],
                                        "path": path
                                    }
                                    break
                        except:
                            continue
                except Exception as e:
                    logger.debug(f"获取 {block_name} 的 {prop_key} 失败: {str(e)}")
        
        return properties

    def quit_app(self):
        self.app.Quit()

    def close_app(self):
        self.app.Close()

    def __del__(self):
        """析构函数，确保资源被正确清理"""
        try:
            if hasattr(self, 'app') and self.app is not None:
                logger.debug("正在清理ASPEN Plus资源")
                
                # 尝试关闭应用程序
                try:
                    if hasattr(self.app, 'Engine') and self.app.Engine.IsRunning:
                        logger.debug("停止正在运行的仿真")
                        self.app.Engine.Stop()
                except:
                    pass
                
                # 尝试关闭文档
                try:
                    self.app.Close()
                    logger.debug("ASPEN Plus文档已关闭")
                except:
                    pass
                
                # 尝试退出应用
                try:
                    self.app.Quit()
                    logger.debug("ASPEN Plus应用已退出")
                except:
                    pass
                
                # 释放COM对象引用
                try:
                    self.app = None
                    logger.debug("COM对象引用已释放")
                except:
                    pass
                    
        except Exception as e:
            # 在析构函数中不要抛出异常，只记录日志
            try:
                logger.debug(f"资源清理过程中出现异常: {str(e)}")
            except:
                # 如果连日志都无法记录，则静默处理
                pass

    def save_as(self, filename: str):
        """另存为文件"""
        try:
            full_path = os.path.join(self.file_dir, filename)
            self.app.SaveAs(full_path)
            logger.info(f"文件已保存为: {full_path}")
            return True
        except Exception as e:
            logger.error(f"保存文件失败: {str(e)}")
            return False
        
    def run(self, file_name: str, file_dir: str = None, ap_version: str = '14.0', 
            visible: bool = False, dialogs: bool = False, save_result: str = None, 
            return_json: bool = False):
        """一键运行完整的ASPEN仿真流程
        
        :param file_name: ASPEN文件名
        :param file_dir: 文件目录，默认为当前目录
        :param ap_version: ASPEN Plus版本号，默认为'14.0'
        :param visible: 是否显示ASPEN界面，默认为False
        :param dialogs: 是否显示对话框，默认为False
        :param save_result: 结果文件名，如果提供则保存结果
        :param return_json: 是否返回详细的JSON格式结果，默认为False
        :return: 如果return_json=True返回详细结果字典，否则返回仿真是否成功的布尔值
        """
        try:
            logger.info(f"开始ASPEN Plus {ap_version}仿真")
            
            # 检查文件是否存在
            if not os.path.exists(file_name if file_dir is None else os.path.join(file_dir, file_name)):
                logger.error(f"文件 {file_name} 不存在")
                return False
            
            # 检查应用是否已经初始化
            if not hasattr(self, 'app') or self.app is None:
                logger.info(f"初始化ASPEN Plus {ap_version}")
                self.init_app(ap_version=ap_version)
            else:
                # 检查现有app是否仍然可用
                try:
                    # 尝试访问app的基本属性来验证其可用性
                    _ = self.app.Visible
                    logger.info("使用现有的ASPEN Plus连接")
                except:
                    # 如果现有app不可用，重新初始化
                    logger.info(f"现有连接失效，重新初始化ASPEN Plus {ap_version}")
                    self.init_app(ap_version=ap_version)
            
            # 加载文件
            logger.info(f"加载文件: {file_name}")
            self.load_ap_file(file_name, file_dir=file_dir, visible=visible, dialogs=dialogs)
            
            # 运行仿真
            logger.info("开始运行仿真")
            self.run_simulation(reinit=True, sleep=1.0)
            logger.info("仿真运行完成")
            
            # 检查仿真状态
            status = self.check_simulation_status()
            if status[0]:
                logger.info("仿真成功完成")
            else:
                logger.warning("仿真可能存在问题")
            
            # 获取详细结果（如果需要）
            detailed_results = None
            if return_json:
                logger.info("获取详细仿真结果")
                detailed_results = self.get_simulation_results(auto_discover=True)
                # 添加保存信息到结果中
                if save_result:
                    detailed_results["summary"]["result_saved_as"] = save_result
            
            # 保存结果（如果指定）
            if save_result:
                logger.info("保存仿真结果")
                save_success = self.save_as(save_result)
                if return_json and detailed_results:
                    detailed_results["summary"]["save_success"] = save_success
            
            # 关闭应用
            logger.info("关闭ASPEN Plus")
            self.close_app()
            
            # 返回结果
            if return_json:
                return detailed_results
            else:
                return status[0]
            
        except Exception as e:
            logger.error(f"仿真运行失败: {str(e)}")
            try:
                self.close_app()
            except:
                pass
            
            if return_json:
                return {
                    "timestamp": datetime.now().isoformat(),
                    "success": False,
                    "errors": [f"仿真运行失败: {str(e)}"],
                    "warnings": [],
                    "streams": {},
                    "blocks": {},
                    "summary": {"file_name": file_name}
                }
            else:
                return False

