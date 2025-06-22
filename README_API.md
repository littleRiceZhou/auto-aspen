# ASPEN & Power Calculation API

提供ASPEN仿真计算和机组功率计算的HTTP API接口。

## 功能特性

- 🔧 **机组功率计算**: 根据主机功率计算机组选型，返回详细的计算结果和验证信息
- 🏭 **ASPEN仿真计算**: 运行APWZ文件仿真，返回仿真结果
- 📊 **完整的计算流程**: 包含参数验证、计算过程、结果输出等完整流程
- 🔍 **详细的响应信息**: 提供计算详情和验证结果
- 📝 **自动文档生成**: 基于FastAPI的自动API文档

## 安装依赖

```bash
pip install -r requirements.txt
```

## 环境变量配置

在启动服务前，可以设置以下环境变量：

- `ASPEN_APWZ_FILE_PATH`: APWZ文件路径 (默认: `./models/RE-Expander.apwz`)

## 启动服务

### 方式1: 使用启动脚本

```bash
# 使用默认APWZ文件路径
python start_api.py

# 指定APWZ文件路径
python start_api.py --apwz-file /path/to/your/model.apwz

# 自定义主机和端口
python start_api.py --host 0.0.0.0 --port 9000 --no-reload
```

### 方式2: 设置环境变量后启动

```bash
# Linux/Mac
export ASPEN_APWZ_FILE_PATH="./models/RE-Expander.apwz"
python main.py

# Windows
set ASPEN_APWZ_FILE_PATH=.\models\RE-Expander.apwz
python main.py
```

### 方式3: 使用uvicorn直接启动

```bash
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

## API文档

启动服务后，访问以下地址查看自动生成的API文档：

- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

## API端点

### 1. 综合仿真计算

**POST** `/api/simulation`

运行ASPEN仿真并基于结果进行机组功率计算和选型。

#### 请求参数

```json
{
  "gas_flow_rate": 33333.333333,
  "inlet_pressure": 0.80,
  "inlet_temperature": 20.0,
  "outlet_pressure": 0.30,
  "efficiency": 85,
  "gas_composition": {
    "CH4": 100,
    "C2H6": 0,
    "C3H8": 0,
    "C4H10": 0,
    "N2": 0,
    "CO2": 0,
    "H2S": 0
  }
}
```

**注意**: APWZ文件路径通过环境变量 `ASPEN_APWZ_FILE_PATH` 控制，不需要在请求中提供。

#### 响应示例

```json
{
  "success": true,
  "aspen_results": {
    "success": true,
    "simulation_results": {
      "power_output": 66.5,
      "inlet_conditions": {...},
      "outlet_conditions": {...},
      "performance_metrics": {...}
    }
  },
  "power_results": {
    "success": true,
    "selection_output": {
      "选型输出": {
        "机组参数": {...},
        "技术参数": {...},
        "净发电功率": "60kW",
        "年收益率": "25.6万元",
        "回报周期": "3.9年"
      }
    }
  },
  "combined_results": {
    "仿真概况": {...},
    "输入参数": {...},
    "ASPEN仿真结果": {...},
    "机组选型结果": {...},
    "经济性分析": {...},
    "验证结果": {...}
  }
}
```

### 2. 健康检查

**GET** `/health`

检查API服务状态。

#### 响应示例

```json
{
  "status": "healthy",
  "message": "API service is running"
}
```

## 使用示例

### Python客户端示例

```python
import requests
import json

# 综合仿真计算（ASPEN + 功率计算）
# 注意：APWZ文件路径通过环境变量控制，不需要在请求中提供
simulation_data = {
    "gas_flow_rate": 33333.333333,
    "inlet_pressure": 0.80,
    "inlet_temperature": 20.0,
    "outlet_pressure": 0.30,
    "efficiency": 85,
    "gas_composition": {
        "CH4": 100,
        "C2H6": 0,
        "C3H8": 0,
        "C4H10": 0,
        "N2": 0,
        "CO2": 0,
        "H2S": 0
    }
}

response = requests.post(
    "http://localhost:8000/api/simulation",
    json=simulation_data
)

if response.status_code == 200:
    result = response.json()
    if result["success"]:
        print("仿真成功:")
        print("ASPEN功率输出:", result["aspen_results"]["simulation_results"]["power_output"])
        print("机组选型结果:", result["power_results"]["selection_output"])
        print("综合结果:", json.dumps(result["combined_results"], indent=2, ensure_ascii=False))
    else:
        print(f"仿真失败: {result['error_message']}")
```

### cURL示例

```bash
# 综合仿真计算 (APWZ文件路径通过环境变量控制)
curl -X POST "http://localhost:8000/api/simulation" \
     -H "Content-Type: application/json" \
     -d '{
       "gas_flow_rate": 33333.333333,
       "inlet_pressure": 0.80,
       "inlet_temperature": 20.0,
       "outlet_pressure": 0.30,
       "efficiency": 85,
       "gas_composition": {
         "CH4": 100,
         "C2H6": 0,
         "C3H8": 0,
         "C4H10": 0,
         "N2": 0,
         "CO2": 0,
         "H2S": 0
       }
     }'
```

## 错误处理

API会返回详细的错误信息，包括：

- 参数验证错误
- 文件不存在错误
- 计算执行错误
- 仿真运行错误

所有错误都会在响应中包含 `error_message` 字段，提供具体的错误描述。

## 日志记录

API会自动记录日志到 `logs/` 目录：

- `logs/api.log`: 普通日志
- `logs/api_error.log`: 错误日志

## 注意事项

1. **环境变量配置**: 请确保设置了正确的 `ASPEN_APWZ_FILE_PATH` 环境变量，指向有效的APWZ文件
2. **文件存在性**: 确保APWZ文件路径正确且文件存在
3. **计算模块**: 机组功率计算需要相关的计算模块正常工作
4. **气体组成**: 气体组成的各组分含量总和应为100%
5. **参数范围**: 压力和温度参数应在合理范围内
6. **功率来源**: 主机功率完全由ASPEN仿真自动生成，无需手动指定

## 技术支持

如有问题，请检查：

1. **依赖安装**: 依赖是否正确安装
2. **环境变量**: `ASPEN_APWZ_FILE_PATH` 环境变量是否设置正确
3. **文件存在**: APWZ文件是否存在且可访问
4. **模块导入**: 计算模块是否正常导入
5. **日志信息**: 查看日志文件中的错误信息

### 环境变量检查

```bash
# 检查环境变量是否设置
echo $ASPEN_APWZ_FILE_PATH

# 检查文件是否存在
ls -la $ASPEN_APWZ_FILE_PATH
``` 