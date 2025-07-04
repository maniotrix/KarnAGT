"""
Comprehensive PDF Document Parser

This module provides functionality to extract all elements from PDF documents including:
- Text content (with formatting and positioning)
- Images (with descriptions using OpenAI Vision)
- Tables and structured data
- Document metadata
- Page structure and layout
"""

import os
import sys
import json
import tempfile
import logging
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
import asyncio
from dataclasses import dataclass, asdict
from datetime import datetime

# PDF processing libraries
try:
    import fitz  # PyMuPDF - most comprehensive PDF library
except ImportError:
    print("Warning: PyMuPDF not found. Install with: pip install PyMuPDF")
    fitz = None

try:
    import pdfplumber  # Good for tables and text extraction
except ImportError:
    print("Warning: pdfplumber not found. Install with: pip install pdfplumber")
    pdfplumber = None

# OpenAI for image analysis
from openai import AsyncOpenAI

# Add the backend directory to the path so we can import from app
backend_dir = Path(__file__).parent.parent.parent
sys.path.insert(0, str(backend_dir))

@dataclass
class TextElement:
    """Represents a text element in the PDF"""
    content: str
    bbox: Tuple[float, float, float, float]  # x0, y0, x1, y1
    font: str
    font_size: float
    font_flags: int  # bold, italic, etc.
    page_number: int
    
@dataclass
class ImageElement:
    """Represents an image element in the PDF"""
    image_index: int
    bbox: Tuple[float, float, float, float]
    width: int
    height: int
    colorspace: str
    bpc: int  # bits per component
    page_number: int
    description: Optional[str] = None  # AI-generated description
    base64_data: Optional[str] = None

@dataclass
class TableElement:
    """Represents a table element in the PDF"""
    bbox: Tuple[float, float, float, float]
    rows: List[List[str]]
    page_number: int

@dataclass
class PageInfo:
    """Information about a PDF page"""
    page_number: int
    width: float
    height: float
    rotation: int
    text_elements: List[TextElement]
    image_elements: List[ImageElement]
    table_elements: List[TableElement]

@dataclass
class DocumentMetadata:
    """PDF document metadata"""
    title: Optional[str]
    author: Optional[str]
    subject: Optional[str]
    creator: Optional[str]
    producer: Optional[str]
    creation_date: Optional[datetime]
    modification_date: Optional[datetime]
    pages: int
    encrypted: bool

@dataclass
class DocumentAnalysis:
    """Complete document analysis result"""
    file_path: str
    metadata: DocumentMetadata
    pages: List[PageInfo]
    total_text_length: int
    total_images: int
    total_tables: int
    processing_time: float

class ComprehensivePDFParser:
    """Comprehensive PDF parser that extracts all document elements"""
    
    def __init__(self, openai_api_key: Optional[str] = None, enable_image_analysis: bool = True):
        self.openai_client = AsyncOpenAI(api_key=openai_api_key or os.getenv("OPENAI_API_KEY")) if enable_image_analysis else None
        self.enable_image_analysis = enable_image_analysis
        self.logger = logging.getLogger(__name__)
        
    async def analyze_image_with_ai(self, image_data: bytes, image_format: str = "png") -> str:
        """Analyze image content using OpenAI Vision"""
        if not self.openai_client:
            return "Image analysis disabled"
            
        try:
            # Save image temporarily
            with tempfile.NamedTemporaryFile(suffix=f".{image_format}", delete=False) as tmp_file:
                tmp_file.write(image_data)
                tmp_file_path = tmp_file.name
            
            try:
                # Upload to OpenAI
                with open(tmp_file_path, 'rb') as f:
                    file_response = await self.openai_client.files.create(
                        file=f,
                        purpose="vision"
                    )
                
                # Analyze with Vision API
                response = await self.openai_client.chat.completions.create(
                    model="gpt-4o",
                    messages=[
                        {
                            "role": "user",
                            "content": [
                                {
                                    "type": "text",
                                    "text": "Describe this image in detail, focusing on any text, charts, diagrams, or important visual elements."
                                },
                                {
                                    "type": "image_url",
                                    "image_url": {
                                        "url": f"data:image/{image_format};base64,{image_data.hex()}"
                                    }
                                }
                            ]
                        }
                    ],
                    max_tokens=300
                )
                
                # Cleanup OpenAI file
                try:
                    await self.openai_client.files.delete(file_response.id)
                except:
                    pass
                    
                return response.choices[0].message.content or "No description provided"
                
            finally:
                # Cleanup temp file
                try:
                    os.unlink(tmp_file_path)
                except:
                    pass
                    
        except Exception as e:
            self.logger.error(f"Error analyzing image: {e}")
            return f"Error analyzing image: {str(e)}"
    
    def extract_text_elements_pymupdf(self, page) -> List[TextElement]:
        """Extract text elements with positioning using PyMuPDF"""
        text_elements = []
        text_dict = page.get_text("dict")
        
        for block in text_dict["blocks"]:
            if "lines" in block:  # Text block
                for line in block["lines"]:
                    for span in line["spans"]:
                        if span["text"].strip():  # Skip empty text
                            text_elements.append(TextElement(
                                content=span["text"],
                                bbox=(span["bbox"][0], span["bbox"][1], span["bbox"][2], span["bbox"][3]),
                                font=span["font"],
                                font_size=span["size"],
                                font_flags=span["flags"],
                                page_number=page.number + 1
                            ))
        
        return text_elements
    
    async def extract_image_elements_pymupdf(self, page) -> List[ImageElement]:
        """Extract image elements using PyMuPDF"""
        image_elements = []
        image_list = page.get_images()
        
        for img_index, img in enumerate(image_list):
            try:
                # Get image data
                base_image = page.parent.extract_image(img[0])
                image_bytes = base_image["image"]
                image_ext = base_image["ext"]
                
                # Get image position (approximate)
                bbox = page.get_image_bbox(img)
                
                description = None
                if self.enable_image_analysis:
                    description = await self.analyze_image_with_ai(image_bytes, image_ext)
                
                image_elements.append(ImageElement(
                    image_index=img_index,
                    bbox=(bbox.x0, bbox.y0, bbox.x1, bbox.y1) if bbox else (0, 0, 0, 0),
                    width=base_image["width"],
                    height=base_image["height"],
                    colorspace=base_image["colorspace"],
                    bpc=base_image["bpc"],
                    page_number=page.number + 1,
                    description=description
                ))
                
            except Exception as e:
                self.logger.error(f"Error extracting image {img_index}: {e}")
                
        return image_elements
    
    def extract_tables_pdfplumber(self, pdf_path: str) -> Dict[int, List[TableElement]]:
        """Extract tables using pdfplumber"""
        if not pdfplumber:
            return {}
            
        tables_by_page = {}
        
        try:
            with pdfplumber.open(pdf_path) as pdf:
                for page_num, page in enumerate(pdf.pages):
                    tables = page.find_tables()
                    page_tables = []
                    
                    for table in tables:
                        try:
                            # Extract table data
                            table_data = table.extract()
                            if table_data:
                                page_tables.append(TableElement(
                                    bbox=table.bbox,
                                    rows=table_data,
                                    page_number=page_num + 1
                                ))
                        except Exception as e:
                            self.logger.error(f"Error extracting table on page {page_num + 1}: {e}")
                    
                    if page_tables:
                        tables_by_page[page_num + 1] = page_tables
                        
        except Exception as e:
            self.logger.error(f"Error with pdfplumber: {e}")
            
        return tables_by_page
    
    def extract_metadata_pymupdf(self, doc) -> DocumentMetadata:
        """Extract document metadata using PyMuPDF"""
        metadata = doc.metadata
        
        def parse_date(date_str):
            if not date_str:
                return None
            try:
                # Handle PDF date format: D:YYYYMMDDHHmmSSOHH'mm'
                if date_str.startswith("D:"):
                    date_str = date_str[2:14]  # Take just YYYYMMDDHHMMSS
                    return datetime.strptime(date_str, "%Y%m%d%H%M%S")
            except:
                return None
            return None
        
        return DocumentMetadata(
            title=metadata.get('title'),
            author=metadata.get('author'),
            subject=metadata.get('subject'),
            creator=metadata.get('creator'),
            producer=metadata.get('producer'),
            creation_date=parse_date(metadata.get('creationDate')),
            modification_date=parse_date(metadata.get('modDate')),
            pages=doc.page_count,
            encrypted=doc.needs_pass
        )
    
    async def parse_pdf(self, pdf_path: str) -> DocumentAnalysis:
        """Parse PDF and extract all elements"""
        start_time = datetime.now()
        
        if not fitz:
            raise ImportError("PyMuPDF is required. Install with: pip install PyMuPDF")
        
                 # Open PDF
        doc = fitz.Document(pdf_path)
        
        # Extract metadata
        metadata = self.extract_metadata_pymupdf(doc)
        
        # Extract tables using pdfplumber
        tables_by_page = self.extract_tables_pdfplumber(pdf_path)
        
        # Process each page
        pages = []
        total_text_length = 0
        total_images = 0
        total_tables = 0
        
        for page_num in range(doc.page_count):
            page = doc[page_num]
            
            # Extract text elements
            text_elements = self.extract_text_elements_pymupdf(page)
            page_text_length = sum(len(elem.content) for elem in text_elements)
            total_text_length += page_text_length
            
            # Extract image elements
            image_elements = await self.extract_image_elements_pymupdf(page)
            total_images += len(image_elements)
            
            # Get tables for this page
            page_tables = tables_by_page.get(page_num + 1, [])
            total_tables += len(page_tables)
            
            pages.append(PageInfo(
                page_number=page_num + 1,
                width=page.rect.width,
                height=page.rect.height,
                rotation=page.rotation,
                text_elements=text_elements,
                image_elements=image_elements,
                table_elements=page_tables
            ))
        
        doc.close()
        
        processing_time = (datetime.now() - start_time).total_seconds()
        
        return DocumentAnalysis(
            file_path=pdf_path,
            metadata=metadata,
            pages=pages,
            total_text_length=total_text_length,
            total_images=total_images,
            total_tables=total_tables,
            processing_time=processing_time
        )
    
    def export_analysis_to_json(self, analysis: DocumentAnalysis, output_path: str):
        """Export analysis results to JSON"""
        # Convert to dict for JSON serialization
        def convert_datetime(obj):
            if isinstance(obj, datetime):
                return obj.isoformat()
            return obj
        
        analysis_dict = asdict(analysis)
        
        # Handle datetime serialization
        def serialize_datetime(d):
            if isinstance(d, dict):
                return {k: serialize_datetime(v) for k, v in d.items()}
            elif isinstance(d, list):
                return [serialize_datetime(item) for item in d]
            elif isinstance(d, datetime):
                return d.isoformat()
            return d
        
        analysis_dict = serialize_datetime(analysis_dict)
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(analysis_dict, f, indent=2, ensure_ascii=False)
    
    def print_analysis_summary(self, analysis: DocumentAnalysis):
        """Print a summary of the analysis"""
        print(f"\n{'='*60}")
        print(f"PDF DOCUMENT ANALYSIS SUMMARY")
        print(f"{'='*60}")
        print(f"File: {analysis.file_path}")
        print(f"Processing Time: {analysis.processing_time:.2f} seconds")
        print(f"\nDocument Metadata:")
        print(f"  Title: {analysis.metadata.title or 'N/A'}")
        print(f"  Author: {analysis.metadata.author or 'N/A'}")
        print(f"  Pages: {analysis.metadata.pages}")
        print(f"  Encrypted: {analysis.metadata.encrypted}")
        print(f"  Creation Date: {analysis.metadata.creation_date or 'N/A'}")
        
        print(f"\nContent Summary:")
        print(f"  Total Text Length: {analysis.total_text_length:,} characters")
        print(f"  Total Images: {analysis.total_images}")
        print(f"  Total Tables: {analysis.total_tables}")
        
        print(f"\nPage-by-Page Breakdown:")
        for page in analysis.pages:
            text_len = sum(len(elem.content) for elem in page.text_elements)
            print(f"  Page {page.page_number}: {len(page.text_elements)} text elements ({text_len} chars), "
                  f"{len(page.image_elements)} images, {len(page.table_elements)} tables")
        
        # Show sample text from first page
        if analysis.pages and analysis.pages[0].text_elements:
            print(f"\nSample Text (First Page):")
            sample_text = " ".join([elem.content for elem in analysis.pages[0].text_elements[:10]])
            print(f"  {sample_text[:200]}{'...' if len(sample_text) > 200 else ''}")
        
        # Show image descriptions if available
        if analysis.total_images > 0:
            print(f"\nImage Analysis:")
            image_count = 0
            for page in analysis.pages:
                for img in page.image_elements:
                    if img.description and image_count < 3:  # Show first 3 images
                        print(f"  Page {page.page_number}, Image {img.image_index + 1}: {img.description[:100]}...")
                        image_count += 1

async def test_pdf_parser():
    """Test the PDF parser with the abhilasha_6_april_ticket.pdf file"""
    
    # Setup logging
    logging.basicConfig(level=logging.INFO)
    
    # Path to the test PDF
    pdf_path = Path(__file__).parent.parent.parent / "test_docs" / "abhilasha_6_april_ticket.pdf"
    
    if not pdf_path.exists():
        print(f"Error: PDF file not found at {pdf_path}")
        return
    
    print(f"Analyzing PDF: {pdf_path}")
    
    # Initialize parser
    parser = ComprehensivePDFParser(enable_image_analysis=False)
    
    try:
        # Parse the PDF
        analysis = await parser.parse_pdf(str(pdf_path))
        
        # Print summary
        parser.print_analysis_summary(analysis)
        
        # Export to JSON
        # output_path = pdf_path.parent / f"{pdf_path.stem}_analysis.json"
        # parser.export_analysis_to_json(analysis, str(output_path))
        # print(f"\nDetailed analysis exported to: {output_path}")
        
        return analysis
        
    except Exception as e:
        print(f"Error analyzing PDF: {e}")
        raise

if __name__ == "__main__":
    # Run the test
    asyncio.run(test_pdf_parser())
