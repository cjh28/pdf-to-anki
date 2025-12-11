"""题目识别器模块"""
import re
import uuid
from typing import List, Tuple, Optional

from models import Question, Option, QuestionType, Image
from exceptions import ParseError, ValidationError


class QuestionRecognizer:
    """题目识别器类"""
    
    # 题目编号正则表达式模式 - 支持多种格式
    QUESTION_NUMBER_PATTERNS = [
        # 数字格式: 1. 1、 1) 1: （支持行首或换行后）
        r'(?:^|\n)\s*(\d+)\s*[.、\):：]\s*',
        # 中文数字格式: 一、 二、 (一) （一）
        r'(?:^|\n)\s*[（(]?([一二三四五六七八九十百]+)[）)]?\s*[、.．:：]\s*',
        # 带括号的数字: (1) （1）
        r'(?:^|\n)\s*[（(](\d+)[）)]\s*',
        # 题目前缀格式: 第1题 第一题
        r'(?:^|\n)\s*第\s*(\d+|[一二三四五六七八九十百]+)\s*题[.、:：]?\s*',
    ]
    
    # 选项标识正则表达式模式 - 支持多种格式
    OPTION_LABEL_PATTERNS = [
        # 大写字母: A. A、 A) (A) A:
        r'[（\(]?([A-Z])[）\)]?\s*[.、\)）:：]?',
        # 小写字母: a. a、 a) (a) a:
        r'[（\(]?([a-z])[）\)]?\s*[.、\)）:：]?',
        # 数字圈: ① ② ③ ④
        r'([①②③④⑤⑥⑦⑧⑨⑩])',
    ]
    
    # 答案标注正则表达式模式 - 支持多种格式（增强版）
    ANSWER_PATTERNS = [
        # 【答案】A 【答案】AB 【答案】A、B （最常见格式，优先匹配）
        r'【(?:答案|正确答案|参考答案|本题答案)】\s*[：:]?\s*([A-Za-z①②③④⑤⑥⑦⑧⑨⑩、,，\s]+)',
        # (答案：A) （答案：AB）
        r'[（\(](?:答案|正确答案|参考答案)[：:]\s*([A-Za-z①②③④⑤⑥⑦⑧⑨⑩、,，]+)[）\)]',
        # 答案：A 答案:A 答案: A、B （支持更宽松的匹配）
        r'(?:答案|正确答案|参考答案|本题答案)\s*[：:]\s*([A-Za-z①②③④⑤⑥⑦⑧⑨⑩、,，\s]+)',
        # 答案A (无分隔符)
        r'(?:答案|正确答案|参考答案)\s+([A-Za-z①②③④⑤⑥⑦⑧⑨⑩]+)',
        # 选A 选B 选AB
        r'(?:应选|选)\s*([A-Za-z]+)',
        # A√ B√ 带勾选标记
        r'([A-Z])\s*[√✓]',
        # 正确选项为A
        r'正确(?:选项|答案)(?:为|是)\s*([A-Za-z①②③④⑤⑥⑦⑧⑨⑩、,，]+)',
        # 单独一行的答案格式：A 或 AB 或 A、B（在解析区域内）
        r'(?:^|\n)\s*答案\s*[：:]*\s*([A-Za-z]+)\s*(?:\n|$)',
        # 答 案 格式（中间有空格）
        r'答\s*案\s*[：:]*\s*([A-Za-z]+)',
        # [答案]A 格式
        r'\[(?:答案|正确答案|参考答案)\]\s*[：:]?\s*([A-Za-z①②③④⑤⑥⑦⑧⑨⑩、,，]+)',
        # 故选A 故选择A
        r'故\s*选\s*(?:择)?\s*([A-Za-z]+)',
        # 本题选A
        r'本题\s*选\s*([A-Za-z]+)',
    ]
    
    # 解析标注正则表达式模式
    EXPLANATION_PATTERNS = [
        # 【解析】内容 - 匹配到下一个【标记或文本结束
        r'【(?:解析|解答|分析|详解|答案解析)】\s*([\s\S]+?)(?=【(?:正确答案|答案|解析|解答|分析|详解)】|\n\s*\d+\s*[.、．]\s*【|$)',
        # 【答案解析】内容
        r'【答案解析】\s*([\s\S]+?)(?=【(?:正确答案|答案)】|\n\s*\d+\s*[.、．]\s*【|$)',
        # 解析：内容 - 匹配到下一个题目或文本结束
        r'(?:解析|解答|分析|详解|答案解析)\s*[：:]\s*([\s\S]+?)(?=\n\s*\d+\s*[.、．]\s*(?:【|[A-Z])|$)',
        # [解析]内容
        r'\[(?:解析|解答|分析)\]\s*([\s\S]+?)(?=\[(?:正确答案|答案)\]|\n\s*\d+\s*[.、．]|$)',
    ]
    
    # 圆圈数字到字母的映射
    CIRCLE_TO_LETTER = {
        '①': 'A', '②': 'B', '③': 'C', '④': 'D',
        '⑤': 'E', '⑥': 'F', '⑦': 'G', '⑧': 'H',
        '⑨': 'I', '⑩': 'J'
    }
    
    # 字母到圆圈数字的映射
    LETTER_TO_CIRCLE = {v: k for k, v in CIRCLE_TO_LETTER.items()}
    
    # 中文数字到阿拉伯数字的映射
    CHINESE_TO_ARABIC = {
        '一': '1', '二': '2', '三': '3', '四': '4', '五': '5',
        '六': '6', '七': '7', '八': '8', '九': '9', '十': '10',
        '十一': '11', '十二': '12', '十三': '13', '十四': '14', '十五': '15',
        '二十': '20', '三十': '30', '四十': '40', '五十': '50',
        '百': '100'
    }
    
    def recognize_questions(self, text: str) -> List[Tuple[str, str]]:
        """
        从文本中识别所有题目，分割文本为题目块
        
        Args:
            text: 包含题目的文本
            
        Returns:
            List[Tuple[str, str]]: 题目列表，每个元素为(题目编号, 题目文本块)
        """
        if not text or not text.strip():
            return []
        
        # 先提取答案区域的答案映射
        answer_map = self._extract_answer_section(text)
        
        # 找到所有题目边界
        boundaries = self._find_question_boundaries(text)
        
        if not boundaries:
            return []
        
        # 根据边界分割文本
        questions = []
        for i, (number, start_pos) in enumerate(boundaries):
            # 确定结束位置
            if i + 1 < len(boundaries):
                end_pos = boundaries[i + 1][1]
            else:
                end_pos = len(text)
            
            # 提取题目文本块
            question_text = text[start_pos:end_pos].strip()
            
            # 如果题目块中没有答案，但答案映射中有，则附加答案信息
            if number in answer_map and '【正确答案】' not in question_text and '【答案】' not in question_text:
                answer_info = answer_map[number]
                question_text = question_text + "\n" + answer_info
            
            questions.append((number, question_text))
        
        return questions
    
    def _extract_answer_section(self, text: str) -> dict:
        """
        从文本的答案区域提取答案映射
        
        很多PDF的答案在文档末尾单独列出，格式如：
        1. 【正确答案】 A
        【答案解析】...
        2. 【正确答案】 B
        ...
        
        Args:
            text: 完整文本
            
        Returns:
            dict: 题目编号到答案信息的映射
        """
        answer_map = {}
        
        # 匹配答案区域的模式：数字. 【正确答案】 答案字母
        # 支持格式：1. 【正确答案】 A 或 1.【正确答案】A
        pattern = r'(\d+)\s*[.、．]\s*【(?:正确答案|答案)】\s*([A-Za-z]+)'
        
        # 找到所有答案条目的位置
        matches = list(re.finditer(pattern, text, re.MULTILINE))
        
        for i, match in enumerate(matches):
            number = match.group(1)
            answer = match.group(2).upper()
            
            # 获取完整的答案和解析块
            start_pos = match.start()
            
            # 找到下一个题目答案的位置或文本结束
            if i + 1 < len(matches):
                end_pos = matches[i + 1].start()
            else:
                end_pos = len(text)
            
            answer_block = text[start_pos:end_pos].strip()
            # 移除题目编号前缀，只保留答案和解析
            answer_block = re.sub(r'^\d+\s*[.、．]\s*', '', answer_block)
            
            # 清理末尾多余的空白
            answer_block = answer_block.rstrip()
            
            answer_map[number] = answer_block
        
        return answer_map
    
    def _find_question_boundaries(self, text: str) -> List[Tuple[str, int]]:
        """
        找到所有题目的边界位置（改进版 - 避免误识别）
        
        Args:
            text: 文本内容
            
        Returns:
            List[Tuple[str, int]]: 边界列表，每个元素为(题目编号, 起始位置)
        """
        boundaries = []
        
        for pattern in self.QUESTION_NUMBER_PATTERNS:
            for match in re.finditer(pattern, text, re.MULTILINE | re.DOTALL):
                number = match.group(1)
                # 转换中文数字为阿拉伯数字
                number = self._convert_chinese_number(number)
                start_pos = match.start()
                
                # 排除在【解析】【答案】等标记内的数字
                before_text = text[max(0, start_pos-20):start_pos]
                # 检查是否在中括号标记内
                is_in_marker = '【' in before_text and '】' not in before_text[before_text.rfind('【'):]
                
                if not is_in_marker:
                    boundaries.append((number, start_pos))
        
        # 按位置排序
        boundaries.sort(key=lambda x: x[1])
        
        # 去除重复的边界
        unique_boundaries = []
        seen_numbers = set()
        last_pos = -100  # 使用更小的初始值确保第一个位置能被添加
        
        for number, pos in boundaries:
            # 位置间隔要足够大（至少20字符）
            if pos >= last_pos + 20:
                # 避免重复的题目编号
                if number not in seen_numbers:
                    unique_boundaries.append((number, pos))
                    seen_numbers.add(number)
                    last_pos = pos
        
        return unique_boundaries

    def _convert_chinese_number(self, number: str) -> str:
        """
        将中文数字转换为阿拉伯数字
        
        Args:
            number: 可能是中文数字的字符串
            
        Returns:
            str: 转换后的数字字符串
        """
        if number in self.CHINESE_TO_ARABIC:
            return self.CHINESE_TO_ARABIC[number]
        
        # 处理复合中文数字（如"二十一"）
        if re.match(r'^[一二三四五六七八九十百]+$', number):
            try:
                return str(self._parse_chinese_number(number))
            except:
                pass
        
        return number
    
    def _parse_chinese_number(self, chinese: str) -> int:
        """
        解析中文数字为整数
        
        Args:
            chinese: 中文数字字符串
            
        Returns:
            int: 对应的整数
        """
        result = 0
        temp = 0
        
        chinese_digits = {
            '零': 0, '一': 1, '二': 2, '三': 3, '四': 4,
            '五': 5, '六': 6, '七': 7, '八': 8, '九': 9
        }
        chinese_units = {'十': 10, '百': 100}
        
        for char in chinese:
            if char in chinese_digits:
                temp = chinese_digits[char]
            elif char in chinese_units:
                if temp == 0:
                    temp = 1
                result += temp * chinese_units[char]
                temp = 0
        
        result += temp
        return result if result > 0 else 1

    def extract_options(self, text: str) -> List[Option]:
        """
        从文本中提取选项列表
        
        Args:
            text: 包含选项的文本
            
        Returns:
            List[Option]: 选项列表
        """
        if not text or not text.strip():
            return []
        
        options = []
        
        # 尝试不同的选项格式
        # 首先尝试大写字母格式
        options = self._extract_options_by_pattern(text, 'upper')
        if options:
            return options
        
        # 尝试小写字母格式
        options = self._extract_options_by_pattern(text, 'lower')
        if options:
            return options
        
        # 尝试圆圈数字格式
        options = self._extract_options_by_pattern(text, 'circle')
        if options:
            return options
        
        return []
    
    def _extract_options_by_pattern(self, text: str, pattern_type: str) -> List[Option]:
        """
        根据指定的模式类型提取选项
        
        Args:
            text: 文本内容
            pattern_type: 模式类型 ('upper', 'lower', 'circle')
            
        Returns:
            List[Option]: 选项列表
        """
        options = []
        
        # 答案标记模式 - 必须在行首（可能有空白）
        answer_marker = r'(?:^|\n)\s*(?:答案|正确答案|参考答案|【答案】|【正确答案】|【参考答案】)'
        
        if pattern_type == 'upper':
            # 大写字母选项: A. A、 A) (A) A:
            # 使用更精确的模式，选项内容延续到下一个选项或行首答案标记
            pattern = r'(?:^|\n)\s*[（\(]?([A-Z])[）\)]?\s*[.、\)）:：]?\s*(.+?)(?=(?:\n\s*[（\(]?[A-Z][）\)]?\s*[.、\)）:：]\s)|(?:^|\n)\s*(?:答案|正确答案|参考答案|【答案】|【正确答案】|【参考答案】)|$)'
            label_set = set('ABCDEFGHIJ')
        elif pattern_type == 'lower':
            # 小写字母选项: a. a、 a) (a) a:
            pattern = r'(?:^|\n)\s*[（\(]?([a-z])[）\)]?\s*[.、\)）:：]?\s*(.+?)(?=(?:\n\s*[（\(]?[a-z][）\)]?\s*[.、\)）:：]\s)|(?:^|\n)\s*(?:答案|正确答案|参考答案|【答案】|【正确答案】|【参考答案】)|$)'
            label_set = set('abcdefghij')
        elif pattern_type == 'circle':
            # 圆圈数字选项: ① ② ③ ④
            pattern = r'(?:^|\n)\s*([①②③④⑤⑥⑦⑧⑨⑩])\s*(.+?)(?=(?:\n\s*[①②③④⑤⑥⑦⑧⑨⑩])|(?:^|\n)\s*(?:答案|正确答案|参考答案|【答案】|【正确答案】|【参考答案】)|$)'
            label_set = set('①②③④⑤⑥⑦⑧⑨⑩')
        else:
            return []
        
        matches = re.findall(pattern, text, re.MULTILINE | re.DOTALL)
        
        for label, content in matches:
            if label in label_set:
                # 清理选项内容
                content = content.strip()
                # 移除末尾可能的答案标记（仅当它在行首时）
                content = re.sub(r'\n\s*(?:答案|正确答案|参考答案|【答案】|【正确答案】|【参考答案】).*$', '', content, flags=re.DOTALL)
                content = content.strip()
                
                if content:  # 只添加有内容的选项
                    # 标准化标签为大写字母
                    normalized_label = label.upper() if pattern_type in ['upper', 'lower'] else self.CIRCLE_TO_LETTER.get(label, label)
                    options.append(Option(label=normalized_label, content=content))
        
        return options
    
    def extract_answer(self, text: str, question_number: str = "") -> List[str]:
        """
        从文本中提取正确答案
        
        Args:
            text: 包含答案的文本
            question_number: 题目编号（用于在答案区域中精确匹配）
            
        Returns:
            List[str]: 正确答案列表（标准化为大写字母）
        """
        if not text or not text.strip():
            return []
        
        # 如果提供了题目编号，优先尝试精确匹配该题目的答案
        if question_number:
            # 匹配格式：题号. 【正确答案】 答案字母
            specific_pattern = rf'{question_number}\s*[.、．]\s*【(?:正确答案|答案)】\s*([A-Za-z]+)'
            match = re.search(specific_pattern, text, re.MULTILINE)
            if match:
                answers = self._parse_answer_string(match.group(1))
                if answers:
                    return answers
        
        # 尝试所有答案模式（但要避免匹配到其他题目的答案）
        # 首先检查文本中是否有多个题目的答案
        multi_answer_pattern = r'\d+\s*[.、．]\s*【(?:正确答案|答案)】'
        has_multiple_answers = len(re.findall(multi_answer_pattern, text)) > 1
        
        if has_multiple_answers and question_number:
            # 如果有多个答案且提供了题号，只提取该题号的答案
            # 已经在上面尝试过了，如果没找到就返回空
            pass
        else:
            # 尝试所有答案模式
            for pattern in self.ANSWER_PATTERNS:
                match = re.search(pattern, text, re.IGNORECASE | re.MULTILINE)
                if match:
                    answer_str = match.group(1)
                    answers = self._parse_answer_string(answer_str)
                    if answers:  # 只有找到有效答案才返回
                        return answers
        
        # 如果常规模式都没匹配到，尝试更宽松的匹配
        # 查找文本中独立的"答案"后面跟着的字母
        loose_patterns = [
            r'答\s*案\s*[：:]*\s*([A-Za-z]+)',  # 答 案：A 或 答案A
            r'(?:本题|此题|该题).*?([A-Z])\s*(?:选项|项)?',  # 本题选A
        ]
        
        for pattern in loose_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                answer_str = match.group(1)
                answers = self._parse_answer_string(answer_str)
                if answers:
                    return answers
        
        return []
    
    def extract_explanation(self, text: str, question_number: str = "") -> str:
        """
        从文本中提取题目解析
        
        Args:
            text: 包含解析的文本
            question_number: 题目编号（用于精确匹配该题目的解析）
            
        Returns:
            str: 解析内容，如果没有找到则返回空字符串
        """
        if not text or not text.strip():
            return ""
        
        # 如果提供了题目编号，优先精确匹配该题目的解析
        if question_number:
            # 匹配格式：题号. 【正确答案】 答案 【答案解析】 解析内容
            specific_pattern = rf'{question_number}\s*[.、．]\s*【(?:正确答案|答案)】\s*[A-Za-z]+\s*【答案解析】\s*([\s\S]+?)(?=\n\s*\d+\s*[.、．]\s*【|$)'
            match = re.search(specific_pattern, text, re.MULTILINE)
            if match:
                explanation = match.group(1).strip()
                explanation = self._clean_explanation(explanation)
                if explanation:
                    return explanation
        
        # 检查文本中是否有多个题目的答案解析
        multi_answer_pattern = r'\d+\s*[.、．]\s*【(?:正确答案|答案)】'
        has_multiple_answers = len(re.findall(multi_answer_pattern, text)) > 1
        
        if has_multiple_answers and question_number:
            # 如果有多个答案且提供了题号，已经在上面尝试过了
            # 如果没找到，返回空（避免返回错误的解析）
            return ""
        
        # 尝试精确匹配【答案解析】格式（单个题目的情况）
        analysis_match = re.search(r'【答案解析】\s*([\s\S]+)', text, re.MULTILINE)
        if analysis_match:
            explanation = analysis_match.group(1).strip()
            # 移除下一个题目的内容（如果有）
            next_q = re.search(r'\n\s*\d+\s*[.、．]\s*【', explanation)
            if next_q:
                explanation = explanation[:next_q.start()].strip()
            explanation = self._clean_explanation(explanation)
            if explanation:
                return explanation
        
        # 尝试【解析】格式
        for pattern in self.EXPLANATION_PATTERNS:
            match = re.search(pattern, text, re.IGNORECASE | re.MULTILINE)
            if match:
                explanation = match.group(1).strip()
                explanation = self._clean_explanation(explanation)
                if explanation:
                    return explanation
        
        return ""
    
    def _clean_explanation(self, explanation: str) -> str:
        """
        清理解析内容
        
        Args:
            explanation: 原始解析内容
            
        Returns:
            str: 清理后的解析内容
        """
        if not explanation:
            return ""
        
        # 移除多余的空白行
        explanation = re.sub(r'\n{3,}', '\n\n', explanation)
        
        # 移除末尾可能的答案标记
        explanation = re.sub(r'\n\s*【(?:正确答案|答案)】.*$', '', explanation, flags=re.DOTALL)
        
        # 移除末尾可能的下一题开头
        explanation = re.sub(r'\n\s*\d+\s*[.、．].*$', '', explanation, flags=re.DOTALL)
        
        return explanation.strip()
    
    def _parse_answer_string(self, answer_str: str) -> List[str]:
        """
        解析答案字符串为答案列表
        
        Args:
            answer_str: 答案字符串（如 "AB", "①②", "abc", "A、B、C"）
            
        Returns:
            List[str]: 标准化的答案列表（大写字母）
        """
        answers = []
        
        # 清理答案字符串，移除分隔符
        clean_str = answer_str.replace('、', '').replace(',', '').replace('，', '').replace(' ', '')
        
        for char in clean_str:
            if char.upper() in 'ABCDEFGHIJ':
                answers.append(char.upper())
            elif char in self.CIRCLE_TO_LETTER:
                answers.append(self.CIRCLE_TO_LETTER[char])
        
        # 去重并保持顺序
        seen = set()
        unique_answers = []
        for ans in answers:
            if ans not in seen:
                seen.add(ans)
                unique_answers.append(ans)
        
        return unique_answers
    
    def identify_question_type(self, question: Question, text_block: str = "") -> QuestionType:
        """
        判断题目类型（单选/多选）
        
        优先级：
        1. 根据正确答案数量判断（最可靠）
        2. 题目文本中的明确标记（如"多选题"、"单选题"）作为辅助
        
        Args:
            question: 题目对象
            text_block: 原始题目文本块（用于检测题型标记）
            
        Returns:
            QuestionType: 题目类型
        """
        # 1. 优先根据正确答案数量判断（最可靠的方式）
        if question.correct_answers:
            num_answers = len(question.correct_answers)
            if num_answers == 1:
                return QuestionType.SINGLE_CHOICE
            elif num_answers > 1:
                return QuestionType.MULTIPLE_CHOICE
        
        # 2. 如果没有答案，尝试从题目文本中检测题型标记
        # 只检测题目文本（问题部分），不检测整个文本块（可能包含其他题目的信息）
        question_text = question.question_text or ""
        
        # 多选题标记（只在题目文本中检测）
        multiple_patterns = [
            r'\(多选\)',
            r'（多选）',
            r'【多选题】',
            r'【多选】',
            r'可多选',
        ]
        for pattern in multiple_patterns:
            if re.search(pattern, question_text, re.IGNORECASE):
                return QuestionType.MULTIPLE_CHOICE
        
        # 单选题标记（只在题目文本中检测）
        single_patterns = [
            r'\(单选\)',
            r'（单选）',
            r'【单选题】',
            r'【单选】',
        ]
        for pattern in single_patterns:
            if re.search(pattern, question_text, re.IGNORECASE):
                return QuestionType.SINGLE_CHOICE
        
        return QuestionType.UNKNOWN
    
    def parse_question(self, text_block: str, number: str = "") -> Question:
        """
        解析单个题目块，整合所有解析功能
        
        Args:
            text_block: 题目文本块
            number: 题目编号（可选）
            
        Returns:
            Question: 解析后的题目对象
        """
        if not text_block or not text_block.strip():
            raise ValidationError("题目文本不能为空")
        
        # 生成唯一ID
        question_id = str(uuid.uuid4())
        
        # 提取题目编号（如果未提供）
        if not number:
            number = self._extract_question_number(text_block)
        
        # 提取问题文本（选项之前的部分）
        question_text = self._extract_question_text(text_block)
        
        # 提取选项
        options = self.extract_options(text_block)
        
        # 提取答案（传递题目编号以精确匹配）
        correct_answers = self.extract_answer(text_block, number)
        
        # 提取解析（传递题目编号以精确匹配）
        explanation = self.extract_explanation(text_block, number)
        
        # 创建题目对象
        question = Question(
            id=question_id,
            number=number,
            question_text=question_text,
            options=options,
            correct_answers=correct_answers,
            question_type=QuestionType.UNKNOWN,  # 先设置为未知
            explanation=explanation,
            images=[],
            needs_review=False,
            metadata={}
        )
        
        # 判断题目类型（传递原始文本块以检测题型标记）
        question.question_type = self.identify_question_type(question, text_block)
        
        # 验证题目结构完整性
        self._validate_question(question)
        
        return question
    
    def _extract_question_number(self, text: str) -> str:
        """
        从文本中提取题目编号
        
        Args:
            text: 题目文本
            
        Returns:
            str: 题目编号
        """
        for pattern in self.QUESTION_NUMBER_PATTERNS:
            match = re.search(pattern, text, re.MULTILINE)
            if match:
                number = match.group(1)
                return self._convert_chinese_number(number)
        
        return ""
    
    def _extract_question_text(self, text: str) -> str:
        """
        提取问题文本（选项之前的部分）
        
        Args:
            text: 完整的题目文本块
            
        Returns:
            str: 问题文本
        """
        # 找到第一个选项的位置
        option_patterns = [
            r'(?:^|\n)\s*[（\(]?[A-Z][）\)]?\s*[.、\)）:：]?',
            r'(?:^|\n)\s*[（\(]?[a-z][）\)]?\s*[.、\)）:：]?',
            r'(?:^|\n)\s*[①②③④⑤⑥⑦⑧⑨⑩]',
        ]
        
        first_option_pos = len(text)
        for pattern in option_patterns:
            match = re.search(pattern, text, re.MULTILINE)
            if match and match.start() < first_option_pos:
                first_option_pos = match.start()
        
        # 提取选项之前的文本
        question_text = text[:first_option_pos].strip()
        
        # 移除题目编号前缀
        for pattern in self.QUESTION_NUMBER_PATTERNS:
            question_text = re.sub(pattern, '', question_text, count=1).strip()
        
        return question_text
    
    def _validate_question(self, question: Question) -> None:
        """
        验证题目结构完整性，设置needs_review标志
        
        Args:
            question: 题目对象
        """
        needs_review = False
        
        # 检查是否有问题文本
        if not question.question_text or not question.question_text.strip():
            needs_review = True
        
        # 检查是否有至少两个选项
        if len(question.options) < 2:
            needs_review = True
        
        # 检查是否有正确答案
        if not question.correct_answers:
            needs_review = True
        
        # 检查题目类型是否已知
        if question.question_type == QuestionType.UNKNOWN:
            needs_review = True
        
        question.needs_review = needs_review
