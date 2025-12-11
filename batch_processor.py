"""批量处理模块 - 实现多PDF文件批量处理和导出功能"""
import os
from dataclasses import dataclass, field
from enum import Enum
from typing import List, Dict, Optional, Tuple, Any

from models import Question
from parsers import PDFParser
from recognizers import QuestionRecognizer
from exporters import CSVExporter, APKGExporter
from question_manager import QuestionManager
from exceptions import PDFConverterError, FileError, ParseError, ExportError


class ExportMode(Enum):
    """导出模式枚举"""
    MERGED = "merged"      # 合并模式：所有题目导出到一个文件
    SEPARATE = "separate"  # 分离模式：每个源文件对应一个输出文件


@dataclass
class ProcessingResult:
    """单个文件处理结果"""
    file_path: str
    success: bool
    questions: List[Question] = field(default_factory=list)
    error_message: str = ""
    question_count: int = 0


@dataclass
class BatchProcessingResult:
    """批量处理结果"""
    total_files: int = 0
    successful_files: int = 0
    failed_files: int = 0
    total_questions: int = 0
    results: List[ProcessingResult] = field(default_factory=list)
    errors: Dict[str, str] = field(default_factory=dict)


class BatchProcessor:
    """
    批量处理器类
    
    实现多PDF文件的批量处理和导出功能
    需求：7.1, 7.3, 7.4
    """
    
    def __init__(self):
        """初始化批量处理器"""
        self.parser = PDFParser()
        self.recognizer = QuestionRecognizer()
        self.question_manager = QuestionManager()
        self.csv_exporter = CSVExporter()
        self.apkg_exporter = APKGExporter()

    
    def process_single_file(self, file_path: str) -> ProcessingResult:
        """
        处理单个PDF文件
        
        Args:
            file_path: PDF文件路径
            
        Returns:
            ProcessingResult: 处理结果
        """
        result = ProcessingResult(file_path=file_path, success=False)
        
        try:
            # 解析PDF文件
            pdf_doc = self.parser.parse_pdf(file_path)
            
            # 识别题目
            question_blocks = self.recognizer.recognize_questions(pdf_doc.text_content)
            
            # 解析每个题目块
            questions = []
            for number, text_block in question_blocks:
                try:
                    question = self.recognizer.parse_question(text_block, number)
                    questions.append(question)
                except Exception as e:
                    # 单个题目解析失败不影响其他题目
                    continue
            
            result.success = True
            result.questions = questions
            result.question_count = len(questions)
            
        except FileError as e:
            result.error_message = f"文件错误: {str(e)}"
        except ParseError as e:
            result.error_message = f"解析错误: {str(e)}"
        except PDFConverterError as e:
            result.error_message = f"处理错误: {str(e)}"
        except Exception as e:
            result.error_message = f"未知错误: {str(e)}"
        
        return result
    
    def process_files(self, file_paths: List[str]) -> BatchProcessingResult:
        """
        批量处理多个PDF文件
        
        实现错误恢复机制：单个文件失败不影响其他文件
        
        Args:
            file_paths: PDF文件路径列表
            
        Returns:
            BatchProcessingResult: 批量处理结果
            
        需求：7.1, 7.4
        """
        batch_result = BatchProcessingResult(total_files=len(file_paths))
        
        # 清空之前的题目
        self.question_manager.clear()
        
        for file_path in file_paths:
            # 处理单个文件
            result = self.process_single_file(file_path)
            batch_result.results.append(result)
            
            if result.success:
                batch_result.successful_files += 1
                batch_result.total_questions += result.question_count
                
                # 将题目添加到管理器
                for question in result.questions:
                    try:
                        self.question_manager.add_question(question, source_file=file_path)
                    except Exception:
                        # 忽略重复ID等错误
                        pass
            else:
                batch_result.failed_files += 1
                batch_result.errors[file_path] = result.error_message
        
        return batch_result

    
    def export_csv_merged(self, output_path: str) -> None:
        """
        合并模式导出CSV：所有题目导出到一个文件
        
        Args:
            output_path: 输出文件路径
            
        Raises:
            ExportError: 导出失败时抛出
            
        需求：7.3
        """
        questions = self.question_manager.get_all_questions()
        if not questions:
            raise ExportError("没有可导出的题目")
        
        self.csv_exporter.export(questions, output_path)
    
    def export_csv_separate(self, output_dir: str) -> Dict[str, str]:
        """
        分离模式导出CSV：每个源文件对应一个输出文件
        
        Args:
            output_dir: 输出目录路径
            
        Returns:
            Dict[str, str]: 源文件到输出文件的映射
            
        Raises:
            ExportError: 导出失败时抛出
            
        需求：7.3
        """
        # 确保输出目录存在
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)
        
        output_files = {}
        source_files = self._get_unique_source_files()
        
        for source_file in source_files:
            questions = self.question_manager.get_questions_by_source(source_file)
            if questions:
                # 生成输出文件名
                base_name = os.path.splitext(os.path.basename(source_file))[0]
                output_path = os.path.join(output_dir, f"{base_name}.csv")
                
                self.csv_exporter.export(questions, output_path)
                output_files[source_file] = output_path
        
        return output_files
    
    def export_apkg_merged(self, output_path: str, deck_name: str = "PDF题目") -> None:
        """
        合并模式导出APKG：所有题目导出到一个文件
        
        Args:
            output_path: 输出文件路径
            deck_name: 卡片组名称
            
        Raises:
            ExportError: 导出失败时抛出
            
        需求：7.3
        """
        questions = self.question_manager.get_all_questions()
        if not questions:
            raise ExportError("没有可导出的题目")
        
        self.apkg_exporter.export(questions, output_path, deck_name)
    
    def export_apkg_separate(self, output_dir: str) -> Dict[str, str]:
        """
        分离模式导出APKG：每个源文件对应一个输出文件
        
        Args:
            output_dir: 输出目录路径
            
        Returns:
            Dict[str, str]: 源文件到输出文件的映射
            
        Raises:
            ExportError: 导出失败时抛出
            
        需求：7.3
        """
        # 确保输出目录存在
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)
        
        output_files = {}
        source_files = self._get_unique_source_files()
        
        for source_file in source_files:
            questions = self.question_manager.get_questions_by_source(source_file)
            if questions:
                # 生成输出文件名和卡片组名称
                base_name = os.path.splitext(os.path.basename(source_file))[0]
                output_path = os.path.join(output_dir, f"{base_name}.apkg")
                
                # 为每个文件创建新的导出器实例
                exporter = APKGExporter(deck_name=base_name)
                exporter.export(questions, output_path, base_name)
                output_files[source_file] = output_path
        
        return output_files

    
    def export(
        self, 
        output_path: str, 
        format: str = "csv", 
        mode: ExportMode = ExportMode.MERGED,
        deck_name: str = "PDF题目"
    ) -> Dict[str, Any]:
        """
        统一导出接口
        
        Args:
            output_path: 输出路径（合并模式为文件路径，分离模式为目录路径）
            format: 导出格式 ("csv" 或 "apkg")
            mode: 导出模式
            deck_name: APKG卡片组名称（仅合并模式使用）
            
        Returns:
            Dict[str, Any]: 导出结果信息
            
        Raises:
            ExportError: 导出失败时抛出
            
        需求：7.3
        """
        result = {
            "format": format,
            "mode": mode.value,
            "output_files": []
        }
        
        if mode == ExportMode.MERGED:
            if format.lower() == "csv":
                self.export_csv_merged(output_path)
            else:
                self.export_apkg_merged(output_path, deck_name)
            result["output_files"] = [output_path]
        else:  # SEPARATE mode
            if format.lower() == "csv":
                output_files = self.export_csv_separate(output_path)
            else:
                output_files = self.export_apkg_separate(output_path)
            result["output_files"] = list(output_files.values())
            result["source_mapping"] = output_files
        
        return result
    
    def _get_unique_source_files(self) -> List[str]:
        """
        获取所有唯一的源文件路径
        
        Returns:
            List[str]: 源文件路径列表
        """
        source_files = set()
        for question in self.question_manager.get_all_questions():
            # 从question_manager的内部映射获取源文件
            if question.id in self.question_manager._source_file_map:
                source_files.add(self.question_manager._source_file_map[question.id])
        return list(source_files)
    
    def get_questions_count(self) -> int:
        """
        获取当前处理的题目总数
        
        Returns:
            int: 题目数量
        """
        return self.question_manager.count()
    
    def get_all_questions(self) -> List[Question]:
        """
        获取所有已处理的题目
        
        Returns:
            List[Question]: 题目列表
        """
        return self.question_manager.get_all_questions()
    
    def clear(self) -> None:
        """清空所有已处理的数据"""
        self.question_manager.clear()
