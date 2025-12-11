"""
自定义异常类模块

定义PDF转Anki转换器中使用的所有异常类型
"""


class PDFConverterError(Exception):
    """
    基础异常类
    
    所有PDF转换器相关异常的基类
    """
    pass


class FileError(PDFConverterError):
    """
    文件相关错误
    
    包括：文件不存在、格式无效、文件损坏、文件过大、权限不足等
    """
    pass


class ParseError(PDFConverterError):
    """
    解析相关错误
    
    包括：PDF加密无法读取、文本提取失败、图片提取失败、题目格式无法识别等
    """
    pass


class ValidationError(PDFConverterError):
    """
    数据验证错误
    
    包括：题目缺少必需字段、选项数量不足、答案标识无效、数据类型不匹配等
    """
    pass


class ExportError(PDFConverterError):
    """
    导出相关错误
    
    包括：输出路径无效、磁盘空间不足、文件写入失败、格式转换失败等
    """
    pass
