"""打包脚本 - 将项目打包为exe文件"""
import subprocess
import sys
import os

def install_pyinstaller():
    """安装PyInstaller"""
    print("正在安装 PyInstaller...")
    subprocess.check_call([sys.executable, "-m", "pip", "install", "pyinstaller", "-q"])
    print("PyInstaller 安装完成")

def build_exe():
    """打包exe"""
    print("开始打包...")
    
    # PyInstaller 参数
    args = [
        sys.executable, "-m", "PyInstaller",
        "--name=PDF转Anki转换器",      # exe名称
        "--onefile",                    # 打包成单个文件
        "--windowed",                   # 无控制台窗口
        "--noconfirm",                  # 覆盖已有文件
        "--clean",                      # 清理临时文件
        "--noupx",                      # 禁用UPX压缩，避免DLL解压错误
        # 隐藏导入 - 只包含必要的
        "--hidden-import=genanki",
        "--hidden-import=pymupdf",
        "--hidden-import=fitz",
        "--hidden-import=tkinter",
        "--hidden-import=tkinter.ttk",
        "--hidden-import=tkinter.filedialog",
        "--hidden-import=tkinter.messagebox",
        "--hidden-import=tkinter.scrolledtext",
        # 排除不需要的大型库
        "--exclude-module=torch",
        "--exclude-module=torchvision",
        "--exclude-module=torchaudio",
        "--exclude-module=tensorflow",
        "--exclude-module=keras",
        "--exclude-module=scipy",
        "--exclude-module=numpy.distutils",
        "--exclude-module=pandas",
        "--exclude-module=matplotlib",
        "--exclude-module=IPython",
        "--exclude-module=jupyter",
        "--exclude-module=notebook",
        "--exclude-module=pytest",
        "--exclude-module=hypothesis",
        "--exclude-module=black",
        "--exclude-module=pylint",
        "--exclude-module=mypy",
        "--exclude-module=boto3",
        "--exclude-module=botocore",
        "--exclude-module=sqlalchemy",
        "--exclude-module=pyarrow",
        # 入口文件
        "main.py"
    ]
    
    subprocess.check_call(args)
    print()
    print("=" * 50)
    print("打包完成！")
    print("exe文件位置: dist/PDF转Anki转换器.exe")
    print("=" * 50)

if __name__ == "__main__":
    try:
        # 检查是否已安装PyInstaller
        import PyInstaller
    except ImportError:
        install_pyinstaller()
    
    build_exe()
