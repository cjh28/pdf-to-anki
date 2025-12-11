"""题目管理器模块 - 实现题目的存储、查询、更新和删除功能"""
from typing import List, Optional, Dict, Any
from dataclasses import replace
import copy

from models import Question, Option, QuestionType
from exceptions import ValidationError


class QuestionManager:
    """
    题目列表管理类
    
    提供题目的添加、删除、查询和更新功能
    """
    
    def __init__(self):
        """初始化题目管理器"""
        self._questions: Dict[str, Question] = {}  # 使用字典存储，key为题目ID
        self._source_file_map: Dict[str, str] = {}  # 题目ID到源文件的映射
    
    def add_question(self, question: Question, source_file: str = "") -> str:
        """
        添加题目到管理器
        
        Args:
            question: 要添加的题目对象
            source_file: 题目来源的PDF文件路径（可选）
            
        Returns:
            str: 添加的题目ID
            
        Raises:
            ValidationError: 如果题目ID已存在或题目无效
        """
        if not question:
            raise ValidationError("题目不能为空")
        
        if not question.id:
            raise ValidationError("题目ID不能为空")
        
        if question.id in self._questions:
            raise ValidationError(f"题目ID '{question.id}' 已存在")
        
        self._questions[question.id] = question
        if source_file:
            self._source_file_map[question.id] = source_file
        
        return question.id
    
    def add_questions(self, questions: List[Question], source_file: str = "") -> List[str]:
        """
        批量添加题目
        
        Args:
            questions: 题目列表
            source_file: 题目来源的PDF文件路径（可选）
            
        Returns:
            List[str]: 添加的题目ID列表
        """
        added_ids = []
        for question in questions:
            question_id = self.add_question(question, source_file)
            added_ids.append(question_id)
        return added_ids

    
    def remove_question(self, question_id: str) -> bool:
        """
        删除指定ID的题目
        
        Args:
            question_id: 要删除的题目ID
            
        Returns:
            bool: 删除成功返回True，题目不存在返回False
        """
        if question_id not in self._questions:
            return False
        
        del self._questions[question_id]
        if question_id in self._source_file_map:
            del self._source_file_map[question_id]
        
        return True
    
    def get_question(self, question_id: str) -> Optional[Question]:
        """
        根据ID查询题目
        
        Args:
            question_id: 题目ID
            
        Returns:
            Optional[Question]: 题目对象，不存在则返回None
        """
        return self._questions.get(question_id)
    
    def get_all_questions(self) -> List[Question]:
        """
        获取所有题目
        
        Returns:
            List[Question]: 所有题目的列表
        """
        return list(self._questions.values())
    
    def get_selected_questions(self) -> List[Question]:
        """
        获取所有被选中的题目（用于导出）
        
        Returns:
            List[Question]: 被选中的题目列表
        """
        return [q for q in self._questions.values() if q.selected]
    
    def select_question(self, question_id: str, selected: bool = True) -> bool:
        """
        设置题目的选中状态
        
        Args:
            question_id: 题目ID
            selected: 是否选中
            
        Returns:
            bool: 操作是否成功
        """
        if question_id not in self._questions:
            return False
        
        question = self._questions[question_id]
        from dataclasses import replace
        self._questions[question_id] = replace(question, selected=selected)
        return True
    
    def select_all(self, selected: bool = True) -> None:
        """
        选中或取消选中所有题目
        
        Args:
            selected: 是否选中
        """
        from dataclasses import replace
        for qid in self._questions:
            question = self._questions[qid]
            self._questions[qid] = replace(question, selected=selected)
    
    def get_selected_count(self) -> int:
        """
        获取被选中的题目数量
        
        Returns:
            int: 被选中的题目数量
        """
        return len([q for q in self._questions.values() if q.selected])
    
    def get_questions_by_source(self, source_file: str) -> List[Question]:
        """
        根据源文件获取题目
        
        Args:
            source_file: 源文件路径
            
        Returns:
            List[Question]: 来自指定源文件的题目列表
        """
        question_ids = [
            qid for qid, src in self._source_file_map.items() 
            if src == source_file
        ]
        return [self._questions[qid] for qid in question_ids if qid in self._questions]
    
    def get_questions_needing_review(self) -> List[Question]:
        """
        获取需要人工审核的题目
        
        Returns:
            List[Question]: 需要审核的题目列表
        """
        return [q for q in self._questions.values() if q.needs_review]
    
    def get_questions_by_type(self, question_type: QuestionType) -> List[Question]:
        """
        根据题目类型获取题目
        
        Args:
            question_type: 题目类型
            
        Returns:
            List[Question]: 指定类型的题目列表
        """
        return [q for q in self._questions.values() if q.question_type == question_type]
    
    def count(self) -> int:
        """
        获取题目总数
        
        Returns:
            int: 题目数量
        """
        return len(self._questions)
    
    def clear(self) -> None:
        """清空所有题目"""
        self._questions.clear()
        self._source_file_map.clear()
    
    def contains(self, question_id: str) -> bool:
        """
        检查题目是否存在
        
        Args:
            question_id: 题目ID
            
        Returns:
            bool: 存在返回True，否则返回False
        """
        return question_id in self._questions

    
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
                - metadata: 元数据
            
        Returns:
            Question: 更新后的题目对象
            
        Raises:
            ValidationError: 如果题目不存在或更新数据无效
        """
        if question_id not in self._questions:
            raise ValidationError(f"题目ID '{question_id}' 不存在")
        
        # 验证更新数据
        self._validate_updates(updates)
        
        # 获取当前题目
        current_question = self._questions[question_id]
        
        # 构建更新后的题目
        updated_fields = {}
        
        if 'question_text' in updates:
            updated_fields['question_text'] = updates['question_text']
        
        if 'options' in updates:
            updated_fields['options'] = updates['options']
        
        if 'correct_answers' in updates:
            updated_fields['correct_answers'] = updates['correct_answers']
        
        if 'question_type' in updates:
            updated_fields['question_type'] = updates['question_type']
        
        if 'needs_review' in updates:
            updated_fields['needs_review'] = updates['needs_review']
        
        if 'metadata' in updates:
            # 合并元数据而不是替换
            new_metadata = copy.deepcopy(current_question.metadata)
            new_metadata.update(updates['metadata'])
            updated_fields['metadata'] = new_metadata
        
        if 'number' in updates:
            updated_fields['number'] = updates['number']
        
        # 使用dataclass的replace创建更新后的对象
        updated_question = replace(current_question, **updated_fields)
        
        # 如果更新了答案数量，自动更新题目类型
        if 'correct_answers' in updates and 'question_type' not in updates:
            updated_question = self._auto_update_question_type(updated_question)
        
        # 存储更新后的题目
        self._questions[question_id] = updated_question
        
        return updated_question
    
    def _validate_updates(self, updates: Dict[str, Any]) -> None:
        """
        验证更新数据的有效性
        
        Args:
            updates: 更新数据字典
            
        Raises:
            ValidationError: 如果更新数据无效
        """
        if not updates:
            raise ValidationError("更新数据不能为空")
        
        # 验证问题文本
        if 'question_text' in updates:
            if not isinstance(updates['question_text'], str):
                raise ValidationError("问题文本必须是字符串")
        
        # 验证选项
        if 'options' in updates:
            options = updates['options']
            if not isinstance(options, list):
                raise ValidationError("选项必须是列表")
            for opt in options:
                if not isinstance(opt, Option):
                    raise ValidationError("选项列表中的元素必须是Option对象")
        
        # 验证正确答案
        if 'correct_answers' in updates:
            answers = updates['correct_answers']
            if not isinstance(answers, list):
                raise ValidationError("正确答案必须是列表")
            for ans in answers:
                if not isinstance(ans, str):
                    raise ValidationError("正确答案列表中的元素必须是字符串")
        
        # 验证题目类型
        if 'question_type' in updates:
            if not isinstance(updates['question_type'], QuestionType):
                raise ValidationError("题目类型必须是QuestionType枚举值")
        
        # 验证needs_review
        if 'needs_review' in updates:
            if not isinstance(updates['needs_review'], bool):
                raise ValidationError("needs_review必须是布尔值")
        
        # 验证metadata
        if 'metadata' in updates:
            if not isinstance(updates['metadata'], dict):
                raise ValidationError("metadata必须是字典")
        
        # 验证number
        if 'number' in updates:
            if not isinstance(updates['number'], str):
                raise ValidationError("题目编号必须是字符串")
    
    def _auto_update_question_type(self, question: Question) -> Question:
        """
        根据答案数量自动更新题目类型
        
        Args:
            question: 题目对象
            
        Returns:
            Question: 更新类型后的题目对象
        """
        num_answers = len(question.correct_answers)
        
        if num_answers == 0:
            new_type = QuestionType.UNKNOWN
        elif num_answers == 1:
            new_type = QuestionType.SINGLE_CHOICE
        else:
            new_type = QuestionType.MULTIPLE_CHOICE
        
        if question.question_type != new_type:
            return replace(question, question_type=new_type)
        
        return question
