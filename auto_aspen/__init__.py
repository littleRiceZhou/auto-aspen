import os
import sys
import time
import json
import zipfile
import tempfile
import shutil
from datetime import datetime
import numpy as np
import win32com.client as win32
from typing import Dict, Any, Optional, List, Tuple
from dataclasses import dataclass, field
from loguru import logger


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
        """载入待运行的ASPEN文件
        
        :param file_name: ASPEN文件名（支持 .bkp 和 .apwz 格式）
        :param file_dir: 文件目录，默认为当前目录
        :param visible: 是否显示ASPEN界面，默认为False
        :param dialogs: 是否显示对话框，默认为False
        """
        # 文件类型检查 - 支持 .bkp 和 .apwz 格式
        file_ext = os.path.splitext(file_name)[1].lower()
        if file_ext not in ['.bkp', '.apwz']:
            raise ValueError(f'不支持的文件格式: {file_ext}。仅支持 .bkp 和 .apwz 格式')
        
        self.file_dir = os.getcwd() if file_dir is None else file_dir  # ASPEN文件所处目录, 默认为当前目录
        full_file_path = os.path.join(self.file_dir, file_name)

        # 根据文件格式选择不同的加载方法
        if file_ext == '.apwz':
            # 对于 .apwz 文件，需要先解压
            logger.info(f'正在处理 .apwz 文件: {file_name}')
            
            try:
                # 创建临时目录来解压文件
                temp_dir = tempfile.mkdtemp(prefix='aspen_apwz_')
                logger.debug(f"创建临时目录: {temp_dir}")
                
                # 解压 .apwz 文件
                with zipfile.ZipFile(full_file_path, 'r') as zip_ref:
                    zip_ref.extractall(temp_dir)
                    logger.debug(f"文件解压完成到: {temp_dir}")
                
                # 查找解压后的 .bkp 文件
                bkp_file = None
                # 按优先级查找文件：.apw > .bkp > .backup
                file_patterns = ['.apw', '.bkp', '.backup']
                
                for pattern in file_patterns:
                    for root, dirs, files in os.walk(temp_dir):
                        for file in files:
                            if file.lower().endswith(pattern):
                                bkp_file = os.path.join(root, file)
                                logger.debug(f"找到 {pattern} 文件: {bkp_file}")
                                break
                        if bkp_file:
                            break
                    if bkp_file:
                        break
                
                if not bkp_file:
                    # 如果没有找到 .bkp 文件，列出所有文件
                    all_files = []
                    for root, dirs, files in os.walk(temp_dir):
                        for file in files:
                            all_files.append(os.path.join(root, file))
                    
                    logger.debug(f"解压后的文件列表: {all_files}")
                    raise Exception(f"在 .apwz 文件中未找到 .bkp 文件。解压后的文件: {all_files}")
                
                # 使用找到的文件加载
                logger.info(f"使用解压后的文件: {os.path.basename(bkp_file)}")
                
                # 根据文件扩展名选择加载方法
                file_ext_found = os.path.splitext(bkp_file)[1].lower()
                if file_ext_found == '.apw':
                    # 对于 .apw 文件，尝试使用 InitFromTemplate2 或 Open
                    try:
                        logger.debug("尝试使用 InitFromTemplate2 加载 .apw 文件")
                        self.app.InitFromTemplate2(bkp_file)
                    except Exception as e1:
                        logger.debug(f"InitFromTemplate2 失败: {str(e1)}")
                        try:
                            logger.debug("尝试使用 InitFromArchive2 加载 .apw 文件")
                            self.app.InitFromArchive2(bkp_file)
                        except Exception as e2:
                            logger.debug(f"InitFromArchive2 失败: {str(e2)}")
                            raise Exception(f"无法加载 .apw 文件: InitFromTemplate2: {str(e1)}, InitFromArchive2: {str(e2)}")
                else:
                    # 对于 .bkp 和 .backup 文件，使用 InitFromArchive2
                    self.app.InitFromArchive2(bkp_file)
                
                # 保存临时目录路径，以便后续清理
                self._temp_dir = temp_dir
                
            except Exception as e:
                # 清理临时目录
                if 'temp_dir' in locals() and os.path.exists(temp_dir):
                    try:
                        shutil.rmtree(temp_dir)
                        logger.debug(f"清理临时目录: {temp_dir}")
                    except:
                        pass
                raise Exception(f"处理 .apwz 文件失败: {str(e)}")
        else:
            # 对于 .bkp 文件，使用原有的方法
            logger.info(f'正在加载 .bkp 文件: {file_name}')
            self.app.InitFromArchive2(full_file_path)
        
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
        """获取设备块的属性信息"""
        properties = {}
        
        try:
            # 特殊处理 EXPANDER 设备块
            if block_name.upper() == 'EXPANDER':
                logger.debug(f"获取 EXPANDER 设备块的详细结果")
                
                # EXPANDER 设备块的关键输出参数（基于实际探索发现的路径）
                expander_params = {
                    "indicated_power": {"path": "\\Data\\Blocks\\EXPANDER\\Output\\IND_POWER", "unit": "kW", "name": "指示马力"},
                    "brake_power": {"path": "\\Data\\Blocks\\EXPANDER\\Output\\BRAKE_POWER", "unit": "kW", "name": "制动马力"},
                    "net_power_required": {"path": "\\Data\\Blocks\\EXPANDER\\Output\\WNET", "unit": "kW", "name": "净功要求"},
                    "power_loss": {"path": "\\Data\\Blocks\\EXPANDER\\Output\\POWER_LOSS", "unit": "kW", "name": "功率损耗"},
                    "efficiency": {"path": "\\Data\\Blocks\\EXPANDER\\Output\\EFF_ISEN", "unit": "", "name": "效率"},
                    "mechanical_efficiency": {"path": "\\Data\\Blocks\\EXPANDER\\Output\\EFF_MECH", "unit": "", "name": "机械效率"},
                    "outlet_pressure": {"path": "\\Data\\Blocks\\EXPANDER\\Output\\POC", "unit": "bar", "name": "出口压力"},
                    "outlet_temperature": {"path": "\\Data\\Blocks\\EXPANDER\\Output\\TOC", "unit": "°C", "name": "出口温度"},
                    "isentropic_outlet_temp": {"path": "\\Data\\Blocks\\EXPANDER\\Output\\TOS", "unit": "°C", "name": "等熵出口温度"},
                    "vapor_fraction": {"path": "\\Data\\Blocks\\EXPANDER\\Output\\B_VFRAC", "unit": "", "name": "汽相分率"},
                    "compression_model": {"path": "\\Data\\Blocks\\EXPANDER\\Input\\TYPE", "unit": "", "name": "压缩机模型"},
                    "inlet_pressure": {"path": "\\Data\\Blocks\\EXPANDER\\Output\\IN_PRES", "unit": "bar", "name": "入口压力"},
                    "pressure_ratio": {"path": "\\Data\\Blocks\\EXPANDER\\Output\\PRES_RATIO", "unit": "", "name": "压力比"},
                    "isentropic_power": {"path": "\\Data\\Blocks\\EXPANDER\\Output\\POWER_ISEN", "unit": "kW", "name": "等熵功率"}
                }
                
                # 尝试获取每个参数
                for param_key, param_info in expander_params.items():
                    try:
                        node = self.app.Tree.FindNode(param_info["path"])
                        if node and node.Value is not None:
                            try:
                                # 尝试转换为数值
                                value = float(node.Value)
                                properties[param_info["name"]] = {
                                    "value": value,
                                    "unit": param_info["unit"],
                                    "path": param_info["path"],
                                    "key": param_key
                                }
                                logger.debug(f"获取到 {param_info['name']}: {value} {param_info['unit']}")
                            except (ValueError, TypeError):
                                # 如果不能转换为数值，保存为字符串
                                value = str(node.Value)
                                properties[param_info["name"]] = {
                                    "value": value,
                                    "unit": param_info["unit"],
                                    "path": param_info["path"],
                                    "key": param_key
                                }
                                logger.debug(f"获取到 {param_info['name']}: {value}")
                    except Exception as e:
                        logger.debug(f"获取 {param_info['name']} 失败: {str(e)}")
                        # 尝试其他可能的路径
                        alternative_paths = [
                            param_info["path"].replace("\\Output\\", "\\Results\\"),
                            param_info["path"].replace("\\Output\\", "\\Input\\"),
                            param_info["path"] + "\\MIXED"
                        ]
                        
                        for alt_path in alternative_paths:
                            try:
                                alt_node = self.app.Tree.FindNode(alt_path)
                                if alt_node and alt_node.Value is not None:
                                    try:
                                        value = float(alt_node.Value)
                                        properties[param_info["name"]] = {
                                            "value": value,
                                            "unit": param_info["unit"],
                                            "path": alt_path,
                                            "key": param_key
                                        }
                                        logger.debug(f"通过备用路径获取到 {param_info['name']}: {value} {param_info['unit']}")
                                        break
                                    except (ValueError, TypeError):
                                        value = str(alt_node.Value)
                                        properties[param_info["name"]] = {
                                            "value": value,
                                            "unit": param_info["unit"],
                                            "path": alt_path,
                                            "key": param_key
                                        }
                                        logger.debug(f"通过备用路径获取到 {param_info['name']}: {value}")
                                        break
                            except:
                                continue
            
            # 通用设备块属性获取（保留原有逻辑作为备用）
            if auto_discover and len(properties) < 5:  # 如果专用方法获取的参数太少，使用通用方法补充
                logger.debug(f"使用通用方法补充 {block_name} 的属性")
                
                # 常见的设备块输出属性
                common_block_props = {
                    "WNET": {"unit": "kW", "name": "net_work"},
                    "POWER": {"unit": "kW", "name": "power"},
                    "QNET": {"unit": "kW", "name": "heat_duty"},
                    "PRES": {"unit": "bar", "name": "pressure"},
                    "TEMP": {"unit": "°C", "name": "temperature"},
                    "EFF": {"unit": "", "name": "efficiency"},
                    "DELPMAX": {"unit": "bar", "name": "pressure_drop"},
                    "VFRAC": {"unit": "", "name": "vapor_fraction"}
                }
                
                for prop_key, prop_info in common_block_props.items():
                    # 跳过已经获取的属性
                    if any(prop_info["name"] in existing_prop.get("key", "") for existing_prop in properties.values()):
                        continue
                        
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
                                        properties[f"通用_{prop_info['name']}"] = {
                                            "value": value,
                                            "unit": prop_info["unit"],
                                            "path": path
                                        }
                                        break
                                    except (ValueError, TypeError):
                                        properties[f"通用_{prop_info['name']}"] = {
                                            "value": str(node.Value),
                                            "unit": prop_info["unit"],
                                            "path": path
                                        }
                                        break
                            except:
                                continue
                    except Exception as e:
                        logger.debug(f"获取 {block_name} 的 {prop_key} 失败: {str(e)}")
        
        except Exception as e:
            logger.error(f"获取设备块 {block_name} 属性时发生错误: {str(e)}")
        
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
            
            # 清理临时目录（如果存在）
            if hasattr(self, '_temp_dir') and self._temp_dir and os.path.exists(self._temp_dir):
                try:
                    shutil.rmtree(self._temp_dir)
                    logger.debug(f"清理临时目录: {self._temp_dir}")
                except Exception as e:
                    logger.debug(f"清理临时目录失败: {str(e)}")
                    
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


@dataclass
class SimulationParameters:
    """仿真参数管理类"""
    
    gas_flow_rate: float = 10000.0  # scmh
    inlet_pressure: float = 0.5     # MPaA
    inlet_temperature: float = 25.0 # °C
    outlet_pressure: float = 3.0    # MPaA
    efficiency: float = 80.0        # %
    gas_composition: Dict[str, float] = field(default_factory=lambda: {
        'CH4': 85.0,    # 甲烷
        'C2H6': 8.0,    # 乙烷
        'C3H8': 3.0,    # 丙烷
        'N2': 2.0,      # 氮气
        'CO2': 2.0      # 二氧化碳
    })
    other_requirements: str = '标准工况下的气体处理'
    
    @classmethod
    def from_file(cls, file_path: str = 'simulation_parameters.py') -> 'SimulationParameters':
        """从文件加载参数"""
        try:
            import importlib.util
            spec = importlib.util.spec_from_file_location("simulation_parameters", file_path)
            if spec and spec.loader:
                module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(module)
                params_dict = module.SIMULATION_PARAMETERS
                return cls(**params_dict)
        except (ImportError, AttributeError, FileNotFoundError) as e:
            logger.info(f"无法从文件加载参数: {str(e)}, 使用默认参数")
        
        return cls()
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            'gas_flow_rate': self.gas_flow_rate,
            'inlet_pressure': self.inlet_pressure,
            'inlet_temperature': self.inlet_temperature,
            'outlet_pressure': self.outlet_pressure,
            'efficiency': self.efficiency,
            'gas_composition': self.gas_composition,
            'other_requirements': self.other_requirements
        }
    
    def log_parameters(self) -> None:
        """记录参数信息"""
        logger.info("仿真参数:")
        for key, value in self.to_dict().items():
            logger.info(f"  {key}: {value}")


@dataclass
class SimulationResult:
    """仿真结果管理类"""
    
    success: bool = False
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    streams: Dict[str, Any] = field(default_factory=dict)
    blocks: Dict[str, Any] = field(default_factory=dict)
    summary: Dict[str, Any] = field(default_factory=dict)
    
    def add_error(self, error: str) -> None:
        """添加错误信息"""
        self.errors.append(error)
    
    def add_warning(self, warning: str) -> None:
        """添加警告信息"""
        self.warnings.append(warning)
    
    def set_summary(self, stream_count: int, block_count: int) -> None:
        """设置摘要信息"""
        self.summary = {
            'stream_count': stream_count,
            'block_count': block_count
        }
    
    def log_results(self) -> None:
        """记录结果信息"""
        logger.info("仿真完成，详细结果:")
        logger.info(f"成功状态: {self.success}")
        logger.info(f"错误数量: {len(self.errors)}")
        logger.info(f"警告数量: {len(self.warnings)}")
        logger.info(f"物料流数量: {self.summary.get('stream_count', 0)}")
        logger.info(f"设备块数量: {self.summary.get('block_count', 0)}")
        
        # 输出物料流信息
        if self.streams:
            logger.info("物料流信息:")
            for stream_name, stream_data in self.streams.items():
                logger.info(f"  {stream_name}:")
                if isinstance(stream_data, dict):
                    for prop_name, prop_data in stream_data.items():
                        if isinstance(prop_data, dict) and 'value' in prop_data:
                            logger.info(f"    {prop_name}: {prop_data.get('value', 'N/A')} {prop_data.get('unit', '')}")
        
        # 输出设备块信息
        if self.blocks:
            logger.info("设备块信息:")
            for block_name, block_data in self.blocks.items():
                logger.info(f"  {block_name}:")
                if isinstance(block_data, dict):
                    for prop_name, prop_data in block_data.items():
                        if isinstance(prop_data, dict) and 'value' in prop_data:
                            logger.info(f"    {prop_name}: {prop_data.get('value', 'N/A')} {prop_data.get('unit', '')}")
        
        # 输出错误和警告信息
        if self.errors:
            logger.error("仿真错误:")
            for error in self.errors:
                logger.error(f"  - {error}")
        
        if self.warnings:
            logger.warning("仿真警告:")
            for warning in self.warnings:
                logger.warning(f"  - {warning}")
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            'success': self.success,
            'errors': self.errors,
            'warnings': self.warnings,
            'streams': self.streams,
            'blocks': self.blocks,
            'summary': self.summary
        }
    
    def save_to_json(self, output_file: str = "simulation_results.json") -> bool:
        """保存结果到JSON文件"""
        try:
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(self.to_dict(), f, ensure_ascii=False, indent=2, default=str)
            logger.info(f"JSON 结果已保存到: {output_file}")
            return True
        except Exception as e:
            logger.error(f"保存 JSON 结果失败: {str(e)}")
            return False


class APWZSimulator:
    """APWZ仿真器类"""
    
    def __init__(self, apwz_file: str, aspen_version: str = '14.0'):
        """
        初始化仿真器
        
        :param apwz_file: APWZ文件路径
        :param aspen_version: ASPEN版本
        """
        self.apwz_file = apwz_file
        self.aspen_version = aspen_version
        self.aspen: Optional[PyASPENPlus] = None
        self.is_initialized = False
        
    def __enter__(self):
        """上下文管理器入口"""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """上下文管理器出口"""
        self.close()
    
    def initialize(self, visible: bool = True, dialogs: bool = False) -> bool:
        """初始化ASPEN应用"""
        try:
            if not os.path.exists(self.apwz_file):
                logger.error(f"文件 {self.apwz_file} 不存在")
                return False
            
            # 创建 ASPEN Plus 实例
            self.aspen = PyASPENPlus()
            
            # 初始化应用
            logger.info("初始化 ASPEN Plus...")
            self.aspen.init_app(ap_version=self.aspen_version)
            
            # 加载文件
            logger.info(f"加载 .apwz 文件: {self.apwz_file}")
            self.aspen.load_ap_file(self.apwz_file, visible=visible, dialogs=dialogs)
            
            self.is_initialized = True
            logger.info("ASPEN 应用初始化成功")
            return True
            
        except Exception as e:
            logger.error(f"初始化 ASPEN 应用失败: {str(e)}")
            return False
    
    def set_parameters(self, parameters: SimulationParameters) -> bool:
        """设置仿真参数"""
        if not self.is_initialized or not self.aspen:
            logger.error("ASPEN 应用未初始化")
            return False
        
        try:
            logger.info("开始设置仿真参数...")
            
            # 设置气体体积流量
            success_count = 0
            
            if self._set_gas_flow_rate(parameters.gas_flow_rate):
                success_count += 1
            
            if self._set_inlet_pressure(parameters.inlet_pressure):
                success_count += 1
            
            if self._set_inlet_temperature(parameters.inlet_temperature):
                success_count += 1
            
            if self._set_outlet_pressure(parameters.outlet_pressure):
                success_count += 1
            
            if self._set_gas_composition(parameters.gas_composition):
                success_count += 1
            
            if self._set_efficiency(parameters.efficiency):
                success_count += 1
            
            logger.info(f"参数设置完成，成功设置 {success_count}/6 个参数组")
            return success_count > 0
            
        except Exception as e:
            logger.error(f"设置参数时发生错误: {str(e)}")
            return False
    
    def _set_gas_flow_rate(self, flow_rate: float) -> bool:
        """设置气体体积流量"""
        logger.info(f"设置气体体积流量: {flow_rate} scmh")
        
        flow_paths = [
            r"\Data\Streams\INLET\Input\TOTFLOW\MIXED",
            r"\Data\Streams\INLET\Input\VOLFLOW\MIXED", 
            r"\Data\Streams\INLET\Input\FLOW\MIXED"
        ]
        
        return self._set_parameter_by_paths(flow_paths, flow_rate, "气体流量")
    
    def _set_inlet_pressure(self, pressure: float) -> bool:
        """设置进气压力"""
        logger.info(f"设置进气压力: {pressure} MPaA")
        
        pressure_value = pressure * 10  # MPaA -> bara
        pressure_paths = [
            r"\Data\Streams\INLET\Input\PRES",
            r"\Data\Streams\INLET\Input\PRES\MIXED"
        ]
        
        return self._set_parameter_by_paths(pressure_paths, pressure_value, "进气压力")
    
    def _set_inlet_temperature(self, temperature: float) -> bool:
        """设置进气温度"""
        logger.info(f"设置进气温度: {temperature} °C")
        
        temp_paths = [
            r"\Data\Streams\INLET\Input\TEMP\MIXED",
            r"\Data\Streams\INLET\Input\TEMP"
        ]
        
        return self._set_parameter_by_paths(temp_paths, temperature, "进气温度")
    
    def _set_outlet_pressure(self, pressure: float) -> bool:
        """设置排气压力"""
        logger.info(f"设置排气压力(排放压力): {pressure} MPaA")
        
        pressure_value = pressure * 10  # MPaA -> bara
        expander_paths = [
            r"\Data\Blocks\EXPANDER\Input\PRES"
        ]
        
        return self._set_parameter_by_paths(expander_paths, pressure_value, "排放压力")
    
    def _set_efficiency(self, efficiency: float) -> bool:
        """设置机组效率"""
        logger.info(f"设置机组效率(等熵效率): {efficiency}%")
        
        efficiency_value = efficiency / 100.0  # 百分比转换为小数
        eff_paths = [
            r"\Data\Blocks\EXPANDER\Input\SEFF"
        ]
        
        return self._set_parameter_by_paths(eff_paths, efficiency_value, "等熵效率")
    
    def _set_gas_composition(self, composition: Dict[str, float]) -> bool:
        """设置气体组分"""
        logger.info("设置气体组分...")
        
        total_set = 0
        for component, fraction in composition.items():
            comp_paths = [
                f"\\Data\\Streams\\INLET\\Input\\FLOW\\MIXED\\{component}",
                f"\\Data\\Streams\\INLET\\Input\\COMPFLOW\\MIXED\\{component}"
            ]
            
            fraction_value = fraction / 100.0  # 百分比转换为小数
            if self._set_parameter_by_paths(comp_paths, fraction_value, f"组分 {component}"):
                total_set += 1
        
        logger.info(f"成功设置 {total_set} 个组分")
        return total_set > 0
    
    def _set_parameter_by_paths(self, paths: List[str], value: float, param_name: str) -> bool:
        """通过路径列表设置参数"""
        for path in paths:
            try:
                node = self.aspen.app.Tree.FindNode(path)
                if node:
                    node.Value = value
                    logger.info(f"成功设置{param_name}: {value} (路径: {path})")
                    return True
            except Exception as e:
                logger.debug(f"{param_name}路径 {path} 设置失败: {str(e)}")
        
        logger.warning(f"所有{param_name}路径设置都失败")
        return False
    
    def run_simulation(self, reinit: bool = True, sleep: float = 2.0) -> bool:
        """运行仿真"""
        if not self.is_initialized or not self.aspen:
            logger.error("ASPEN 应用未初始化")
            return False
        
        try:
            logger.info("开始运行仿真...")
            self.aspen.run_simulation(reinit=reinit, sleep=sleep)
            
            # 检查仿真状态
            logger.info("检查仿真状态...")
            status = self.aspen.check_simulation_status()
            logger.info(f"仿真状态: {'成功' if status[0] else '失败'}")
            
            return status[0]
            
        except Exception as e:
            logger.error(f"运行仿真失败: {str(e)}")
            return False
    
    def get_results(self) -> SimulationResult:
        """获取仿真结果"""
        result = SimulationResult()
        
        if not self.is_initialized or not self.aspen:
            result.add_error("ASPEN 应用未初始化")
            return result
        
        try:
            logger.info("获取仿真结果...")
            
            # 获取基本结果
            aspen_result = self.aspen.get_simulation_results(auto_discover=True)
            
            # 填充结果对象
            result.success = aspen_result.get('success', False)
            result.errors = aspen_result.get('errors', [])
            result.warnings = aspen_result.get('warnings', [])
            result.streams = aspen_result.get('streams', {})
            result.blocks = aspen_result.get('blocks', {})
            result.summary = aspen_result.get('summary', {})
            
            # 特别获取 EXPANDER 设备块的详细结果
            logger.info("获取 EXPANDER 设备块详细结果...")
            try:
                expander_results = self.aspen._get_block_properties("EXPANDER", auto_discover=True)
                if expander_results:
                    if 'blocks' not in result.blocks:
                        result.blocks = {}
                    result.blocks['EXPANDER'] = expander_results
                    logger.info(f"成功获取 EXPANDER 设备块 {len(expander_results)} 个参数")
                else:
                    logger.warning("未能获取 EXPANDER 设备块详细结果")
            except Exception as e:
                logger.warning(f"获取 EXPANDER 设备块结果时出错: {str(e)}")
            
            return result
            
        except Exception as e:
            logger.error(f"获取仿真结果失败: {str(e)}")
            result.add_error(f"获取仿真结果失败: {str(e)}")
            return result
    
    def close(self) -> None:
        """关闭ASPEN应用"""
        if self.aspen:
            try:
                self.aspen.close_app()
                logger.info("ASPEN 应用已关闭")
            except Exception as e:
                logger.warning(f"关闭 ASPEN 应用时出错: {str(e)}")
            finally:
                self.aspen = None
                self.is_initialized = False
    
    def run_full_simulation(self, parameters: SimulationParameters) -> SimulationResult:
        """运行完整仿真流程"""
        result = SimulationResult()
        
        try:
            # 初始化
            if not self.initialize():
                result.add_error("初始化失败")
                return result
            
            # 设置参数
            if not self.set_parameters(parameters):
                result.add_warning("参数设置可能不完整")
            
            # 运行仿真
            if not self.run_simulation():
                result.add_error("仿真运行失败")
                return result
            
            # 获取结果
            result = self.get_results()
            
            return result
            
        except Exception as e:
            logger.error(f"完整仿真流程失败: {str(e)}")
            result.add_error(f"完整仿真流程失败: {str(e)}")
            return result
