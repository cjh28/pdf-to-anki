"""PDF转Anki转换器 - 主程序入口"""
import sys


def main():
    """主函数 - 启动图形界面"""
    # 检查是否有命令行参数
    if len(sys.argv) > 1 and sys.argv[1] == "--cli":
        # 命令行模式
        run_cli_mode()
    else:
        # 图形界面模式
        run_gui_mode()


def run_gui_mode():
    """运行图形界面模式"""
    try:
        from ui import MainWindow
        app = MainWindow()
        app.run()
    except ImportError as e:
        print(f"无法启动图形界面: {e}")
        print("请确保已安装tkinter")
        sys.exit(1)
    except Exception as e:
        print(f"启动失败: {e}")
        sys.exit(1)


def run_cli_mode():
    """运行命令行模式"""
    from parsers import PDFParser
    from exceptions import FileError, ParseError
    
    print("=" * 50)
    print("PDF转Anki转换器 (命令行模式)")
    print("=" * 50)
    print()
    
    parser = PDFParser()
    
    # 获取PDF文件路径
    if len(sys.argv) > 2:
        pdf_path = sys.argv[2]
    else:
        pdf_path = input("请输入PDF文件路径: ").strip()
        if pdf_path.startswith('"') and pdf_path.endswith('"'):
            pdf_path = pdf_path[1:-1]
    
    if not pdf_path:
        print("[错误] 未提供PDF文件路径")
        return
    
    print(f"\n正在处理: {pdf_path}")
    print("-" * 50)
    
    try:
        # 验证PDF文件
        print("[1/3] 验证PDF文件...")
        parser.validate_pdf(pdf_path)
        print("      ✓ 文件验证通过")
        
        # 解析PDF
        print("[2/3] 解析PDF内容...")
        pdf_doc = parser.parse_pdf(pdf_path)
        print(f"      ✓ 成功解析 {pdf_doc.page_count} 页")
        
        # 提取图片
        print("[3/3] 提取图片...")
        images = parser.extract_images(pdf_path)
        print(f"      ✓ 发现 {len(images)} 张图片")
        
        print("-" * 50)
        print("\n文本内容预览 (前500字符):")
        print("-" * 50)
        preview = pdf_doc.text_content[:500] if len(pdf_doc.text_content) > 500 else pdf_doc.text_content
        print(preview)
        if len(pdf_doc.text_content) > 500:
            print(f"\n... (共 {len(pdf_doc.text_content)} 字符)")
        
        print("\n" + "=" * 50)
        print("解析完成！")
        print("=" * 50)
        
    except FileError as e:
        print(f"\n[文件错误] {e}")
    except ParseError as e:
        print(f"\n[解析错误] {e}")
    except Exception as e:
        print(f"\n[未知错误] {e}")


if __name__ == "__main__":
    main()
