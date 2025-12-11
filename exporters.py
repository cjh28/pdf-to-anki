"""导出器模块 - CSV和APKG导出功能"""
import csv
import io
import os
import random
import hashlib
from typing import List, Tuple, Optional

import genanki

from models import Question, QuestionType, Image
from exceptions import ExportError


class CSVExporter:
    """CSV导出器 - 将题目列表转换为Anki可导入的CSV格式"""
    
    def format_question_card(self, question: Question) -> Tuple[str, str]:
        """
        格式化单个题目为卡片的正面和背面
        
        正面：题目编号 + 问题文本 + 所有选项
        背面：正确答案（多选题清晰标注所有正确选项）
        
        Args:
            question: 题目对象
            
        Returns:
            Tuple[str, str]: (正面内容, 背面内容)
            
        需求：4.2, 4.3
        """
        # 构建正面内容：题目编号 + 问题文本 + 选项
        front_parts = []
        
        # 添加题目编号和问题文本
        front_parts.append(f"{question.number}. {question.question_text}")
        
        # 添加所有选项
        for option in question.options:
            front_parts.append(f"{option.label}. {option.content}")
        
        front = "\n".join(front_parts)
        
        # 构建背面内容：正确答案
        if question.question_type == QuestionType.MULTIPLE_CHOICE:
            # 多选题：清晰标注所有正确选项
            sorted_answers = sorted(question.correct_answers)
            answer_str = "、".join(sorted_answers)
            back = f"【多选题答案】{answer_str}"
        else:
            # 单选题或未知类型
            if question.correct_answers:
                back = f"答案：{question.correct_answers[0]}"
            else:
                back = "答案：未知"
        
        return front, back
    
    def escape_csv_content(self, content: str) -> str:
        """
        转义CSV特殊字符，确保符合RFC 4180标准
        
        RFC 4180规定：
        - 如果字段包含逗号、双引号或换行符，整个字段需要用双引号包围
        - 字段内的双引号需要用两个双引号转义
        
        Args:
            content: 原始内容
            
        Returns:
            str: 转义后的内容
            
        需求：4.5
        """
        if content is None:
            return ""
        
        # 检查是否需要转义
        needs_quoting = any(char in content for char in [',', '"', '\n', '\r'])
        
        if needs_quoting:
            # 先转义双引号（双引号变成两个双引号）
            escaped = content.replace('"', '""')
            # 用双引号包围整个字段
            return f'"{escaped}"'
        
        return content

    
    def export(self, questions: List[Question], output_path: str) -> None:
        """
        导出题目为CSV文件
        
        CSV格式：
        - 第一行为头部：front,back
        - 每行一道题目，正面和背面用逗号分隔
        - 符合RFC 4180标准
        
        Args:
            questions: 题目列表
            output_path: 输出文件路径
            
        Raises:
            ExportError: 导出失败时抛出
            
        需求：4.1
        """
        if not questions:
            raise ExportError("题目列表为空，无法导出")
        
        try:
            # 确保输出目录存在
            output_dir = os.path.dirname(output_path)
            if output_dir and not os.path.exists(output_dir):
                os.makedirs(output_dir)
            
            # 使用utf-8-sig编码（带BOM），确保Excel正确识别中文
            with open(output_path, 'w', encoding='utf-8-sig', newline='') as f:
                writer = csv.writer(f, quoting=csv.QUOTE_MINIMAL)
                
                # 写入CSV头部
                writer.writerow(['front', 'back'])
                
                # 写入每道题目
                for question in questions:
                    front, back = self.format_question_card(question)
                    writer.writerow([front, back])
                    
        except IOError as e:
            raise ExportError(f"写入CSV文件失败: {e}")
        except Exception as e:
            raise ExportError(f"导出CSV时发生错误: {e}")
    
    def export_to_string(self, questions: List[Question]) -> str:
        """
        导出题目为CSV字符串（用于测试）
        
        Args:
            questions: 题目列表
            
        Returns:
            str: CSV格式的字符串
        """
        output = io.StringIO()
        writer = csv.writer(output, quoting=csv.QUOTE_MINIMAL)
        
        # 写入CSV头部
        writer.writerow(['front', 'back'])
        
        # 写入每道题目
        for question in questions:
            front, back = self.format_question_card(question)
            writer.writerow([front, back])
        
        return output.getvalue()


class APKGExporter:
    """APKG导出器 - 将题目列表转换为Anki可导入的APKG格式"""
    
    # 定义卡片模板的唯一ID（使用固定值以保持一致性）
    MODEL_ID = 1607392327  # 更新ID以强制Anki更新模板（v7）
    
    # 定义卡片模板 - v7：单选题只能选一个，解析完整显示
    CARD_MODEL = genanki.Model(
        MODEL_ID,
        'PDF题目卡片模板v7',
        fields=[
            {'name': 'Front'},
            {'name': 'Back'},
            {'name': 'Explanation'},
            {'name': 'QuestionType'},  # 新增：题目类型字段 (single/multiple)
        ],
        templates=[
            {
                'name': '题目卡片',
                'qfmt': '''
<div class="question-card">
    <div class="question-text">{{Front}}</div>
</div>
<div class="question-type-data" style="display:none;">{{QuestionType}}</div>
<script>
(function() {
    // 获取题目类型
    var typeEl = document.querySelector('.question-type-data');
    var isSingleChoice = typeEl && typeEl.textContent.trim() === 'single';
    
    // 选项点击交互
    document.querySelectorAll('.option').forEach(function(opt) {
        opt.addEventListener('click', function() {
            if (isSingleChoice) {
                // 单选题：先取消所有选中，再选中当前
                var wasSelected = this.classList.contains('selected');
                document.querySelectorAll('.option').forEach(function(o) {
                    o.classList.remove('selected');
                });
                if (!wasSelected) {
                    this.classList.add('selected');
                }
            } else {
                // 多选题：切换选中状态
                this.classList.toggle('selected');
            }
            
            // 获取当前已选择的答案
            var selectedAnswers = [];
            document.querySelectorAll('.option.selected').forEach(function(selectedOpt) {
                var selectedLabel = selectedOpt.querySelector('.option-label');
                if (selectedLabel) {
                    selectedAnswers.push(selectedLabel.textContent.replace('.', '').trim());
                }
            });
            
            // 保存到localStorage
            try {
                localStorage.setItem('userAnswer_' + window.location.href, JSON.stringify(selectedAnswers));
            } catch(e) {
                try { sessionStorage.setItem('userAnswer_' + window.location.href, JSON.stringify(selectedAnswers)); } catch(e2) {}
            }
        });
    });
    
    // 页面加载时恢复用户选择
    try {
        var savedAnswers = localStorage.getItem('userAnswer_' + window.location.href) || sessionStorage.getItem('userAnswer_' + window.location.href);
        if (savedAnswers) {
            var answers = JSON.parse(savedAnswers);
            document.querySelectorAll('.option').forEach(function(opt) {
                var label = opt.querySelector('.option-label');
                if (label && answers.includes(label.textContent.replace('.', '').trim())) {
                    opt.classList.add('selected');
                }
            });
        }
    } catch(e) {}
})();
</script>
''',
                'afmt': '''
<div class="question-card">
    <div class="question-text">{{Front}}</div>
    <hr id="answer">
    
    <!-- 答案对比区域 - 同一排显示 -->
    <div class="answer-compare-row">
        <div class="user-answer-box" id="userAnswerBox">
            <div class="answer-box-label">您的答案</div>
            <div class="answer-box-content" id="userAnswerContent">-</div>
        </div>
        <div class="result-box" id="resultBox">
            <div class="result-icon" id="resultIcon">?</div>
        </div>
        <div class="correct-answer-box">
            <div class="answer-box-label">正确答案</div>
            <div class="answer-box-content correct-answers-display">{{Back}}</div>
        </div>
    </div>
    
    {{#Explanation}}
    <div class="explanation-section">
        <div class="explanation-title">【解析】</div>
        <div class="explanation-content">{{Explanation}}</div>
    </div>
    {{/Explanation}}
</div>
<div class="question-type-data" style="display:none;">{{QuestionType}}</div>
<script>
(function() {
    // 获取正确答案
    var correctEl = document.querySelector('.correct-answers');
    if (!correctEl) return;
    
    var correctText = correctEl.textContent.replace(/[、，, ]/g, '');
    var correctArr = correctText.split('').filter(function(a) { return a.trim(); });
    
    // 从localStorage恢复用户选择
    var userAnswers = [];
    try {
        var saved = localStorage.getItem('userAnswer_' + window.location.href) || sessionStorage.getItem('userAnswer_' + window.location.href);
        if (saved) userAnswers = JSON.parse(saved);
    } catch(e) {}
    
    // 恢复选中状态并标记颜色
    var isCorrect = true;
    document.querySelectorAll('.option').forEach(function(opt) {
        var label = opt.querySelector('.option-label');
        if (label) {
            var labelText = label.textContent.replace('.', '').trim();
            var isCorrectAnswer = correctArr.includes(labelText);
            var isUserSelected = userAnswers.includes(labelText);
            
            // 用户选中的保持蓝色高亮
            if (isUserSelected) {
                opt.classList.add('selected');
            }
            
            // 正确答案标记绿色
            if (isCorrectAnswer) {
                opt.classList.add('correct');
            }
            
            // 用户选错标记红色
            if (isUserSelected && !isCorrectAnswer) {
                opt.classList.add('wrong');
                isCorrect = false;
            } else if (!isUserSelected && isCorrectAnswer) {
                isCorrect = false;
            }
        }
    });
    
    // 显示用户答案
    var userContent = document.getElementById('userAnswerContent');
    var userBox = document.getElementById('userAnswerBox');
    if (userAnswers.length > 0) {
        userContent.textContent = userAnswers.sort().join('、');
        userBox.classList.add('has-answer');
    } else {
        userContent.textContent = '未作答';
        userBox.classList.add('no-answer');
    }
    
    // 显示判断结果
    var resultIcon = document.getElementById('resultIcon');
    var resultBox = document.getElementById('resultBox');
    if (userAnswers.length > 0) {
        if (isCorrect && userAnswers.length === correctArr.length) {
            resultIcon.textContent = '✓';
            resultBox.classList.add('result-pass');
        } else {
            resultIcon.textContent = '✗';
            resultBox.classList.add('result-fail');
        }
    } else {
        resultIcon.textContent = '-';
        resultBox.classList.add('result-none');
    }
})();
</script>
''',
            },
        ],
        css='''
.question-card {
    font-family: "Microsoft YaHei", "SimHei", "PingFang SC", Arial, sans-serif;
    font-size: 16px;
    line-height: 1.8;
    padding: 15px;
    max-width: 800px;
    margin: 0 auto;
    color: #2E7D32;
}
.question-text {
    margin-bottom: 15px;
    color: #2E7D32;
}
.question-title {
    font-weight: bold;
    margin-bottom: 10px;
    color: #1B5E20;
}
.options {
    margin: 15px 0;
}
.option {
    display: block;
    padding: 10px 15px;
    margin: 8px 0;
    border: 2px solid #81C784;
    border-radius: 8px;
    cursor: pointer;
    transition: all 0.2s ease;
    background: #E8F5E9;
    color: #2E7D32;
}
.option:hover {
    border-color: #2196F3;
    background: #BBDEFB;
    color: #1565C0;
}
.option.selected {
    border-color: #1976D2 !important;
    background: #BBDEFB !important;
    color: #0D47A1 !important;
    font-weight: bold;
}
.option.correct {
    border-color: #4CAF50 !important;
    background: #C8E6C9 !important;
    color: #1B5E20 !important;
    font-weight: bold;
}
.option.wrong {
    border-color: #f44336 !important;
    background: #FFCDD2 !important;
    color: #B71C1C !important;
    font-weight: bold;
}
.option.selected.correct {
    border-color: #4CAF50 !important;
    background: #C8E6C9 !important;
}
.option.selected.wrong {
    border-color: #f44336 !important;
    background: #FFCDD2 !important;
}
.option-label {
    font-weight: bold;
    margin-right: 8px;
}

/* 答案对比区域 - 同一排显示 */
.answer-compare-row {
    display: flex;
    justify-content: center;
    align-items: center;
    gap: 20px;
    margin: 20px 0;
    flex-wrap: wrap;
}
.user-answer-box, .correct-answer-box {
    flex: 1;
    min-width: 120px;
    max-width: 200px;
    padding: 15px;
    border-radius: 10px;
    text-align: center;
}
.user-answer-box {
    background: #E3F2FD;
    border: 2px solid #2196F3;
}
.user-answer-box.has-answer {
    background: #BBDEFB;
}
.user-answer-box.no-answer {
    background: #ECEFF1;
    border-color: #90A4AE;
}
.correct-answer-box {
    background: #E8F5E9;
    border: 2px solid #4CAF50;
}
.answer-box-label {
    font-size: 12px;
    color: #666;
    margin-bottom: 8px;
}
.answer-box-content {
    font-size: 24px;
    font-weight: bold;
}
.user-answer-box .answer-box-content {
    color: #1565C0;
}
.correct-answer-box .answer-box-content {
    color: #2E7D32;
}
.correct-answers-display .correct-answers {
    font-size: 24px;
}
.correct-answers-display .answer-label {
    display: none;
}

/* 结果图标 */
.result-box {
    width: 50px;
    height: 50px;
    border-radius: 50%;
    display: flex;
    align-items: center;
    justify-content: center;
    flex-shrink: 0;
}
.result-icon {
    font-size: 28px;
    font-weight: bold;
}
.result-box.result-pass {
    background: #C8E6C9;
    border: 3px solid #4CAF50;
}
.result-box.result-pass .result-icon {
    color: #2E7D32;
}
.result-box.result-fail {
    background: #FFCDD2;
    border: 3px solid #f44336;
}
.result-box.result-fail .result-icon {
    color: #B71C1C;
}
.result-box.result-none {
    background: #ECEFF1;
    border: 3px solid #90A4AE;
}
.result-box.result-none .result-icon {
    color: #607D8B;
}

.explanation-section {
    background: #FFF8E1;
    padding: 15px 18px;
    border-radius: 8px;
    margin-top: 15px;
    border-left: 4px solid #FFC107;
    word-wrap: break-word;
    overflow-wrap: break-word;
}
.explanation-title {
    font-weight: bold;
    color: #F57C00;
    margin-bottom: 10px;
    font-size: 15px;
}
.explanation-content {
    color: #5D4037;
    line-height: 2.0;
    font-size: 15px;
    white-space: pre-wrap;
    word-break: break-word;
}
.question-image {
    max-width: 100%;
    height: auto;
    margin: 10px 0;
    border-radius: 4px;
}
hr#answer {
    border: none;
    border-top: 2px dashed #81C784;
    margin: 20px 0;
}
'''
    )
    
    def __init__(self, deck_name: str = "PDF题目"):
        """
        初始化APKG导出器
        
        Args:
            deck_name: 卡片组名称
        """
        self.deck_name = deck_name
        self.deck = None
        self.media_files = []
    
    def _generate_deck_id(self, deck_name: str) -> int:
        """
        根据卡片组名称生成唯一的deck ID
        
        Args:
            deck_name: 卡片组名称
            
        Returns:
            int: 唯一的deck ID
        """
        # 使用deck名称的hash生成一个稳定的ID
        hash_obj = hashlib.md5(deck_name.encode('utf-8'))
        # 取hash的前8个字节转换为整数
        return int(hash_obj.hexdigest()[:8], 16)
    
    def create_deck(self, deck_name: str = None) -> genanki.Deck:
        """
        创建Anki卡片组
        
        Args:
            deck_name: 卡片组名称，如果为None则使用默认名称
            
        Returns:
            genanki.Deck: 创建的卡片组
            
        需求：5.1, 5.3
        """
        if deck_name:
            self.deck_name = deck_name
        
        deck_id = self._generate_deck_id(self.deck_name)
        self.deck = genanki.Deck(deck_id, self.deck_name)
        self.media_files = []
        
        return self.deck
    
    def _format_front_html(self, question: Question) -> str:
        """
        将题目格式化为HTML（正面）- 支持交互式选项
        
        Args:
            question: 题目对象
            
        Returns:
            str: HTML格式的正面内容
        """
        html_parts = []
        
        # 题目编号和问题文本
        html_parts.append(f'<div class="question-title"><strong>{question.number}.</strong> {self._escape_html(question.question_text)}</div>')
        
        # 添加题目中的图片
        for i, img in enumerate(question.images):
            img_filename = self._get_image_filename(question.id, i, img.format)
            html_parts.append(f'<div class="question-image"><img src="{img_filename}"></div>')
        
        # 选项 - 使用可点击的样式
        html_parts.append('<div class="options">')
        for option in question.options:
            option_html = f'<div class="option" data-label="{option.label}">'
            option_html += f'<span class="option-label">{option.label}.</span> '
            option_html += f'<span class="option-content">{self._escape_html(option.content)}</span>'
            # 添加选项中的图片
            for j, img in enumerate(option.images):
                img_filename = self._get_image_filename(f"{question.id}_opt_{option.label}", j, img.format)
                option_html += f'<br><img src="{img_filename}" class="question-image">'
            option_html += '</div>'
            html_parts.append(option_html)
        html_parts.append('</div>')
        
        return '\n'.join(html_parts)
    
    def _format_back_html(self, question: Question) -> str:
        """
        将答案格式化为HTML（背面）- 包含正确答案标记
        
        Args:
            question: 题目对象
            
        Returns:
            str: HTML格式的背面内容
        """
        html_parts = []
        
        if question.question_type == QuestionType.MULTIPLE_CHOICE:
            sorted_answers = sorted(question.correct_answers)
            answer_str = "、".join(sorted_answers)
            html_parts.append(f'<div class="answer-label">【多选题】正确答案：</div>')
            html_parts.append(f'<div class="correct-answers">{answer_str}</div>')
        else:
            if question.correct_answers:
                html_parts.append(f'<div class="answer-label">正确答案：</div>')
                html_parts.append(f'<div class="correct-answers">{question.correct_answers[0]}</div>')
            else:
                html_parts.append('<div class="correct-answers">答案：未知</div>')
        
        return '\n'.join(html_parts)
    
    def _format_explanation_html(self, question: Question) -> str:
        """
        将解析格式化为HTML
        
        Args:
            question: 题目对象
            
        Returns:
            str: HTML格式的解析内容
        """
        if question.explanation:
            return self._escape_html(question.explanation)
        return ""
    
    def _escape_html(self, text: str) -> str:
        """
        转义HTML特殊字符
        
        Args:
            text: 原始文本
            
        Returns:
            str: 转义后的文本
        """
        if not text:
            return ""
        return (text
                .replace('&', '&amp;')
                .replace('<', '&lt;')
                .replace('>', '&gt;')
                .replace('"', '&quot;')
                .replace('\n', '<br>'))
    
    def _get_image_filename(self, prefix: str, index: int, format: str) -> str:
        """
        生成图片文件名
        
        Args:
            prefix: 文件名前缀
            index: 图片索引
            format: 图片格式
            
        Returns:
            str: 图片文件名
        """
        # 清理前缀中的非法字符
        safe_prefix = "".join(c if c.isalnum() or c == '_' else '_' for c in prefix)
        return f"{safe_prefix}_{index}.{format}"
    
    def _generate_note_guid(self, question: Question) -> str:
        """
        为笔记生成唯一的GUID
        
        Args:
            question: 题目对象
            
        Returns:
            str: 唯一的GUID
        """
        # 使用题目ID和内容生成稳定的GUID
        content = f"{question.id}_{question.number}_{question.question_text}"
        return hashlib.md5(content.encode('utf-8')).hexdigest()[:10]
    
    def create_note(self, question: Question) -> genanki.Note:
        """
        为单个题目创建Anki笔记（包含解析）
        
        Args:
            question: 题目对象
            
        Returns:
            genanki.Note: 创建的笔记
            
        需求：5.2, 5.3
        """
        front_html = self._format_front_html(question)
        back_html = self._format_back_html(question)
        explanation_html = self._format_explanation_html(question)
        
        # 确定题目类型：single（单选）或 multiple（多选）
        question_type = 'multiple' if question.question_type == QuestionType.MULTIPLE_CHOICE else 'single'
        
        note = genanki.Note(
            model=self.CARD_MODEL,
            fields=[front_html, back_html, explanation_html, question_type],
            guid=self._generate_note_guid(question)
        )
        
        return note
    
    def add_media(self, image: Image, filename: str) -> str:
        """
        添加媒体文件到APKG包
        
        Args:
            image: 图片对象
            filename: 文件名
            
        Returns:
            str: 媒体文件名（用于在卡片中引用）
            
        需求：6.4
        """
        # 将图片数据和文件名添加到媒体文件列表
        self.media_files.append((filename, image.data))
        return filename
    
    def _collect_media_files(self, questions: List[Question]) -> List[str]:
        """
        收集所有题目中的图片并准备媒体文件
        
        Args:
            questions: 题目列表
            
        Returns:
            List[str]: 临时媒体文件路径列表
        """
        import tempfile
        temp_files = []
        
        for question in questions:
            # 处理题目中的图片
            for i, img in enumerate(question.images):
                filename = self._get_image_filename(question.id, i, img.format)
                # 创建临时文件
                temp_path = os.path.join(tempfile.gettempdir(), filename)
                with open(temp_path, 'wb') as f:
                    f.write(img.data)
                temp_files.append(temp_path)
                self.add_media(img, filename)
            
            # 处理选项中的图片
            for option in question.options:
                for j, img in enumerate(option.images):
                    filename = self._get_image_filename(f"{question.id}_opt_{option.label}", j, img.format)
                    temp_path = os.path.join(tempfile.gettempdir(), filename)
                    with open(temp_path, 'wb') as f:
                        f.write(img.data)
                    temp_files.append(temp_path)
                    self.add_media(img, filename)
        
        return temp_files
    
    def export(self, questions: List[Question], output_path: str, deck_name: str = None) -> None:
        """
        导出题目为APKG文件
        
        Args:
            questions: 题目列表
            output_path: 输出文件路径
            deck_name: 卡片组名称（可选）
            
        Raises:
            ExportError: 导出失败时抛出
            
        需求：5.1
        """
        if not questions:
            raise ExportError("题目列表为空，无法导出")
        
        try:
            # 创建卡片组
            self.create_deck(deck_name)
            
            # 收集媒体文件
            temp_media_files = self._collect_media_files(questions)
            
            # 为每道题目创建笔记并添加到卡片组
            for question in questions:
                note = self.create_note(question)
                self.deck.add_note(note)
            
            # 确保输出目录存在
            output_dir = os.path.dirname(output_path)
            if output_dir and not os.path.exists(output_dir):
                os.makedirs(output_dir)
            
            # 创建APKG包并写入文件
            package = genanki.Package(self.deck)
            if temp_media_files:
                package.media_files = temp_media_files
            package.write_to_file(output_path)
            
            # 清理临时文件
            for temp_file in temp_media_files:
                try:
                    os.remove(temp_file)
                except OSError:
                    pass
                    
        except IOError as e:
            raise ExportError(f"写入APKG文件失败: {e}")
        except Exception as e:
            raise ExportError(f"导出APKG时发生错误: {e}")
    
    def get_media_count(self) -> int:
        """
        获取已添加的媒体文件数量
        
        Returns:
            int: 媒体文件数量
        """
        return len(self.media_files)
