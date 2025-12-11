"""用户界面模块 - 使用Tkinter实现PDF转Anki转换器的图形界面"""
import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext
from typing import List, Optional, Callable
import threading
import os

from models import Question, Option, QuestionType
from ui_controller import UIController
from exceptions import PDFConverterError, FileError, ParseError, ExportError


class MainWindow:
    """主窗口类 - 实现PDF转Anki转换器的主界面"""
    
    def __init__(self):
        """初始化主窗口"""
        self.root = tk.Tk()
        self.root.title("PDF转Anki转换器")
        self.root.geometry("1000x700")
        self.root.minsize(800, 600)
        
        # 初始化UIController - 协调所有业务逻辑
        self.controller = UIController()
        
        # 设置回调函数
        self.controller.set_progress_callback(self._on_progress_update)
        self.controller.set_error_callback(self._on_error)
        
        # 存储选中的文件列表
        self.selected_files: List[str] = []
        
        # 当前选中的题目ID
        self._current_question_id: Optional[str] = None
        
        # 创建界面
        self._create_menu()
        self._create_main_layout()
        self._create_status_bar()
        
        # 绑定事件
        self._bind_events()
    
    def _on_progress_update(self, progress: float, message: str):
        """进度更新回调"""
        self.root.after(0, lambda: self.progress_var.set(progress))
        self.root.after(0, lambda: self.load_status_label.config(text=message))
    
    def _on_error(self, message: str):
        """错误回调"""
        self.root.after(0, lambda: messagebox.showerror("错误", message))
    
    def _create_menu(self):
        """创建菜单栏"""
        menubar = tk.Menu(self.root)
        self.root.config(menu=menubar)
        
        # 文件菜单
        file_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="文件", menu=file_menu)
        file_menu.add_command(label="打开PDF文件...", command=self._on_select_files)
        file_menu.add_command(label="打开多个PDF文件...", command=self._on_select_multiple_files)
        file_menu.add_separator()
        file_menu.add_command(label="导出为CSV...", command=self._on_export_csv)
        file_menu.add_command(label="导出为APKG...", command=self._on_export_apkg)
        file_menu.add_separator()
        file_menu.add_command(label="退出", command=self.root.quit)
        
        # 编辑菜单
        edit_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="编辑", menu=edit_menu)
        edit_menu.add_command(label="编辑选中题目", command=self._on_edit_question)
        edit_menu.add_command(label="删除选中题目", command=self._on_delete_question)
        
        # 帮助菜单
        help_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="帮助", menu=help_menu)
        help_menu.add_command(label="关于", command=self._show_about)

    
    def _create_main_layout(self):
        """创建主布局 - 分为三个区域：文件选择区、预览区、导出区"""
        # 创建主框架
        main_frame = ttk.Frame(self.root, padding="5")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # 使用PanedWindow实现可调整大小的分割
        paned = ttk.PanedWindow(main_frame, orient=tk.HORIZONTAL)
        paned.pack(fill=tk.BOTH, expand=True)
        
        # 左侧面板 - 文件选择区和导出区
        left_panel = ttk.Frame(paned, width=300)
        paned.add(left_panel, weight=1)
        
        # 右侧面板 - 预览区
        right_panel = ttk.Frame(paned, width=700)
        paned.add(right_panel, weight=3)
        
        # 创建各个区域
        self._create_file_selection_area(left_panel)
        self._create_export_area(left_panel)
        self._create_preview_area(right_panel)
    
    def _create_file_selection_area(self, parent):
        """创建文件选择区"""
        # 文件选择框架
        file_frame = ttk.LabelFrame(parent, text="文件选择", padding="5")
        file_frame.pack(fill=tk.X, padx=5, pady=5)
        
        # 按钮框架
        btn_frame = ttk.Frame(file_frame)
        btn_frame.pack(fill=tk.X, pady=5)
        
        # 选择文件按钮
        self.btn_select_file = ttk.Button(btn_frame, text="选择PDF文件", command=self._on_select_files)
        self.btn_select_file.pack(side=tk.LEFT, padx=2)
        
        # 选择多个文件按钮
        self.btn_select_multiple = ttk.Button(btn_frame, text="批量选择", command=self._on_select_multiple_files)
        self.btn_select_multiple.pack(side=tk.LEFT, padx=2)
        
        # 清除按钮
        self.btn_clear_files = ttk.Button(btn_frame, text="清除", command=self._on_clear_files)
        self.btn_clear_files.pack(side=tk.LEFT, padx=2)
        
        # 文件列表
        list_frame = ttk.Frame(file_frame)
        list_frame.pack(fill=tk.BOTH, expand=True, pady=5)
        
        # 文件列表框
        self.file_listbox = tk.Listbox(list_frame, height=6, selectmode=tk.EXTENDED)
        self.file_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        # 滚动条
        file_scrollbar = ttk.Scrollbar(list_frame, orient=tk.VERTICAL, command=self.file_listbox.yview)
        file_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.file_listbox.config(yscrollcommand=file_scrollbar.set)
        
        # 加载按钮
        self.btn_load = ttk.Button(file_frame, text="加载并解析PDF", command=self._on_load_pdf)
        self.btn_load.pack(fill=tk.X, pady=5)
        
        # 进度条
        self.progress_var = tk.DoubleVar()
        self.progress_bar = ttk.Progressbar(file_frame, variable=self.progress_var, maximum=100)
        self.progress_bar.pack(fill=tk.X, pady=5)
        
        # 状态标签
        self.load_status_label = ttk.Label(file_frame, text="请选择PDF文件")
        self.load_status_label.pack(fill=tk.X)

    
    def _create_export_area(self, parent):
        """创建导出区"""
        # 导出框架
        export_frame = ttk.LabelFrame(parent, text="导出选项", padding="5")
        export_frame.pack(fill=tk.X, padx=5, pady=5)
        
        # 导出格式选择
        format_frame = ttk.Frame(export_frame)
        format_frame.pack(fill=tk.X, pady=5)
        
        ttk.Label(format_frame, text="导出格式:").pack(side=tk.LEFT)
        
        self.export_format_var = tk.StringVar(value="csv")
        ttk.Radiobutton(format_frame, text="CSV", variable=self.export_format_var, value="csv").pack(side=tk.LEFT, padx=5)
        ttk.Radiobutton(format_frame, text="APKG", variable=self.export_format_var, value="apkg").pack(side=tk.LEFT, padx=5)
        
        # 导出范围选择
        scope_frame = ttk.Frame(export_frame)
        scope_frame.pack(fill=tk.X, pady=5)
        
        ttk.Label(scope_frame, text="导出范围:").pack(side=tk.LEFT)
        
        self.export_scope_var = tk.StringVar(value="all")
        ttk.Radiobutton(scope_frame, text="全部", variable=self.export_scope_var, value="all").pack(side=tk.LEFT, padx=5)
        ttk.Radiobutton(scope_frame, text="仅选中", variable=self.export_scope_var, value="selected").pack(side=tk.LEFT, padx=5)
        
        # 批量导出模式选择
        mode_frame = ttk.Frame(export_frame)
        mode_frame.pack(fill=tk.X, pady=5)
        
        ttk.Label(mode_frame, text="批量模式:").pack(side=tk.LEFT)
        
        self.batch_mode_var = tk.StringVar(value="merge")
        ttk.Radiobutton(mode_frame, text="合并", variable=self.batch_mode_var, value="merge").pack(side=tk.LEFT, padx=5)
        ttk.Radiobutton(mode_frame, text="分离", variable=self.batch_mode_var, value="separate").pack(side=tk.LEFT, padx=5)
        
        # 卡片组名称（仅APKG）
        deck_frame = ttk.Frame(export_frame)
        deck_frame.pack(fill=tk.X, pady=5)
        
        ttk.Label(deck_frame, text="卡片组名称:").pack(side=tk.LEFT)
        self.deck_name_var = tk.StringVar(value="PDF题目")
        self.deck_name_entry = ttk.Entry(deck_frame, textvariable=self.deck_name_var)
        self.deck_name_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        
        # 导出按钮
        btn_export_frame = ttk.Frame(export_frame)
        btn_export_frame.pack(fill=tk.X, pady=5)
        
        self.btn_export = ttk.Button(btn_export_frame, text="导出", command=self._on_export)
        self.btn_export.pack(fill=tk.X)
        
        # 导出进度
        self.export_progress_var = tk.DoubleVar()
        self.export_progress_bar = ttk.Progressbar(export_frame, variable=self.export_progress_var, maximum=100)
        self.export_progress_bar.pack(fill=tk.X, pady=5)
        
        # 导出状态标签
        self.export_status_label = ttk.Label(export_frame, text="")
        self.export_status_label.pack(fill=tk.X)
    
    def _create_preview_area(self, parent):
        """创建预览区"""
        # 预览框架
        preview_frame = ttk.LabelFrame(parent, text="题目预览", padding="5")
        preview_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # 上方工具栏
        toolbar = ttk.Frame(preview_frame)
        toolbar.pack(fill=tk.X, pady=5)
        
        # 筛选选项
        ttk.Label(toolbar, text="筛选:").pack(side=tk.LEFT)
        
        self.filter_var = tk.StringVar(value="all")
        ttk.Radiobutton(toolbar, text="全部", variable=self.filter_var, value="all", command=self._on_filter_change).pack(side=tk.LEFT, padx=5)
        ttk.Radiobutton(toolbar, text="需审核", variable=self.filter_var, value="review", command=self._on_filter_change).pack(side=tk.LEFT, padx=5)
        ttk.Radiobutton(toolbar, text="单选题", variable=self.filter_var, value="single", command=self._on_filter_change).pack(side=tk.LEFT, padx=5)
        ttk.Radiobutton(toolbar, text="多选题", variable=self.filter_var, value="multiple", command=self._on_filter_change).pack(side=tk.LEFT, padx=5)
        
        # 题目数量标签
        self.question_count_label = ttk.Label(toolbar, text="共 0 道题目")
        self.question_count_label.pack(side=tk.RIGHT, padx=10)
        
        # 分割面板 - 左侧题目列表，右侧题目详情
        preview_paned = ttk.PanedWindow(preview_frame, orient=tk.HORIZONTAL)
        preview_paned.pack(fill=tk.BOTH, expand=True)
        
        # 题目列表
        list_frame = ttk.Frame(preview_paned)
        preview_paned.add(list_frame, weight=1)
        
        # 题目列表框（使用Treeview）- 支持多选
        columns = ("selected", "number", "type", "status")
        self.question_tree = ttk.Treeview(list_frame, columns=columns, show="headings", selectmode="extended")
        self.question_tree.heading("selected", text="选中")
        self.question_tree.heading("number", text="编号")
        self.question_tree.heading("type", text="类型")
        self.question_tree.heading("status", text="状态")
        self.question_tree.column("selected", width=40)
        self.question_tree.column("number", width=60)
        self.question_tree.column("type", width=60)
        self.question_tree.column("status", width=60)
        self.question_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        # 列表滚动条
        tree_scrollbar = ttk.Scrollbar(list_frame, orient=tk.VERTICAL, command=self.question_tree.yview)
        tree_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.question_tree.config(yscrollcommand=tree_scrollbar.set)
        
        # 题目详情
        detail_frame = ttk.Frame(preview_paned)
        preview_paned.add(detail_frame, weight=2)
        
        # 详情文本框
        self.detail_text = scrolledtext.ScrolledText(detail_frame, wrap=tk.WORD, state=tk.DISABLED)
        self.detail_text.pack(fill=tk.BOTH, expand=True)
        
        # 编辑按钮
        btn_frame = ttk.Frame(detail_frame)
        btn_frame.pack(fill=tk.X, pady=5)
        
        self.btn_edit = ttk.Button(btn_frame, text="编辑题目", command=self._on_edit_question)
        self.btn_edit.pack(side=tk.LEFT, padx=5)
        
        self.btn_delete = ttk.Button(btn_frame, text="删除题目", command=self._on_delete_question)
        self.btn_delete.pack(side=tk.LEFT, padx=5)
        
        # 选择按钮
        select_frame = ttk.Frame(preview_frame)
        select_frame.pack(fill=tk.X, pady=5)
        
        self.btn_select_all = ttk.Button(select_frame, text="全选", command=self._on_select_all)
        self.btn_select_all.pack(side=tk.LEFT, padx=5)
        
        self.btn_deselect_all = ttk.Button(select_frame, text="取消全选", command=self._on_deselect_all)
        self.btn_deselect_all.pack(side=tk.LEFT, padx=5)
        
        self.btn_toggle_selected = ttk.Button(select_frame, text="切换选中", command=self._on_toggle_selected)
        self.btn_toggle_selected.pack(side=tk.LEFT, padx=5)
        
        # 序号选择输入框
        ttk.Label(select_frame, text="序号选择:").pack(side=tk.LEFT, padx=(15, 5))
        self.range_entry_var = tk.StringVar()
        self.range_entry = ttk.Entry(select_frame, textvariable=self.range_entry_var, width=15)
        self.range_entry.pack(side=tk.LEFT, padx=2)
        
        self.btn_select_range = ttk.Button(select_frame, text="选择", command=self._on_select_by_range)
        self.btn_select_range.pack(side=tk.LEFT, padx=2)
        
        # 提示标签
        ttk.Label(select_frame, text="(如: 1-10,15,20-25)", foreground="gray").pack(side=tk.LEFT, padx=5)
        
        # 选中数量标签
        self.selected_count_label = ttk.Label(select_frame, text="已选中: 0")
        self.selected_count_label.pack(side=tk.RIGHT, padx=10)

    
    def _create_status_bar(self):
        """创建状态栏"""
        self.status_bar = ttk.Label(self.root, text="就绪", relief=tk.SUNKEN, anchor=tk.W)
        self.status_bar.pack(side=tk.BOTTOM, fill=tk.X)
    
    def _bind_events(self):
        """绑定事件"""
        # 题目列表选择事件
        self.question_tree.bind("<<TreeviewSelect>>", self._on_question_select)
        # 双击编辑
        self.question_tree.bind("<Double-1>", lambda e: self._on_edit_question())
    
    def _update_status(self, message: str):
        """更新状态栏消息"""
        self.status_bar.config(text=message)
        self.root.update_idletasks()
    
    # ==================== 文件选择功能 ====================
    
    def _on_select_files(self):
        """选择单个PDF文件"""
        file_path = filedialog.askopenfilename(
            title="选择PDF文件",
            filetypes=[("PDF文件", "*.pdf"), ("所有文件", "*.*")]
        )
        if file_path:
            self._add_files([file_path])
    
    def _on_select_multiple_files(self):
        """选择多个PDF文件"""
        file_paths = filedialog.askopenfilenames(
            title="选择PDF文件",
            filetypes=[("PDF文件", "*.pdf"), ("所有文件", "*.*")]
        )
        if file_paths:
            self._add_files(list(file_paths))
    
    def _add_files(self, file_paths: List[str]):
        """添加文件到列表"""
        for path in file_paths:
            if path not in self.selected_files:
                self.selected_files.append(path)
                # 只显示文件名
                filename = os.path.basename(path)
                self.file_listbox.insert(tk.END, filename)
        
        self.load_status_label.config(text=f"已选择 {len(self.selected_files)} 个文件")
        self._update_status(f"已选择 {len(self.selected_files)} 个PDF文件")
    
    def _on_clear_files(self):
        """清除文件列表"""
        self.selected_files.clear()
        self.file_listbox.delete(0, tk.END)
        self.load_status_label.config(text="请选择PDF文件")
        self._update_status("文件列表已清除")
    
    # ==================== PDF加载和解析 ====================
    
    def _on_load_pdf(self):
        """加载并解析PDF文件"""
        if not self.selected_files:
            messagebox.showwarning("警告", "请先选择PDF文件")
            return
        
        # 禁用按钮
        self.btn_load.config(state=tk.DISABLED)
        self.progress_var.set(0)
        
        # 在后台线程中执行解析
        thread = threading.Thread(target=self._load_pdf_thread)
        thread.daemon = True
        thread.start()
    
    def _load_pdf_thread(self):
        """后台线程执行PDF解析 - 使用UIController协调"""
        try:
            # 清空现有题目
            self.controller.clear_questions()
            
            total_files = len(self.selected_files)
            total_questions = 0
            errors = []
            
            for i, file_path in enumerate(self.selected_files):
                # 更新进度
                progress = (i / total_files) * 100
                self.root.after(0, lambda p=progress: self.progress_var.set(p))
                self.root.after(0, lambda f=os.path.basename(file_path): self.load_status_label.config(text=f"正在解析: {f}"))
                
                # 使用UIController加载PDF
                result = self.controller.load_pdf(file_path)
                
                if result.success:
                    total_questions += result.total_questions
                
                # 收集错误
                errors.extend(result.errors)
            
            # 完成
            self.root.after(0, lambda: self.progress_var.set(100))
            self.root.after(0, lambda: self._on_load_complete(total_questions, errors))
            
        except Exception as e:
            self.root.after(0, lambda: self._on_load_error(str(e)))
    
    def _on_load_complete(self, total_questions: int, errors: List[str]):
        """加载完成回调"""
        self.btn_load.config(state=tk.NORMAL)
        self.load_status_label.config(text=f"解析完成，共 {total_questions} 道题目")
        
        # 刷新题目列表
        self._refresh_question_list()
        
        # 显示错误信息
        if errors:
            error_msg = "\n".join(errors[:10])  # 最多显示10条错误
            if len(errors) > 10:
                error_msg += f"\n... 还有 {len(errors) - 10} 条错误"
            messagebox.showwarning("解析警告", f"部分内容解析时出现问题:\n\n{error_msg}")
        
        self._update_status(f"解析完成，共提取 {total_questions} 道题目")
    
    def _on_load_error(self, error_msg: str):
        """加载错误回调"""
        self.btn_load.config(state=tk.NORMAL)
        self.load_status_label.config(text="解析失败")
        messagebox.showerror("错误", f"解析PDF时发生错误:\n{error_msg}")
        self._update_status("解析失败")

    
    # ==================== 题目预览功能 ====================
    
    def _refresh_question_list(self):
        """刷新题目列表 - 使用UIController获取题目"""
        # 清空现有列表
        for item in self.question_tree.get_children():
            self.question_tree.delete(item)
        
        # 使用UIController获取筛选后的题目
        filter_type = self.filter_var.get()
        questions = self.controller.display_questions(filter_type)
        
        # 存储题目ID映射
        self._question_id_map = {}
        
        # 添加到列表
        for question in questions:
            # 确定类型显示
            type_text = {
                QuestionType.SINGLE_CHOICE: "单选",
                QuestionType.MULTIPLE_CHOICE: "多选",
                QuestionType.UNKNOWN: "未知"
            }.get(question.question_type, "未知")
            
            # 确定状态显示
            status_text = "需审核" if question.needs_review else "正常"
            
            # 选中状态
            selected_text = "✓" if question.selected else ""
            
            # 插入到树形视图
            item_id = self.question_tree.insert("", tk.END, values=(selected_text, question.number, type_text, status_text))
            
            # 存储题目ID映射
            self._question_id_map[item_id] = question.id
            
            # 设置标签
            tags = []
            if question.needs_review:
                tags.append("needs_review")
            if question.selected:
                tags.append("selected")
            if tags:
                self.question_tree.item(item_id, tags=tuple(tags))
        
        # 设置样式
        self.question_tree.tag_configure("needs_review", background="#FFEB3B")
        self.question_tree.tag_configure("selected", foreground="#1976D2")
        
        # 更新题目数量
        total = self.controller.get_question_count()
        filtered = len(questions)
        selected = self.controller.get_selected_count()
        if filter_type == "all":
            self.question_count_label.config(text=f"共 {total} 道题目")
        else:
            self.question_count_label.config(text=f"显示 {filtered}/{total} 道题目")
        
        # 更新选中数量
        self.selected_count_label.config(text=f"已选中: {selected}")
    
    def _on_select_all(self):
        """全选所有题目"""
        self.controller.select_all_questions(True)
        self._refresh_question_list()
        self._update_status("已全选所有题目")
    
    def _on_deselect_all(self):
        """取消全选"""
        self.controller.select_all_questions(False)
        self._refresh_question_list()
        self._update_status("已取消全选")
    
    def _on_toggle_selected(self):
        """切换当前选中项的选中状态"""
        selection = self.question_tree.selection()
        if not selection:
            messagebox.showwarning("警告", "请先在列表中选择题目")
            return
        
        for item in selection:
            if hasattr(self, '_question_id_map') and item in self._question_id_map:
                question_id = self._question_id_map[item]
                question = self.controller.get_question(question_id)
                if question:
                    # 切换选中状态
                    self.controller.select_question(question_id, not question.selected)
        
        self._refresh_question_list()
        self._update_status(f"已切换 {len(selection)} 道题目的选中状态")
    
    def _on_select_by_range(self):
        """根据输入的序号范围选择题目"""
        range_str = self.range_entry_var.get().strip()
        if not range_str:
            messagebox.showwarning("警告", "请输入题目序号范围\n格式: 1-10,15,20-25")
            return
        
        # 解析序号范围
        numbers = self._parse_number_range(range_str)
        if not numbers:
            messagebox.showerror("错误", "序号格式无效\n正确格式: 1-10,15,20-25")
            return
        
        # 先取消全选
        self.controller.select_all_questions(False)
        
        # 选择指定序号的题目
        selected_count = 0
        questions = self.controller.display_questions("all")
        for question in questions:
            try:
                q_num = int(question.number)
                if q_num in numbers:
                    self.controller.select_question(question.id, True)
                    selected_count += 1
            except ValueError:
                # 如果题目编号不是数字，尝试直接匹配
                if question.number in [str(n) for n in numbers]:
                    self.controller.select_question(question.id, True)
                    selected_count += 1
        
        self._refresh_question_list()
        self._update_status(f"已选中 {selected_count} 道题目")
    
    def _parse_number_range(self, range_str: str) -> set:
        """
        解析序号范围字符串
        
        Args:
            range_str: 序号范围字符串，如 "1-10,15,20-25"
            
        Returns:
            set: 序号集合
        """
        numbers = set()
        
        # 分割逗号
        parts = range_str.replace('，', ',').split(',')
        
        for part in parts:
            part = part.strip()
            if not part:
                continue
            
            # 检查是否是范围（包含-）
            if '-' in part:
                try:
                    start, end = part.split('-', 1)
                    start = int(start.strip())
                    end = int(end.strip())
                    if start <= end:
                        numbers.update(range(start, end + 1))
                except ValueError:
                    continue
            else:
                # 单个数字
                try:
                    numbers.add(int(part))
                except ValueError:
                    continue
        
        return numbers
    
    def _on_filter_change(self):
        """筛选条件改变"""
        self._refresh_question_list()
    
    def _on_question_select(self, event):
        """题目选择事件 - 使用UIController获取题目"""
        selection = self.question_tree.selection()
        if not selection:
            return
        
        # 获取选中项的题目ID
        item = selection[0]
        if hasattr(self, '_question_id_map') and item in self._question_id_map:
            question_id = self._question_id_map[item]
            question = self.controller.get_question(question_id)
            if question:
                self._display_question_detail(question)
    
    def _display_question_detail(self, question: Question):
        """显示题目详情 - 使用UIController格式化"""
        self.detail_text.config(state=tk.NORMAL)
        self.detail_text.delete(1.0, tk.END)
        
        # 使用UIController格式化题目
        detail = self.controller.format_question_for_display(question)
        
        self.detail_text.insert(tk.END, detail)
        self.detail_text.config(state=tk.DISABLED)
        
        # 存储当前选中的题目ID
        self._current_question_id = question.id
    
    # ==================== 题目编辑功能 ====================
    
    def _on_edit_question(self):
        """编辑选中的题目 - 使用UIController协调"""
        if not self._current_question_id:
            messagebox.showwarning("警告", "请先选择一道题目")
            return
        
        question = self.controller.get_question(self._current_question_id)
        if not question:
            messagebox.showerror("错误", "找不到选中的题目")
            return
        
        # 打开编辑对话框
        dialog = QuestionEditDialog(self.root, question)
        if dialog.result:
            # 使用UIController更新题目
            try:
                self.controller.update_question(self._current_question_id, dialog.result)
                self._refresh_question_list()
                # 重新显示详情
                updated_question = self.controller.get_question(self._current_question_id)
                if updated_question:
                    self._display_question_detail(updated_question)
                self._update_status("题目已更新")
            except Exception as e:
                messagebox.showerror("错误", f"更新题目失败: {str(e)}")
    
    def _on_delete_question(self):
        """删除选中的题目 - 使用UIController协调"""
        if not self._current_question_id:
            messagebox.showwarning("警告", "请先选择一道题目")
            return
        
        if messagebox.askyesno("确认", "确定要删除选中的题目吗？"):
            if self.controller.delete_question(self._current_question_id):
                self._current_question_id = None
                self._refresh_question_list()
                self.detail_text.config(state=tk.NORMAL)
                self.detail_text.delete(1.0, tk.END)
                self.detail_text.config(state=tk.DISABLED)
                self._update_status("题目已删除")
            else:
                messagebox.showerror("错误", "删除题目失败")
    
    # ==================== 导出功能 ====================
    
    def _on_export(self):
        """导出题目 - 使用UIController协调"""
        if self.controller.get_question_count() == 0:
            messagebox.showwarning("警告", "没有可导出的题目")
            return
        
        export_format = self.export_format_var.get()
        
        if export_format == "csv":
            self._on_export_csv()
        else:
            self._on_export_apkg()
    
    def _on_export_csv(self):
        """导出为CSV - 使用UIController协调"""
        if self.controller.get_question_count() == 0:
            messagebox.showwarning("警告", "没有可导出的题目")
            return
        
        # 选择保存路径
        file_path = filedialog.asksaveasfilename(
            title="保存CSV文件",
            defaultextension=".csv",
            filetypes=[("CSV文件", "*.csv"), ("所有文件", "*.*")]
        )
        
        if not file_path:
            return
        
        try:
            self.export_status_label.config(text="正在导出...")
            self.export_progress_var.set(50)
            self.root.update_idletasks()
            
            # 使用UIController导出CSV
            selected_only = self.export_scope_var.get() == "selected"
            result = self.controller.export_to_csv(file_path, selected_only=selected_only)
            
            if result.success:
                self.export_progress_var.set(100)
                self.export_status_label.config(text="导出完成")
                messagebox.showinfo("成功", f"已成功导出 {result.question_count} 道题目到:\n{file_path}")
                self._update_status(f"CSV导出完成: {file_path}")
            else:
                self.export_status_label.config(text="导出失败")
                messagebox.showerror("导出错误", result.error_message)
            
        except ExportError as e:
            self.export_status_label.config(text="导出失败")
            messagebox.showerror("导出错误", str(e))
        except Exception as e:
            self.export_status_label.config(text="导出失败")
            messagebox.showerror("错误", f"导出时发生错误: {str(e)}")
        finally:
            self.export_progress_var.set(0)
    
    def _on_export_apkg(self):
        """导出为APKG - 使用UIController协调"""
        if self.controller.get_question_count() == 0:
            messagebox.showwarning("警告", "没有可导出的题目")
            return
        
        # 选择保存路径
        file_path = filedialog.asksaveasfilename(
            title="保存APKG文件",
            defaultextension=".apkg",
            filetypes=[("Anki卡片包", "*.apkg"), ("所有文件", "*.*")]
        )
        
        if not file_path:
            return
        
        try:
            self.export_status_label.config(text="正在导出...")
            self.export_progress_var.set(50)
            self.root.update_idletasks()
            
            deck_name = self.deck_name_var.get() or "PDF题目"
            
            # 使用UIController导出APKG
            selected_only = self.export_scope_var.get() == "selected"
            result = self.controller.export_to_apkg(file_path, deck_name, selected_only=selected_only)
            
            if result.success:
                self.export_progress_var.set(100)
                self.export_status_label.config(text="导出完成")
                messagebox.showinfo("成功", f"已成功导出 {result.question_count} 道题目到:\n{file_path}")
                self._update_status(f"APKG导出完成: {file_path}")
            else:
                self.export_status_label.config(text="导出失败")
                messagebox.showerror("导出错误", result.error_message)
            
        except ExportError as e:
            self.export_status_label.config(text="导出失败")
            messagebox.showerror("导出错误", str(e))
        except Exception as e:
            self.export_status_label.config(text="导出失败")
            messagebox.showerror("错误", f"导出时发生错误: {str(e)}")
        finally:
            self.export_progress_var.set(0)
    
    def _show_about(self):
        """显示关于对话框"""
        messagebox.showinfo(
            "关于",
            "PDF转Anki转换器\n\n"
            "版本: 1.0.0\n\n"
            "将PDF中的选择题转换为Anki可导入的格式\n"
            "支持CSV和APKG格式导出"
        )
    
    def run(self):
        """运行主窗口"""
        self.root.mainloop()



class QuestionEditDialog:
    """题目编辑对话框"""
    
    def __init__(self, parent, question: Question):
        """
        初始化编辑对话框
        
        Args:
            parent: 父窗口
            question: 要编辑的题目
        """
        self.result = None
        self.question = question
        
        # 创建对话框窗口
        self.dialog = tk.Toplevel(parent)
        self.dialog.title(f"编辑题目 - {question.number}")
        self.dialog.geometry("600x500")
        self.dialog.transient(parent)
        self.dialog.grab_set()
        
        # 创建界面
        self._create_widgets()
        
        # 填充数据
        self._populate_data()
        
        # 等待对话框关闭
        parent.wait_window(self.dialog)
    
    def _create_widgets(self):
        """创建对话框控件"""
        main_frame = ttk.Frame(self.dialog, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # 题目编号
        number_frame = ttk.Frame(main_frame)
        number_frame.pack(fill=tk.X, pady=5)
        ttk.Label(number_frame, text="题目编号:").pack(side=tk.LEFT)
        self.number_var = tk.StringVar()
        ttk.Entry(number_frame, textvariable=self.number_var, width=10).pack(side=tk.LEFT, padx=5)
        
        # 题目类型
        type_frame = ttk.Frame(main_frame)
        type_frame.pack(fill=tk.X, pady=5)
        ttk.Label(type_frame, text="题目类型:").pack(side=tk.LEFT)
        self.type_var = tk.StringVar()
        type_combo = ttk.Combobox(type_frame, textvariable=self.type_var, state="readonly", width=15)
        type_combo['values'] = ("单选题", "多选题", "未知")
        type_combo.pack(side=tk.LEFT, padx=5)
        
        # 需要审核
        self.review_var = tk.BooleanVar()
        ttk.Checkbutton(type_frame, text="需要审核", variable=self.review_var).pack(side=tk.LEFT, padx=20)
        
        # 问题文本
        ttk.Label(main_frame, text="问题文本:").pack(anchor=tk.W, pady=(10, 0))
        self.question_text = scrolledtext.ScrolledText(main_frame, height=5, wrap=tk.WORD)
        self.question_text.pack(fill=tk.X, pady=5)
        
        # 选项编辑区
        options_frame = ttk.LabelFrame(main_frame, text="选项", padding="5")
        options_frame.pack(fill=tk.BOTH, expand=True, pady=5)
        
        # 选项列表
        self.option_entries = []
        self.option_frame = ttk.Frame(options_frame)
        self.option_frame.pack(fill=tk.BOTH, expand=True)
        
        # 添加选项按钮
        btn_frame = ttk.Frame(options_frame)
        btn_frame.pack(fill=tk.X, pady=5)
        ttk.Button(btn_frame, text="添加选项", command=self._add_option).pack(side=tk.LEFT)
        
        # 正确答案
        answer_frame = ttk.Frame(main_frame)
        answer_frame.pack(fill=tk.X, pady=5)
        ttk.Label(answer_frame, text="正确答案 (多个用逗号分隔):").pack(side=tk.LEFT)
        self.answer_var = tk.StringVar()
        ttk.Entry(answer_frame, textvariable=self.answer_var, width=20).pack(side=tk.LEFT, padx=5)
        
        # 按钮
        btn_frame = ttk.Frame(main_frame)
        btn_frame.pack(fill=tk.X, pady=10)
        ttk.Button(btn_frame, text="保存", command=self._on_save).pack(side=tk.RIGHT, padx=5)
        ttk.Button(btn_frame, text="取消", command=self._on_cancel).pack(side=tk.RIGHT, padx=5)
    
    def _populate_data(self):
        """填充题目数据"""
        self.number_var.set(self.question.number)
        
        # 设置题目类型
        type_text = {
            QuestionType.SINGLE_CHOICE: "单选题",
            QuestionType.MULTIPLE_CHOICE: "多选题",
            QuestionType.UNKNOWN: "未知"
        }.get(self.question.question_type, "未知")
        self.type_var.set(type_text)
        
        self.review_var.set(self.question.needs_review)
        
        self.question_text.insert(tk.END, self.question.question_text)
        
        # 填充选项
        for option in self.question.options:
            self._add_option(option.label, option.content)
        
        # 填充答案
        self.answer_var.set(", ".join(self.question.correct_answers))
    
    def _add_option(self, label: str = "", content: str = ""):
        """添加选项输入行"""
        row_frame = ttk.Frame(self.option_frame)
        row_frame.pack(fill=tk.X, pady=2)
        
        # 选项标签
        label_var = tk.StringVar(value=label or chr(65 + len(self.option_entries)))
        label_entry = ttk.Entry(row_frame, textvariable=label_var, width=5)
        label_entry.pack(side=tk.LEFT, padx=2)
        
        ttk.Label(row_frame, text=".").pack(side=tk.LEFT)
        
        # 选项内容
        content_var = tk.StringVar(value=content)
        content_entry = ttk.Entry(row_frame, textvariable=content_var)
        content_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        
        # 删除按钮
        def remove_option():
            row_frame.destroy()
            self.option_entries.remove((label_var, content_var, row_frame))
        
        ttk.Button(row_frame, text="×", width=3, command=remove_option).pack(side=tk.RIGHT)
        
        self.option_entries.append((label_var, content_var, row_frame))
    
    def _on_save(self):
        """保存修改"""
        # 收集数据
        updates = {}
        
        # 题目编号
        number = self.number_var.get().strip()
        if number:
            updates['number'] = number
        
        # 题目类型
        type_text = self.type_var.get()
        type_map = {
            "单选题": QuestionType.SINGLE_CHOICE,
            "多选题": QuestionType.MULTIPLE_CHOICE,
            "未知": QuestionType.UNKNOWN
        }
        updates['question_type'] = type_map.get(type_text, QuestionType.UNKNOWN)
        
        # 需要审核
        updates['needs_review'] = self.review_var.get()
        
        # 问题文本
        question_text = self.question_text.get(1.0, tk.END).strip()
        if question_text:
            updates['question_text'] = question_text
        
        # 选项
        options = []
        for label_var, content_var, _ in self.option_entries:
            label = label_var.get().strip()
            content = content_var.get().strip()
            if label and content:
                options.append(Option(label=label, content=content))
        updates['options'] = options
        
        # 正确答案
        answer_str = self.answer_var.get().strip()
        if answer_str:
            answers = [a.strip().upper() for a in answer_str.replace("，", ",").split(",") if a.strip()]
            updates['correct_answers'] = answers
        else:
            updates['correct_answers'] = []
        
        self.result = updates
        self.dialog.destroy()
    
    def _on_cancel(self):
        """取消编辑"""
        self.dialog.destroy()


def main():
    """主函数"""
    app = MainWindow()
    app.run()


if __name__ == "__main__":
    main()
