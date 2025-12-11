# PDF转Anki转换器

<p align="center">
  <img src="https://img.shields.io/badge/Python-3.8+-blue.svg" alt="Python">
  <img src="https://img.shields.io/badge/Platform-Windows-green.svg" alt="Platform">
  <img src="https://img.shields.io/badge/License-MIT-yellow.svg" alt="License">
</p>

一款将PDF题库自动转换为Anki卡片的工具，支持单选题和多选题识别、答案自动提取、交互式学习卡片生成。

## ✨ 功能特点

- 🔍 **智能识别** - 自动识别PDF中的选择题，支持单选和多选
- 📝 **答案提取** - 自动从PDF末尾答案区域提取正确答案和解析
- 🎯 **题目筛选** - 支持按序号范围选择题目（如 `1-10,15,20-25`）
- 📤 **多格式导出** - 支持CSV和APKG格式导出
- 🎨 **交互式卡片** - Anki卡片支持点击选择，自动判断对错
- 🌿 **绿色主题** - 护眼的绿色卡片主题

## 🚀 快速开始

### 方式一：直接下载exe（推荐）

1. 从 [Releases](https://github.com/yourusername/pdf-to-anki/releases) 下载最新版本
2. 解压后双击 `PDF转Anki转换器.exe` 运行

### 方式二：从源码运行

#### 环境要求
- Python 3.8+
- Windows 10/11

#### 安装步骤

```bash
# 克隆仓库
git clone https://github.com/yourusername/pdf-to-anki.git
cd pdf-to-anki

# 安装依赖
pip install -r requirements.txt

# 运行程序
python main.py
```

或者直接双击 `run.bat` 运行。

## 📖 使用说明

### 1. 加载PDF文件

1. 点击 **"选择PDF文件"** 按钮
2. 选择包含题目的PDF文件
3. 点击 **"加载并解析PDF"**

### 2. 预览和筛选题目

- 在左侧列表查看所有识别到的题目
- 使用筛选功能：全部/需审核/单选题/多选题
- 使用序号选择功能快速选择题目

#### 序号选择格式

| 格式 | 示例 | 说明 |
|------|------|------|
| 逗号分隔 | `1,6,9` 或 `1，6，9` | 选择题目1、6、9 |
| 范围格式 | `1-10` | 选择题目1到10 |
| 混合格式 | `1-10,15,20-25` | 选择题目1-10、15、20-25 |

### 3. 导出卡片

1. 选择导出格式：**CSV** 或 **APKG**
2. 选择导出范围：**全部** 或 **仅选中**
3. 点击 **"导出"** 按钮
4. 选择保存位置

### 4. 导入Anki

1. 打开Anki
2. 文件 → 导入
3. 选择导出的 `.apkg` 文件
4. 点击导入

## 🎴 Anki卡片功能

### 交互式选项
- 点击选项进行选择（蓝色高亮）
- 单选题只能选一个，多选题可选多个

### 答案对比
- 显示您的答案和正确答案
- 自动判断对错（✓ 正确 / ✗ 错误）
- 正确选项绿色标记
- 错误选项红色标记

### 解析显示
- 自动显示题目解析（如果有）

## 🔧 从源码打包

```bash
# 安装PyInstaller
pip install pyinstaller

# 运行打包脚本
python build.py
```

打包完成后，exe文件位于 `dist/PDF转Anki转换器.exe`

## 📁 项目结构

```
pdf-to-anki/
├── main.py              # 程序入口
├── ui.py                # 图形界面
├── ui_controller.py     # 界面控制器
├── parsers.py           # PDF解析器
├── recognizers.py       # 题目识别器
├── exporters.py         # 导出器（CSV/APKG）
├── question_manager.py  # 题目管理器
├── batch_processor.py   # 批量处理器
├── models.py            # 数据模型
├── exceptions.py        # 异常定义
├── build.py             # 打包脚本
├── run.bat              # 启动脚本
├── requirements.txt     # 依赖包
└── README.md            # 项目说明
```

## 📋 支持的PDF格式

程序支持以下答案格式：

- `【正确答案】 A`
- `【答案】 BCE`
- `答案：D`
- `(答案：A)`
- 答案在PDF末尾单独列出

## ❓ 常见问题

### Q: 为什么有些题目显示"需审核"？

A: 以下情况会标记为需审核：
- 没有识别到答案
- 选项少于2个
- 题目文本为空

### Q: 导出的CSV在Excel中乱码怎么办？

A: 程序已使用UTF-8 BOM编码，Excel应该能正确显示。如果仍有问题，请使用记事本打开CSV文件，另存为时选择UTF-8编码。

### Q: exe运行报错"Failed to extract MSVCP140.dll"？

A: 请安装 [Visual C++ Redistributable](https://aka.ms/vs/17/release/vc_redist.x64.exe)

## 🤝 贡献

欢迎提交 Issue 和 Pull Request！

## 📄 许可证

本项目采用 [MIT License](LICENSE) 许可证。

## 🙏 致谢

- [PyMuPDF](https://github.com/pymupdf/PyMuPDF) - PDF解析
- [genanki](https://github.com/kerrickstaley/genanki) - Anki卡片生成
