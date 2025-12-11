"""UIController协调层模块 - 连接UI和业务逻辑"""
import os
from typing import List, Dict, Any, Optional, Callable
from dataclasses import dataclass

from models import Question, Option, QuestionType, Image
from parsers import PDFParser
from recognizers import QuestionRecognizer
from exporters import CSVExporter, APKGExporter
from question_manager import QuestionManager
from batch_processor import BatchProcessor, ExportMode, BatchProcessingResult
from exceptions import PDFConverterError, FileError, ParseError, ExportError, ValidationError


@dataclass
class LoadResult:
    """PDF加载结果"""
    success: bool
    total_questions: int
    errors: List[str]
    file_path: str = ""


@dataclass
class ExportResult:
    """导出结果"""
    success: bool
    output_path: str
    question_count: int
    error_message: str = ""


class UIController:
    """
    用户界面控制器类
    
    协调用户交互和业务逻辑，连接UI层和核心处理层
    
    职责：
    - 初始化和管理所有组件
    - 处理PDF加载和解析
    - 管理题目的显示和更新
    - 协调导出操作
    
    需求：所有
    """
    
    def __init__(self):
        """
        初始化控制器
        
        创建并初始化所有组件：
        - PDF解析器
        - 题目识别器
        - CSV导出器
        - APKG导出器
        - 题目管理器
        - 批量处理器
        """
        # 初始化核心组件
        self.parser = PDFParser()
        self.recognizer = QuestionRecognizer()
        self.csv_exporter = CSVExporter()
        self.apkg_exporter = APKGExporter()
        self.question_manager = QuestionManager()
        self.batch_processor = BatchProcessor()
        
        # 回调函数
        self._progress_callback: Optional[Callable[[float, str], None]] = None
        self._error_callback: Optional[Callable[[str], None]] = None

    
    def set_progress_callback(self, callback: Callable[[float, str], None]) -> None:
        """
        设置进度回调函数
        
        Args:
            callback: 回调函数，接收进度百分比(0-100)和状态消息
        """
        self._progress_callback = callback
    
    def set_error_callback(self, callback: Callable[[str], None]) -> None:
        """
        设置错误回调函数
        
        Args:
            callback: 回调函数，接收错误消息
        """
        self._error_callback = callback
    
    def _report_progress(self, progress: float, message: str) -> None:
        """报告进度"""
        if self._progress_callback:
            self._progress_callback(progress, message)
    
    def _report_error(self, message: str) -> None:
        """报告错误"""
        if self._error_callback:
            self._error_callback(message)
    
    # ==================== PDF加载功能 ====================
    
    def load_pdf(self, file_path: str) -> LoadResult:
        """
        加载单个PDF文件
        
        解析PDF文件并提取其中的题目
        
        Args:
            file_path: PDF文件路径
            
        Returns:
            LoadResult: 加载结果，包含成功状态、题目数量和错误信息
            
        需求：1.1, 1.2, 1.3, 1.4
        """
        result = LoadResult(
            success=False,
            total_questions=0,
            errors=[],
            file_path=file_path
        )
        
        try:
            self._report_progress(10, f"正在验证文件: {os.path.basename(file_path)}")
            
            # 验证PDF文件
            self.parser.validate_pdf(file_path)
            
            self._report_progress(30, "正在解析PDF内容...")
            
            # 解析PDF文件
            pdf_doc = self.parser.parse_pdf(file_path)
            
            self._report_progress(50, "正在识别题目...")
            
            # 识别题目边界
            question_blocks = self.recognizer.recognize_questions(pdf_doc.text_content)
            
            self._report_progress(70, "正在解析题目结构...")
            
            # 解析每个题目块
            questions_added = 0
            for number, text_block in question_blocks:
                try:
                    question = self.recognizer.parse_question(text_block, number)
                    self.question_manager.add_question(question, source_file=file_path)
                    questions_added += 1
                except ValidationError as e:
                    result.errors.append(f"题目 {number} 解析失败: {str(e)}")
                except Exception as e:
                    result.errors.append(f"题目 {number} 处理错误: {str(e)}")
            
            # 提取图片（如果有）
            try:
                images = self.parser.extract_images(file_path)
                # 图片可以后续关联到题目
            except Exception as e:
                result.errors.append(f"图片提取警告: {str(e)}")
            
            self._report_progress(100, "加载完成")
            
            result.success = True
            result.total_questions = questions_added
            
        except FileError as e:
            result.errors.append(f"文件错误: {str(e)}")
            self._report_error(str(e))
        except ParseError as e:
            result.errors.append(f"解析错误: {str(e)}")
            self._report_error(str(e))
        except PDFConverterError as e:
            result.errors.append(f"处理错误: {str(e)}")
            self._report_error(str(e))
        except Exception as e:
            result.errors.append(f"未知错误: {str(e)}")
            self._report_error(str(e))
        
        return result
    
    def load_multiple_pdfs(self, file_paths: List[str]) -> BatchProcessingResult:
        """
        加载多个PDF文件（批量处理）
        
        Args:
            file_paths: PDF文件路径列表
            
        Returns:
            BatchProcessingResult: 批量处理结果
            
        需求：7.1, 7.2, 7.4
        """
        # 清空之前的数据
        self.question_manager.clear()
        
        # 使用批量处理器
        total_files = len(file_paths)
        
        for i, file_path in enumerate(file_paths):
            progress = (i / total_files) * 100
            self._report_progress(progress, f"正在处理: {os.path.basename(file_path)}")
        
        result = self.batch_processor.process_files(file_paths)
        
        # 同步批量处理器的题目到控制器的题目管理器
        self.question_manager = self.batch_processor.question_manager
        
        self._report_progress(100, f"批量处理完成，共 {result.total_questions} 道题目")
        
        return result

    
    # ==================== 题目显示功能 ====================
    
    def display_questions(self, filter_type: str = "all") -> List[Question]:
        """
        获取要显示的题目列表
        
        根据筛选条件返回题目列表
        
        Args:
            filter_type: 筛选类型
                - "all": 所有题目
                - "review": 需要审核的题目
                - "single": 单选题
                - "multiple": 多选题
                
        Returns:
            List[Question]: 筛选后的题目列表
            
        需求：3.1, 3.5
        """
        if filter_type == "all":
            return self.question_manager.get_all_questions()
        elif filter_type == "review":
            return self.question_manager.get_questions_needing_review()
        elif filter_type == "single":
            return self.question_manager.get_questions_by_type(QuestionType.SINGLE_CHOICE)
        elif filter_type == "multiple":
            return self.question_manager.get_questions_by_type(QuestionType.MULTIPLE_CHOICE)
        else:
            return self.question_manager.get_all_questions()
    
    def get_question(self, question_id: str) -> Optional[Question]:
        """
        获取单个题目
        
        Args:
            question_id: 题目ID
            
        Returns:
            Optional[Question]: 题目对象，不存在则返回None
            
        需求：3.2
        """
        return self.question_manager.get_question(question_id)
    
    def get_question_count(self) -> int:
        """
        获取题目总数
        
        Returns:
            int: 题目数量
        """
        return self.question_manager.count()
    
    def get_questions_by_source(self, source_file: str) -> List[Question]:
        """
        根据源文件获取题目
        
        Args:
            source_file: 源文件路径
            
        Returns:
            List[Question]: 来自指定源文件的题目列表
        """
        return self.question_manager.get_questions_by_source(source_file)
    
    # ==================== 题目更新功能 ====================
    
    def update_question(self, question_id: str, updates: Dict[str, Any]) -> Question:
        """
        更新题目内容
        
        Args:
            question_id: 要更新的题目ID
            updates: 更新数据字典，可包含以下字段：
                - question_text: 问题文本
                - options: 选项列表
                - correct_answers: 正确答案列表
                - question_type: 题目类型
                - needs_review: 是否需要审核
                - number: 题目编号
                - metadata: 元数据
                
        Returns:
            Question: 更新后的题目对象
            
        Raises:
            ValidationError: 如果题目不存在或更新数据无效
            
        需求：3.3, 3.4
        """
        return self.question_manager.update_question(question_id, updates)
    
    def delete_question(self, question_id: str) -> bool:
        """
        删除题目
        
        Args:
            question_id: 要删除的题目ID
            
        Returns:
            bool: 删除成功返回True，题目不存在返回False
        """
        return self.question_manager.remove_question(question_id)
    
    def clear_questions(self) -> None:
        """清空所有题目"""
        self.question_manager.clear()
    
    def select_question(self, question_id: str, selected: bool = True) -> bool:
        """
        设置题目的选中状态
        
        Args:
            question_id: 题目ID
            selected: 是否选中
            
        Returns:
            bool: 操作是否成功
        """
        return self.question_manager.select_question(question_id, selected)
    
    def select_all_questions(self, selected: bool = True) -> None:
        """
        选中或取消选中所有题目
        
        Args:
            selected: 是否选中
        """
        self.question_manager.select_all(selected)
    
    def get_selected_count(self) -> int:
        """
        获取被选中的题目数量
        
        Returns:
            int: 被选中的题目数量
        """
        return self.question_manager.get_selected_count()

    
    # ==================== 导出功能 ====================
    
    def export_to_csv(self, output_path: str, selected_only: bool = False) -> ExportResult:
        """
        导出题目为CSV格式
        
        Args:
            output_path: 输出文件路径
            selected_only: 是否只导出选中的题目
            
        Returns:
            ExportResult: 导出结果
            
        需求：4.1, 4.2, 4.3, 4.4, 4.5
        """
        result = ExportResult(
            success=False,
            output_path=output_path,
            question_count=0
        )
        
        try:
            if selected_only:
                questions = self.question_manager.get_selected_questions()
            else:
                questions = self.question_manager.get_all_questions()
            
            if not questions:
                result.error_message = "没有可导出的题目" if not selected_only else "没有选中的题目"
                return result
            
            self._report_progress(50, "正在生成CSV文件...")
            
            self.csv_exporter.export(questions, output_path)
            
            self._report_progress(100, "CSV导出完成")
            
            result.success = True
            result.question_count = len(questions)
            
        except ExportError as e:
            result.error_message = str(e)
            self._report_error(str(e))
        except Exception as e:
            result.error_message = f"导出错误: {str(e)}"
            self._report_error(result.error_message)
        
        return result
    
    def export_to_apkg(self, output_path: str, deck_name: str = "PDF题目", selected_only: bool = False) -> ExportResult:
        """
        导出题目为APKG格式
        
        Args:
            output_path: 输出文件路径
            deck_name: Anki卡片组名称
            selected_only: 是否只导出选中的题目
            
        Returns:
            ExportResult: 导出结果
            
        需求：5.1, 5.2, 5.3, 5.4, 5.5
        """
        result = ExportResult(
            success=False,
            output_path=output_path,
            question_count=0
        )
        
        try:
            if selected_only:
                questions = self.question_manager.get_selected_questions()
            else:
                questions = self.question_manager.get_all_questions()
            
            if not questions:
                result.error_message = "没有可导出的题目" if not selected_only else "没有选中的题目"
                return result
            
            self._report_progress(30, "正在创建Anki卡片组...")
            
            # 创建新的导出器实例以确保干净的状态
            exporter = APKGExporter(deck_name=deck_name)
            
            self._report_progress(60, "正在生成APKG文件...")
            
            exporter.export(questions, output_path, deck_name)
            
            self._report_progress(100, "APKG导出完成")
            
            result.success = True
            result.question_count = len(questions)
            
        except ExportError as e:
            result.error_message = str(e)
            self._report_error(str(e))
        except Exception as e:
            result.error_message = f"导出错误: {str(e)}"
            self._report_error(result.error_message)
        
        return result
    
    def export_batch(
        self, 
        output_path: str, 
        format: str = "csv", 
        mode: str = "merged",
        deck_name: str = "PDF题目"
    ) -> Dict[str, Any]:
        """
        批量导出题目
        
        Args:
            output_path: 输出路径（合并模式为文件路径，分离模式为目录路径）
            format: 导出格式 ("csv" 或 "apkg")
            mode: 导出模式 ("merged" 或 "separate")
            deck_name: APKG卡片组名称（仅合并模式使用）
            
        Returns:
            Dict[str, Any]: 导出结果信息
            
        需求：7.3
        """
        export_mode = ExportMode.MERGED if mode == "merged" else ExportMode.SEPARATE
        
        self._report_progress(50, f"正在导出为{format.upper()}格式...")
        
        result = self.batch_processor.export(
            output_path=output_path,
            format=format,
            mode=export_mode,
            deck_name=deck_name
        )
        
        self._report_progress(100, "批量导出完成")
        
        return result

    
    # ==================== 辅助方法 ====================
    
    def validate_pdf_file(self, file_path: str) -> bool:
        """
        验证PDF文件是否有效
        
        Args:
            file_path: PDF文件路径
            
        Returns:
            bool: 文件有效返回True
            
        Raises:
            FileError: 文件无效时抛出
        """
        return self.parser.validate_pdf(file_path)
    
    def get_statistics(self) -> Dict[str, Any]:
        """
        获取当前题目统计信息
        
        Returns:
            Dict[str, Any]: 统计信息字典
        """
        all_questions = self.question_manager.get_all_questions()
        
        single_count = len([q for q in all_questions if q.question_type == QuestionType.SINGLE_CHOICE])
        multiple_count = len([q for q in all_questions if q.question_type == QuestionType.MULTIPLE_CHOICE])
        unknown_count = len([q for q in all_questions if q.question_type == QuestionType.UNKNOWN])
        review_count = len([q for q in all_questions if q.needs_review])
        
        return {
            "total": len(all_questions),
            "single_choice": single_count,
            "multiple_choice": multiple_count,
            "unknown": unknown_count,
            "needs_review": review_count
        }
    
    def format_question_for_display(self, question: Question) -> str:
        """
        格式化题目用于显示（包含解析）
        
        Args:
            question: 题目对象
            
        Returns:
            str: 格式化后的题目文本
        """
        lines = []
        
        # 题目编号和类型
        type_text = {
            QuestionType.SINGLE_CHOICE: "单选题",
            QuestionType.MULTIPLE_CHOICE: "多选题",
            QuestionType.UNKNOWN: "未知类型"
        }.get(question.question_type, "未知类型")
        
        lines.append(f"题目编号: {question.number}")
        lines.append(f"题目类型: {type_text}")
        lines.append(f"状态: {'需要审核' if question.needs_review else '正常'}")
        lines.append(f"选中导出: {'是' if question.selected else '否'}")
        lines.append(f"题目ID: {question.id}")
        lines.append("")
        lines.append("=" * 40)
        lines.append("")
        
        # 问题文本
        lines.append(f"【问题】")
        lines.append(question.question_text)
        lines.append("")
        
        # 选项
        lines.append("【选项】")
        for option in question.options:
            lines.append(f"  {option.label}. {option.content}")
        
        # 答案
        lines.append("")
        if question.correct_answers:
            lines.append(f"【正确答案】 {', '.join(question.correct_answers)}")
        else:
            lines.append("【正确答案】 未知")
        
        # 解析
        if question.explanation:
            lines.append("")
            lines.append("【解析】")
            lines.append(question.explanation)
        
        # 图片信息
        if question.images:
            lines.append(f"\n包含 {len(question.images)} 张图片")
        
        return "\n".join(lines)
    
    def create_question(
        self,
        number: str,
        question_text: str,
        options: List[Option],
        correct_answers: List[str],
        question_type: QuestionType = None,
        source_file: str = ""
    ) -> Question:
        """
        创建新题目并添加到管理器
        
        Args:
            number: 题目编号
            question_text: 问题文本
            options: 选项列表
            correct_answers: 正确答案列表
            question_type: 题目类型（可选，会自动推断）
            source_file: 源文件路径（可选）
            
        Returns:
            Question: 创建的题目对象
        """
        import uuid
        
        # 自动推断题目类型
        if question_type is None:
            if len(correct_answers) == 0:
                question_type = QuestionType.UNKNOWN
            elif len(correct_answers) == 1:
                question_type = QuestionType.SINGLE_CHOICE
            else:
                question_type = QuestionType.MULTIPLE_CHOICE
        
        question = Question(
            id=str(uuid.uuid4()),
            number=number,
            question_text=question_text,
            options=options,
            correct_answers=correct_answers,
            question_type=question_type,
            images=[],
            needs_review=False,
            metadata={}
        )
        
        self.question_manager.add_question(question, source_file)
        
        return question
