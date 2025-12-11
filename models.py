"""
数据模型定义模块

定义PDF转Anki转换器中使用的所有数据模型
"""
from dataclasses import dataclass, field
from enum import Enum
from typing import List, Dict, Any


class QuestionType(Enum):
    """
    题目类型枚举
    
    - SINGLE_CHOICE: 单选题（只有一个正确答案）
    - MULTIPLE_CHOICE: 多选题（有多个正确答案）
    - UNKNOWN: 未知类型（需要人工确认）
    """
    SINGLE_CHOICE = "single"      # 单选题
    MULTIPLE_CHOICE = "multiple"  # 多选题
    UNKNOWN = "unknown"           # 未知类型


@dataclass
class Image:
    """
    图片数据模型
    
    存储从PDF中提取的图片信息
    
    属性:
        data: 图片二进制数据
        format: 图片格式（png、jpg等）
        width: 图片宽度（像素）
        height: 图片高度（像素）
        position: 图片在文档中的位置
    """
    data: bytes       # 图片二进制数据
    format: str       # 图片格式
    width: int        # 宽度
    height: int       # 高度
    position: int     # 位置


@dataclass
class Option:
    """
    选项数据模型
    
    存储题目的单个选项信息
    
    属性:
        label: 选项标识（A、B、C、D等）
        content: 选项内容文本
        images: 选项中包含的图片列表
    """
    label: str                                    # 选项标识
    content: str                                  # 选项内容
    images: List[Image] = field(default_factory=list)  # 选项中的图片


@dataclass
class Question:
    """
    题目数据模型
    
    存储完整的题目信息，包括问题、选项、答案等
    
    属性:
        id: 题目唯一标识
        number: 题目编号（如"1"、"一"、"(1)"等）
        question_text: 问题文本
        options: 选项列表
        correct_answers: 正确答案列表（选项标识）
        question_type: 题目类型（单选/多选/未知）
        explanation: 题目解析/解释
        images: 题目中的图片列表
        needs_review: 是否需要人工审核
        metadata: 额外元数据（如来源文件等）
    """
    id: str                                       # 题目唯一标识
    number: str                                   # 题目编号
    question_text: str                            # 问题文本
    options: List[Option]                         # 选项列表
    correct_answers: List[str]                    # 正确答案
    question_type: QuestionType                   # 题目类型
    explanation: str = ""                         # 题目解析
    images: List[Image] = field(default_factory=list)      # 题目图片
    needs_review: bool = False                    # 是否需要审核
    selected: bool = True                         # 是否选中导出
    metadata: Dict[str, Any] = field(default_factory=dict) # 元数据


@dataclass
class PDFDocument:
    """
    PDF文档数据模型
    
    存储解析后的PDF文档信息
    
    属性:
        file_path: 文件路径
        page_count: 页数
        text_content: 全部文本内容
        images: 文档中的所有图片
        metadata: PDF元数据（如标题、作者等）
    """
    file_path: str                                # 文件路径
    page_count: int                               # 页数
    text_content: str                             # 文本内容
    images: List[Image] = field(default_factory=list)      # 图片列表
    metadata: Dict[str, Any] = field(default_factory=dict) # 元数据
