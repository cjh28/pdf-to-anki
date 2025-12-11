"""PDF解析器模块"""
import os
from typing import List
try:
    import fitz  # PyMuPDF
except ImportError:
    import pymupdf as fitz

from models import PDFDocument, Image
from exceptions import FileError, ParseError


class PDFParser:
    """PDF解析器类"""
    
    MAX_FILE_SIZE = 50 * 1024 * 1024  # 50MB in bytes
    
    def validate_pdf(self, file_path: str) -> bool:
        """
        验证PDF文件是否有效
        
        Args:
            file_path: PDF文件路径
            
        Returns:
            bool: 文件是否有效
            
        Raises:
            FileError: 文件不存在、格式无效、过大或无法读取
        """
        # 检查文件是否存在
        if not os.path.exists(file_path):
            raise FileError(f"文件不存在: {file_path}")
        
        # 检查文件大小
        file_size = os.path.getsize(file_path)
        if file_size > self.MAX_FILE_SIZE:
            raise FileError(f"文件过大: {file_size} bytes (最大: {self.MAX_FILE_SIZE} bytes)")
        
        # 检查文件扩展名
        if not file_path.lower().endswith('.pdf'):
            raise FileError(f"文件格式无效: 必须是PDF文件")
        
        # 尝试打开PDF文件验证格式
        try:
            doc = fitz.open(file_path)
            doc.close()
            return True
        except Exception as e:
            raise FileError(f"无法读取PDF文件: {str(e)}")
    
    def parse_pdf(self, file_path: str) -> PDFDocument:
        """
        解析PDF文件，返回文档对象
        
        Args:
            file_path: PDF文件路径
            
        Returns:
            PDFDocument: 解析后的文档对象
            
        Raises:
            FileError: 文件验证失败
            ParseError: 解析失败
        """
        # 首先验证文件
        self.validate_pdf(file_path)
        
        try:
            doc = fitz.open(file_path)
            
            # 检查是否加密
            if doc.is_encrypted:
                doc.close()
                raise ParseError("PDF文件已加密，无法读取")
            
            # 提取所有页面的文本
            text_content = ""
            for page_num in range(len(doc)):
                text_content += self.extract_text(doc, page_num)
            
            # 获取元数据
            metadata = doc.metadata or {}
            
            pdf_document = PDFDocument(
                file_path=file_path,
                page_count=len(doc),
                text_content=text_content,
                images=[],
                metadata=metadata
            )
            
            doc.close()
            return pdf_document
            
        except ParseError:
            raise
        except Exception as e:
            raise ParseError(f"解析PDF文件失败: {str(e)}")
    
    def extract_text(self, doc: fitz.Document, page_num: int) -> str:
        """
        提取指定页面的文本
        
        Args:
            doc: PyMuPDF文档对象
            page_num: 页码（从0开始）
            
        Returns:
            str: 页面文本内容
        """
        try:
            page = doc[page_num]
            text = page.get_text()
            return text
        except Exception as e:
            raise ParseError(f"提取第{page_num + 1}页文本失败: {str(e)}")
    
    def extract_images(self, file_path: str, page_num: int = None) -> List[Image]:
        """
        提取PDF中的图片
        
        Args:
            file_path: PDF文件路径
            page_num: 页码（可选，如果为None则提取所有页面）
            
        Returns:
            List[Image]: 图片列表
        """
        images = []
        
        try:
            doc = fitz.open(file_path)
            
            # 确定要处理的页面范围
            if page_num is not None:
                page_range = [page_num]
            else:
                page_range = range(len(doc))
            
            position = 0
            for pnum in page_range:
                page = doc[pnum]
                image_list = page.get_images()
                
                for img_index, img in enumerate(image_list):
                    xref = img[0]
                    base_image = doc.extract_image(xref)
                    
                    image_data = Image(
                        data=base_image["image"],
                        format=base_image["ext"],
                        width=base_image["width"],
                        height=base_image["height"],
                        position=position
                    )
                    images.append(image_data)
                    position += 1
            
            doc.close()
            return images
            
        except Exception as e:
            raise ParseError(f"提取图片失败: {str(e)}")
