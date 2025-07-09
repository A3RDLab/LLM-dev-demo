import logging
import os
import datetime
from typing import Dict, Any, List, Optional

# 确保日志目录存在
log_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'logs')
os.makedirs(log_dir, exist_ok=True)

# 获取当前日期作为日志文件名的一部分
current_date = datetime.datetime.now().strftime('%Y-%m-%d')
log_file = os.path.join(log_dir, f'model_interactions_{current_date}.log')

# 配置日志记录器
logger = logging.getLogger('model_interactions')
logger.setLevel(logging.INFO)

# 创建文件处理器
file_handler = logging.FileHandler(log_file, encoding='utf-8')
file_handler.setLevel(logging.INFO)

# 创建控制台处理器
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.INFO)

# 创建格式化器
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
file_handler.setFormatter(formatter)
console_handler.setFormatter(formatter)

# 添加处理器到日志记录器
logger.addHandler(file_handler)
logger.addHandler(console_handler)


def log_model_request(messages: List[Dict[str, Any]], model: str = 'unknown') -> None:
    """
    记录发送给模型的请求
    
    Args:
        messages: 发送给模型的消息列表
        model: 模型名称
    """
    # 只记录最后一条消息，避免重复记录已经记录过的消息
    if not messages:
        return
        
    logger.info(f"===== 发送请求到模型: {model} =====")
    # 只记录最后一条消息
    last_msg = messages[-1]
    role = last_msg.get('role', 'unknown') if isinstance(last_msg, dict) else getattr(last_msg, 'role', 'unknown')
    content = last_msg.get('content', '') if isinstance(last_msg, dict) else getattr(last_msg, 'content', '')
    logger.info(f"角色: {role}")
    logger.info(f"内容: {content}")
    logger.info("===== 请求结束 =====")


def log_model_response(response_message: Dict[str, Any], model: str = 'unknown') -> None:
    """
    记录模型的响应
    
    Args:
        response_message: 模型的响应消息
        model: 模型名称
    """
    logger.info(f"===== 收到模型响应: {model} =====")
    
    # 正确处理不同类型的响应消息对象
    if isinstance(response_message, dict):
        role = response_message.get('role', 'unknown')
        content = response_message.get('content', '')
        tool_calls = response_message.get('tool_calls', [])
    else:
        role = getattr(response_message, 'role', 'unknown')
        content = getattr(response_message, 'content', '')
        tool_calls = getattr(response_message, 'tool_calls', [])
    
    logger.info(f"角色: {role}")
    logger.info(f"内容: {content}")
    
    # 记录工具调用信息（如果有）
    if tool_calls:
        logger.info("工具调用:")
        for tool_call in tool_calls:
            # 处理不同类型的tool_call对象
            if isinstance(tool_call, dict) and 'function' in tool_call:
                function_name = tool_call['function'].get('name', 'unknown')
                function_args = tool_call['function'].get('arguments', '{}')
            else:
                function_name = getattr(tool_call.function, 'name', 'unknown')
                function_args = getattr(tool_call.function, 'arguments', '{}')
                
            logger.info(f"  - 函数: {function_name}")
            logger.info(f"  - 参数: {function_args}")
    
    logger.info("===== 响应结束 =====")


def log_tool_result(function_name: str, result: Any) -> None:
    """
    记录工具执行结果
    
    Args:
        function_name: 工具函数名称
        result: 执行结果，可能是任何类型
    """
    logger.info(f"===== 工具执行结果: {function_name} =====")
    # 确保结果是字符串类型
    if not isinstance(result, str):
        try:
            result_str = str(result)
        except Exception:
            result_str = "<无法转换为字符串的结果>"
    else:
        result_str = result
        
    logger.info(f"结果: {result_str}")
    logger.info("===== 执行结束 =====")