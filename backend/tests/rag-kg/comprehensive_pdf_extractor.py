"""
Comprehensive PDF Content Extractor

Extracts ALL content from PDFs including:
- Traditional images
- Vector graphics/drawings  
- Text (even embedded/rendered text)
- Tables and structured content
- Form fields
- Annotations
- Everything rendered as visual content using OCR
"""

import os
import io
import logging
import asyncio
import tempfile
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from dataclasses import dataclass, asdict
import json

# PDF processing libraries
try:
    import fitz  # PyMuPDF
except ImportError:
    fitz = None

try:
    import pdfplumber
except ImportError:
    pdfplumber = None

try:
    import easyocr
except ImportError:
    easyocr = None

# OpenAI and agents
from openai import AsyncOpenAI
from agents import Agent, Runner

from dotenv import load_dotenv
load_dotenv()

logger = logging.getLogger(__name__)

def get_default_content_agent(model_name: str = "gpt-4o-mini-2024-07-18"):
    """Create content analysis agent"""
    return Agent(
        name="PDF Content Analyzer",
        model=model_name,
        instructions="""You are an expert at analyzing PDF content. Describe all visible content including:
        - Text content (extract exact text)
        - Images, logos, QR codes
        - Tables and structured data
        - Forms and fields
        - Any other visual elements
        Focus on extracting readable text and describing visual elements accurately.""",
    )

@dataclass
class ContentElement:
    """Represents any content element in the PDF"""
    element_type: str  # 'text', 'image', 'drawing', 'table', 'form', 'annotation', 'ocr'
    content: str
    bbox: Optional[Tuple[float, float, float, float]]
    page_number: int
    confidence: float = 1.0
    metadata: Dict[str, Any] = None

@dataclass
class PageAnalysis:
    """Complete analysis of a PDF page"""
    page_number: int
    width: float
    height: float
    raw_elements: List[ContentElement]  # Raw extracted elements (text, images, drawings, etc.)
    
    # Separate sections for enhanced analysis
    ocr_section: Dict[str, Any] = None  # OCR results section
    ai_analysis_section: Dict[str, Any] = None  # AI analysis section
    
    def get_formatted_output(self) -> str:
        """Get formatted output with sections clearly separated"""
        output = []
        
        # Page header
        output.append(f"=== PAGE {self.page_number} ===")
        output.append(f"Dimensions: {self.width} x {self.height}")
        output.append("")
        
        # Raw content section
        output.append("--- RAW CONTENT ---")
        
        # Group elements by type
        elements_by_type = {}
        for elem in self.raw_elements:
            if elem.element_type not in elements_by_type:
                elements_by_type[elem.element_type] = []
            elements_by_type[elem.element_type].append(elem)
        
        # Display raw content by type
        for elem_type, elements in elements_by_type.items():
            if elem_type != 'ocr':  # OCR goes in separate section
                output.append(f"\n{elem_type.upper()}:")
                for elem in elements:
                    bbox_str = f" @ {elem.bbox}" if elem.bbox else ""
                    confidence_str = f" (confidence: {elem.confidence:.2f})" if elem.confidence < 1.0 else ""
                    output.append(f"  • {elem.content}{bbox_str}{confidence_str}")
        
        # OCR Section
        if self.ocr_section:
            output.append("\n--- OCR ANALYSIS SECTION ---")
            output.append("(Text extracted using Optical Character Recognition)")
            output.append("")
            
            if self.ocr_section.get('combined_text'):
                output.append("Combined OCR Text:")
                output.append(self.ocr_section['combined_text'])
                output.append("")
            
            if self.ocr_section.get('detailed_results'):
                output.append("Detailed OCR Results:")
                for result in self.ocr_section['detailed_results']:
                    bbox_str = f" @ {result.get('bbox', 'unknown')}"
                    conf_str = f" (confidence: {result.get('confidence', 0):.2f})"
                    output.append(f"  • {result.get('text', '')}{bbox_str}{conf_str}")
                output.append("")
        
        # AI Analysis Section
        if self.ai_analysis_section:
            output.append("--- AI ANALYSIS SECTION ---")
            output.append("(Comprehensive visual analysis using AI)")
            output.append("")
            
            if self.ai_analysis_section.get('description'):
                output.append("AI Visual Description:")
                output.append(self.ai_analysis_section['description'])
                output.append("")
            
            if self.ai_analysis_section.get('summary'):
                output.append("AI Summary:")
                output.append(self.ai_analysis_section['summary'])
                output.append("")
        
        output.append("=" * 50)
        output.append("")
        
        return "\n".join(output)

class ComprehensivePDFExtractor:
    """Comprehensive PDF content extractor that captures everything"""
    
    def __init__(
        self,
        enable_ocr: bool = True,
        enable_ai_analysis: bool = True,
        ocr_languages: List[str] = ['en'],
        model_name: str = "gpt-4o"
    ):
        self.enable_ocr = enable_ocr and easyocr is not None
        self.enable_ai_analysis = enable_ai_analysis
        self.ocr_languages = ocr_languages
        self.model_name = model_name
        
        # Initialize OCR reader
        if self.enable_ocr:
            try:
                self.ocr_reader = easyocr.Reader(self.ocr_languages, gpu=False)
                logger.info(f"EasyOCR initialized for languages: {self.ocr_languages}")
            except Exception as e:
                logger.warning(f"Failed to initialize EasyOCR: {e}")
                self.enable_ocr = False
                self.ocr_reader = None
        else:
            self.ocr_reader = None
            
        # Initialize AI agent
        if self.enable_ai_analysis:
            try:
                self.content_agent = get_default_content_agent(model_name)
                self.openai_client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))
                logger.info(f"AI analysis initialized with model: {model_name}")
            except Exception as e:
                logger.warning(f"Failed to initialize AI analysis: {e}")
                self.enable_ai_analysis = False
                self.content_agent = None
                self.openai_client = None
        else:
            self.content_agent = None
            self.openai_client = None
            
        self.logger = logging.getLogger(__name__)

    def extract_traditional_images(self, page, page_num: int) -> List[ContentElement]:
        """Extract traditional embedded images"""
        elements = []
        try:
            image_list = page.get_images()
            for img_index, img in enumerate(image_list):
                try:
                    # Get image bounds
                    img_bbox = None
                    try:
                        img_bbox = page.get_image_bbox(img)
                        bbox = (img_bbox.x0, img_bbox.y0, img_bbox.x1, img_bbox.y1) if img_bbox else None
                    except:
                        bbox = None
                    
                    elements.append(ContentElement(
                        element_type='image',
                        content=f"Traditional image {img_index + 1}",
                        bbox=bbox,
                        page_number=page_num,
                        metadata={'img_info': img}
                    ))
                except Exception as e:
                    self.logger.warning(f"Error processing image {img_index}: {e}")
        except Exception as e:
            self.logger.warning(f"Error extracting traditional images: {e}")
        
        return elements

    def extract_drawings_and_paths(self, page, page_num: int) -> List[ContentElement]:
        """Extract vector graphics, drawings, and path objects"""
        elements = []
        try:
            # Get all drawings/paths on the page
            drawings = page.get_drawings()
            for draw_index, drawing in enumerate(drawings):
                try:
                    # Extract drawing info
                    rect = drawing.get('rect', None)
                    bbox = (rect.x0, rect.y0, rect.x1, rect.y1) if rect else None
                    
                    # Analyze drawing content
                    content_desc = f"Vector drawing {draw_index + 1}"
                    if 'items' in drawing:
                        content_desc += f" with {len(drawing['items'])} path elements"
                    
                    elements.append(ContentElement(
                        element_type='drawing',
                        content=content_desc,
                        bbox=bbox,
                        page_number=page_num,
                        metadata={'drawing_info': drawing}
                    ))
                except Exception as e:
                    self.logger.warning(f"Error processing drawing {draw_index}: {e}")
        except Exception as e:
            self.logger.warning(f"Error extracting drawings: {e}")
            
        return elements

    def extract_text_elements(self, page, page_num: int) -> List[ContentElement]:
        """Extract all text elements with positioning"""
        elements = []
        try:
            # Method 1: Structured text extraction
            text_dict = page.get_text("dict")
            for block in text_dict.get("blocks", []):
                if "lines" in block:  # Text block
                    for line in block["lines"]:
                        for span in line["spans"]:
                            text_content = span.get("text", "").strip()
                            if text_content:
                                bbox = span.get("bbox")
                                elements.append(ContentElement(
                                    element_type='text',
                                    content=text_content,
                                    bbox=tuple(bbox) if bbox else None,
                                    page_number=page_num,
                                    metadata={
                                        'font': span.get('font'),
                                        'size': span.get('size'),
                                        'flags': span.get('flags')
                                    }
                                ))
            
            # Method 2: Block-level text if structured failed
            if not elements:
                blocks = page.get_text("blocks")
                for block in blocks:
                    if len(block) >= 5 and block[4].strip():
                        elements.append(ContentElement(
                            element_type='text',
                            content=block[4].strip(),
                            bbox=(block[0], block[1], block[2], block[3]),
                            page_number=page_num
                        ))
                        
        except Exception as e:
            self.logger.warning(f"Error extracting text: {e}")
            
        return elements

    def extract_annotations_and_forms(self, page, page_num: int) -> List[ContentElement]:
        """Extract annotations, form fields, and interactive elements"""
        elements = []
        try:
            # Get annotations
            annots = page.annots()
            for annot in annots:
                try:
                    annot_dict = annot.info
                    content = annot_dict.get('content', '') or annot_dict.get('title', '') or 'Annotation'
                    rect = annot.rect
                    bbox = (rect.x0, rect.y0, rect.x1, rect.y1)
                    
                    elements.append(ContentElement(
                        element_type='annotation',
                        content=content,
                        bbox=bbox,
                        page_number=page_num,
                        metadata={'annot_type': annot_dict.get('type')}
                    ))
                except Exception as e:
                    self.logger.warning(f"Error processing annotation: {e}")
                    
        except Exception as e:
            self.logger.warning(f"Error extracting annotations: {e}")
            
        return elements

    def extract_with_pdfplumber(self, pdf_path: str, page_num: int) -> List[ContentElement]:
        """Extract additional content using pdfplumber"""
        elements = []
        if not pdfplumber:
            return elements
            
        try:
            with pdfplumber.open(pdf_path) as pdf:
                if page_num < len(pdf.pages):
                    page = pdf.pages[page_num]
                    
                    # Extract tables
                    tables = page.find_tables()
                    for table_index, table in enumerate(tables):
                        try:
                            table_data = table.extract()
                            if table_data:
                                # Convert table to text
                                table_text = "\n".join(["\t".join([str(cell) if cell is not None else "" for cell in row]) for row in table_data if row])
                                elements.append(ContentElement(
                                    element_type='table',
                                    content=table_text,
                                    bbox=table.bbox,
                                    page_number=page_num + 1,
                                    metadata={'table_index': table_index}
                                ))
                        except Exception as e:
                            self.logger.warning(f"Error extracting table {table_index}: {e}")
                    
                    # Extract characters for detailed analysis
                    chars = page.chars
                    if chars and not any(elem.element_type == 'text' for elem in elements):
                        # If no text found by other methods, use character-level extraction
                        char_text = "".join([char.get('text', '') for char in chars])
                        if char_text.strip():
                            elements.append(ContentElement(
                                element_type='text',
                                content=char_text.strip(),
                                bbox=None,
                                page_number=page_num + 1,
                                metadata={'source': 'pdfplumber_chars'}
                            ))
                    
        except Exception as e:
            self.logger.warning(f"Error with pdfplumber extraction: {e}")
            
        return elements

    def extract_with_ocr(self, page, page_num: int) -> List[ContentElement]:
        """Extract text using OCR from rendered page"""
        elements = []
        if not self.enable_ocr or not self.ocr_reader:
            return elements
            
        try:
            # Render page as image
            mat = fitz.Matrix(2.0, 2.0)  # High resolution
            pix = page.get_pixmap(matrix=mat)  # type: ignore
            img_data = pix.tobytes("png")
            
            # Perform OCR
            with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp_file:
                tmp_file.write(img_data)
                tmp_file_path = tmp_file.name
            
            try:
                # EasyOCR returns list of (bbox, text, confidence)
                ocr_results = self.ocr_reader.readtext(tmp_file_path)
                
                for bbox, text, confidence in ocr_results:
                    if text.strip() and confidence > 0.3:  # Filter low-confidence results
                        # Convert bbox coordinates back to PDF coordinates
                        # bbox is [[x1,y1], [x2,y2], [x3,y3], [x4,y4]]
                        if len(bbox) >= 2:
                            x1, y1 = bbox[0]
                            x2, y2 = bbox[2] if len(bbox) > 2 else bbox[1]
                            # Scale back from high-res image to PDF coordinates
                            pdf_bbox = (x1/2.0, y1/2.0, x2/2.0, y2/2.0)
                        else:
                            pdf_bbox = None
                            
                        elements.append(ContentElement(
                            element_type='ocr',
                            content=text.strip(),
                            bbox=pdf_bbox,
                            page_number=page_num,
                            confidence=confidence,
                            metadata={'ocr_bbox': bbox}
                        ))
                        
            finally:
                # Cleanup temp file
                try:
                    os.unlink(tmp_file_path)
                except:
                    pass
                    
        except Exception as e:
            self.logger.warning(f"Error with OCR extraction: {e}")
            
        return elements

    async def analyze_with_ai(self, page, page_num: int, all_elements: List[ContentElement]) -> str:
        """Analyze page with AI to get comprehensive description"""
        if not self.enable_ai_analysis or not self.content_agent:
            return ""
            
        try:
            # Render page as image for AI analysis
            mat = fitz.Matrix(1.5, 1.5)  # Good resolution for AI
            pix = page.get_pixmap(matrix=mat)  # type: ignore
            img_data = pix.tobytes("png")
            
            # Create context from extracted elements
            context = f"Page {page_num} content analysis:\n"
            context += f"Extracted {len(all_elements)} elements:\n"
            
            for elem in all_elements[:10]:  # Limit context size
                context += f"- {elem.element_type}: {elem.content[:100]}...\n"
            
            context += "\nPlease analyze this page image and provide a comprehensive description of all visible content."
            
            # Upload image and analyze
            with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp_file:
                tmp_file.write(img_data)
                tmp_file_path = tmp_file.name
            
            try:
                # Upload to OpenAI
                with open(tmp_file_path, 'rb') as f:
                    file_response = await self.openai_client.files.create(
                        file=f,
                        purpose="vision"
                    )
                
                # Analyze with agent
                result = await asyncio.wait_for(
                    Runner.run(
                        self.content_agent,
                        [
                            {
                                "role": "user",
                                "content": [
                                    {"type": "input_image", "file_id": file_response.id}
                                ]
                            }
                        ],
                    ),
                    timeout=120.0
                )
                
                # Cleanup OpenAI file
                try:
                    await self.openai_client.files.delete(file_response.id)
                except:
                    pass
                    
                return result.final_output or ""
                
            finally:
                try:
                    os.unlink(tmp_file_path)
                except:
                    pass
                    
        except Exception as e:
            self.logger.warning(f"Error with AI analysis: {e}")
            return ""

    async def analyze_page(self, page, page_num: int, pdf_path: str) -> PageAnalysis:
        """Comprehensive analysis of a single page"""
        self.logger.info(f"Analyzing page {page_num}...")
        
        # Extract raw content elements (excluding OCR - will be done separately)
        raw_elements = []
        raw_elements.extend(self.extract_traditional_images(page, page_num))
        raw_elements.extend(self.extract_drawings_and_paths(page, page_num))
        raw_elements.extend(self.extract_text_elements(page, page_num))
        raw_elements.extend(self.extract_annotations_and_forms(page, page_num))
        raw_elements.extend(self.extract_with_pdfplumber(pdf_path, page_num - 1))  # pdfplumber is 0-indexed
        
        # STEP 1: OCR Analysis (done first as requested)
        self.logger.info(f"Page {page_num}: Running OCR analysis...")
        ocr_elements = self.extract_with_ocr(page, page_num)
        
        # Build OCR section
        ocr_section = None
        if ocr_elements:
            combined_ocr_text = " ".join([elem.content for elem in ocr_elements])
            detailed_ocr_results = []
            for elem in ocr_elements:
                detailed_ocr_results.append({
                    'text': elem.content,
                    'bbox': elem.bbox,
                    'confidence': elem.confidence,
                    'metadata': elem.metadata
                })
            
            ocr_section = {
                'combined_text': combined_ocr_text,
                'detailed_results': detailed_ocr_results,
                'total_elements': len(ocr_elements)
            }
            self.logger.info(f"Page {page_num}: OCR found {len(ocr_elements)} text elements")
        
        # STEP 2: AI Analysis (done after OCR)
        self.logger.info(f"Page {page_num}: Running AI visual analysis...")
        ai_description = await self.analyze_with_ai(page, page_num, raw_elements + ocr_elements)
        
        # Build AI analysis section
        ai_analysis_section = None
        if ai_description:
            ai_analysis_section = {
                'description': ai_description,
                'summary': f"AI analyzed page with {len(raw_elements)} raw elements and {len(ocr_elements)} OCR elements",
                'analysis_type': 'visual_ai_analysis'
            }
            self.logger.info(f"Page {page_num}: AI analysis completed ({len(ai_description)} chars)")
        
        self.logger.info(f"Page {page_num}: Analysis complete - {len(raw_elements)} raw elements, {len(ocr_elements)} OCR elements")
        
        return PageAnalysis(
            page_number=page_num,
            width=page.rect.width,
            height=page.rect.height,
            raw_elements=raw_elements,
            ocr_section=ocr_section,
            ai_analysis_section=ai_analysis_section
        )

    async def extract_comprehensive(self, pdf_path: str) -> List[PageAnalysis]:
        """Extract all content from PDF comprehensively"""
        if not fitz:
            raise ImportError("PyMuPDF is required")
            
        self.logger.info(f"Starting comprehensive extraction of: {pdf_path}")
        
        doc = None
        try:
            doc = fitz.Document(pdf_path)
            page_analyses = []
            
            for page_num in range(doc.page_count):
                page = doc[page_num]
                analysis = await self.analyze_page(page, page_num + 1, pdf_path)
                page_analyses.append(analysis)
                
                # Small delay to avoid overwhelming APIs
                await asyncio.sleep(0.5)
                
            return page_analyses
            
        finally:
            if doc:
                doc.close()

    def export_analysis(self, analyses: List[PageAnalysis], output_path: str):
        """Export comprehensive analysis to JSON"""
        def convert_for_json(obj):
            if hasattr(obj, '__dict__') and hasattr(obj.__class__, '__dataclass_fields__'):
                return asdict(obj)
            elif hasattr(obj, '__dict__'):
                return obj.__dict__
            return str(obj)
            
        try:
            analysis_data = []
            for analysis in analyses:
                analysis_dict = asdict(analysis)
                analysis_data.append(analysis_dict)
        except Exception as e:
            # Fallback to manual conversion
            analysis_data = []
            for analysis in analyses:
                analysis_dict = {
                    'page_number': analysis.page_number,
                    'width': analysis.width,
                    'height': analysis.height,
                    'raw_elements': [asdict(elem) for elem in analysis.raw_elements],
                    'ocr_section': analysis.ocr_section,
                    'ai_analysis_section': analysis.ai_analysis_section
                }
                analysis_data.append(analysis_dict)
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(analysis_data, f, indent=2, ensure_ascii=False, default=convert_for_json)
    
    def export_formatted_text(self, analyses: List[PageAnalysis], output_path: str):
        """Export formatted text output with clear sections"""
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write("COMPREHENSIVE PDF ANALYSIS REPORT\n")
            f.write("=" * 60 + "\n\n")
            
            for analysis in analyses:
                f.write(analysis.get_formatted_output())
                f.write("\n")
            
            f.write("\nANALYSIS COMPLETE\n")
            f.write("=" * 60 + "\n")

# Test function
async def test_comprehensive_extractor():
    """Test the comprehensive PDF extractor"""
    pdf_path = Path(__file__).parent.parent.parent / "test_docs" / "abhilasha_6_april_ticket.pdf"
    
    if not pdf_path.exists():
        print(f"❌ Test PDF not found: {pdf_path}")
        return
    
    print(f"🔍 Testing Comprehensive PDF Extractor")
    print(f"📄 File: {pdf_path.name}")
    print("=" * 60)
    
    extractor = ComprehensivePDFExtractor(
        enable_ocr=True,
        enable_ai_analysis=False,
        ocr_languages=['en']
    )
    
    try:
        analyses = await extractor.extract_comprehensive(str(pdf_path))
        
        print(f"\n✅ COMPREHENSIVE ANALYSIS RESULTS")
        print(f"Total pages analyzed: {len(analyses)}")
        
        total_elements = 0
        for analysis in analyses:
            elements_by_type = {}
            for elem in analysis.raw_elements:
                elements_by_type[elem.element_type] = elements_by_type.get(elem.element_type, 0) + 1
            
            total_elements += len(analysis.raw_elements)
            
            print(f"\n📄 Page {analysis.page_number}:")
            print(f"   📊 Total raw elements: {len(analysis.raw_elements)}")
            print(f"   🔍 By type: {elements_by_type}")
            
            # OCR section info
            if analysis.ocr_section:
                ocr_text_len = len(analysis.ocr_section.get('combined_text', ''))
                ocr_elements = analysis.ocr_section.get('total_elements', 0)
                print(f"   📝 OCR: {ocr_elements} elements, {ocr_text_len} chars total")
                if analysis.ocr_section.get('combined_text'):
                    print(f"   📖 OCR preview: {analysis.ocr_section['combined_text'][:200]}...")
            else:
                print(f"   📝 OCR: No OCR text found")
            
            # AI analysis section info
            if analysis.ai_analysis_section:
                ai_desc_len = len(analysis.ai_analysis_section.get('description', ''))
                print(f"   🤖 AI analysis: {ai_desc_len} chars")
                if analysis.ai_analysis_section.get('description'):
                    print(f"   🧠 AI preview: {analysis.ai_analysis_section['description'][:200]}...")
            else:
                print(f"   🤖 AI analysis: No AI analysis available")
            
            # Show formatted output for first page as example
            if analysis.page_number == 1:
                print(f"\n📋 FORMATTED OUTPUT EXAMPLE (Page 1):")
                print("─" * 40)
                formatted_output = analysis.get_formatted_output()
                # Show first 1000 chars of formatted output
                print(formatted_output[:1000])
                if len(formatted_output) > 1000:
                    print("... (truncated)")
                print("─" * 40)
        
        print(f"\n🎯 SUMMARY:")
        print(f"   • Total elements extracted: {total_elements}")
        print(f"   • Used multiple extraction methods")
        print(f"   • OCR for text recognition")
        print(f"   • AI for comprehensive analysis")
        
        # Export results
        current_dir = os.path.dirname(os.path.abspath(__file__))
        cache_dir = Path(current_dir) / "cache"
        # create cache directory if it doesn't exist
        cache_dir.mkdir(parents=True, exist_ok=True)
        
        json_output_path = cache_dir / f"{pdf_path.stem}_comprehensive_analysis.json"
        text_output_path = cache_dir / f"{pdf_path.stem}_comprehensive_analysis.txt"
        
        extractor.export_analysis(analyses, str(json_output_path))
        extractor.export_formatted_text(analyses, str(text_output_path))
        
        print(f"   • JSON results exported to: {json_output_path}")
        print(f"   • Formatted text exported to: {text_output_path}")
        
        return analyses
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(test_comprehensive_extractor()) 