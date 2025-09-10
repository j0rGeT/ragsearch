import os
from typing import List, Dict
import aiofiles
from docx import Document
import PyPDF2
from io import BytesIO

class DocumentParser:
    """文档解析器，支持PDF、Word、TXT格式"""
    
    def __init__(self):
        self.supported_extensions = ['.pdf', '.docx', '.txt']
    
    async def parse_document(self, file_path: str, filename: str) -> Dict[str, str]:
        """
        解析文档内容
        
        Args:
            file_path: 文件路径
            filename: 文件名
            
        Returns:
            解析结果字典，包含文本内容和元数据
        """
        file_ext = os.path.splitext(filename)[1].lower()
        
        if file_ext not in self.supported_extensions:
            raise ValueError(f"不支持的文件格式: {file_ext}")
        
        try:
            if file_ext == '.pdf':
                content = await self._parse_pdf(file_path)
            elif file_ext == '.docx':
                content = await self._parse_docx(file_path)
            elif file_ext == '.txt':
                content = await self._parse_txt(file_path)
            else:
                raise ValueError(f"未实现的解析器: {file_ext}")
            
            return {
                'filename': filename,
                'content': content,
                'file_type': file_ext,
                'char_count': len(content)
            }
        
        except Exception as e:
            raise Exception(f"解析文件 {filename} 时出错: {str(e)}")
    
    async def _parse_pdf(self, file_path: str) -> str:
        """解析PDF文件"""
        content = ""
        
        async with aiofiles.open(file_path, 'rb') as file:
            pdf_bytes = await file.read()
            
        pdf_reader = PyPDF2.PdfReader(BytesIO(pdf_bytes))
        
        for page in pdf_reader.pages:
            content += page.extract_text() + "\n"
        
        return content.strip()
    
    async def _parse_docx(self, file_path: str) -> str:
        """解析Word文档"""
        doc = Document(file_path)
        content = ""
        
        for paragraph in doc.paragraphs:
            content += paragraph.text + "\n"
        
        return content.strip()
    
    async def _parse_txt(self, file_path: str) -> str:
        """解析文本文件"""
        async with aiofiles.open(file_path, 'r', encoding='utf-8') as file:
            content = await file.read()
        
        return content.strip()
    
    def split_text(self, text: str, chunk_size: int = 500, chunk_overlap: int = 50) -> List[str]:
        """
        将文本分块
        
        Args:
            text: 原始文本
            chunk_size: 块大小
            chunk_overlap: 重叠大小
            
        Returns:
            文本块列表
        """
        if len(text) <= chunk_size:
            return [text]
        
        chunks = []
        start = 0
        
        while start < len(text):
            end = start + chunk_size
            
            if end < len(text):
                # 尝试在句号、问号或感叹号处分割
                for i in range(end, start + chunk_size - 100, -1):
                    if text[i] in '.?!。？！':
                        end = i + 1
                        break
            
            chunk = text[start:end].strip()
            if chunk:
                chunks.append(chunk)
            
            start = end - chunk_overlap
            
            if start >= len(text):
                break
        
        return chunks