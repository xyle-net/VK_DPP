import re
import argparse
import os
from docx import Document
from docx.shared import Pt, Cm, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_LINE_SPACING, WD_BREAK, WD_TAB_LEADER
from docx.enum.section import WD_SECTION
from docx.oxml.ns import qn
from docx.enum.style import WD_STYLE_TYPE
from docx.oxml import OxmlElement
from docx.oxml.shared import qn

# Import ML classifier if available
try:
    from ml_classifier import *
    ML_AVAILABLE = True
except ImportError:
    ML_AVAILABLE = False
    print("ML classifier not available, using regex-based detection only.")

# Check if Spire.Doc is available for page numbering
try:
    from spire.doc import FieldType, HorizontalAlignment, ParagraphStyle
    from spire.doc import Document as SpireDocument
    from spire.doc.common import *
    SPIRE_AVAILABLE = True
except ImportError:
    SPIRE_AVAILABLE = False
    print("Spire.Doc not available. Page numbering will not be applied.")

class GostFormatter:
    def __init__(self, use_ml=True):
        self.document = Document()
        self.setup_document_formatting()
        self.sections = []
        self.current_page = 1
        self.estimated_chars_per_page = 1800  # Approximately characters per page
        
        # Initialize ML classifier if available and requested
        self.use_ml = use_ml and ML_AVAILABLE
        self.classifier = None
        
        if self.use_ml:
            model_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'models/section_classifier.pt')
            if os.path.exists(model_path):
                try:
                    self.classifier = TextClassifier(model_path)
                    print("ML classifier loaded successfully.")
                except Exception as e:
                    print(f"Error loading ML classifier: {e}")
                    self.use_ml = False
            else:
                print(f"ML model not found at {model_path}. Using regex-based detection only.")
                self.use_ml = False
                
        # Setup list styles
        self._setup_list_styles()
        
        # Set up numbering definitions
        self.bullet_list_id = self._add_numbering_definition(
            abstractNumId=1,
            nsid="{66AF548E-3092-4FAD-93A7-1A1D7A1B2E09}",
            bullet=True
        )
        
        self.number_list_id = self._add_numbering_definition(
            abstractNumId=2,
            nsid="{2AFA7914-9D97-45B1-A387-4CDB345D2704}",
            bullet=False
        )

    def setup_document_formatting(self):
        # Set up document according to ГОСТ standards
        section = self.document.sections[0]
        section.page_height = Cm(29.7)  # A4
        section.page_width = Cm(21.0)
        section.left_margin = Cm(3)
        section.right_margin = Cm(1.5)
        section.top_margin = Cm(2)
        section.bottom_margin = Cm(2)
        
        # Set default font
        style = self.document.styles['Normal']
        font = style.font
        font.name = 'Times New Roman'
        font.size = Pt(14)
        paragraph_format = style.paragraph_format
        paragraph_format.line_spacing_rule = WD_LINE_SPACING.ONE_POINT_FIVE
        paragraph_format.space_after = Pt(0)
        paragraph_format.first_line_indent = Cm(1.25)  # Standard paragraph indent per GOST
        
        # Initialize heading styles
        self._setup_heading_styles()

    def _setup_heading_styles(self):
        """Setup heading styles according to GOST standards"""
        # Configure Heading 1 style
        style = self.document.styles['Heading 1']
        font = style.font
        font.name = 'Times New Roman'
        font.size = Pt(16)
        font.bold = True
        font.color.rgb = RGBColor(0, 0, 0)  # Set color to black
        paragraph_format = style.paragraph_format
        paragraph_format.alignment = WD_ALIGN_PARAGRAPH.CENTER
        paragraph_format.space_before = Pt(14)
        paragraph_format.space_after = Pt(14)
        paragraph_format.line_spacing_rule = WD_LINE_SPACING.ONE_POINT_FIVE
        paragraph_format.first_line_indent = Cm(0)
        
        # Configure Heading 2 style
        style = self.document.styles['Heading 2']
        font = style.font
        font.name = 'Times New Roman'
        font.size = Pt(14)
        font.bold = True
        font.color.rgb = RGBColor(0, 0, 0)  # Set color to black
        paragraph_format = style.paragraph_format
        paragraph_format.alignment = WD_ALIGN_PARAGRAPH.CENTER
        paragraph_format.space_before = Pt(14)
        paragraph_format.space_after = Pt(14)
        paragraph_format.line_spacing_rule = WD_LINE_SPACING.ONE_POINT_FIVE
        paragraph_format.first_line_indent = Cm(0)
        
        # Configure Heading 3 style
        style = self.document.styles['Heading 3']
        font = style.font
        font.name = 'Times New Roman'
        font.size = Pt(14)
        font.bold = True
        font.color.rgb = RGBColor(0, 0, 0)  # Set color to black
        paragraph_format = style.paragraph_format
        paragraph_format.alignment = WD_ALIGN_PARAGRAPH.CENTER
        paragraph_format.space_before = Pt(12)
        paragraph_format.space_after = Pt(12)
        paragraph_format.line_spacing_rule = WD_LINE_SPACING.ONE_POINT_FIVE
        paragraph_format.first_line_indent = Cm(0)

    def _setup_list_styles(self):
        """Set up list styles for the document"""
        # Numbered list style
        if 'GOST Numbered List' not in self.document.styles:
            numbered_style = self.document.styles.add_style('GOST Numbered List', WD_STYLE_TYPE.PARAGRAPH)
            numbered_style.base_style = self.document.styles['Normal']
            numbered_style.font.name = 'Times New Roman'
            numbered_style.font.size = Pt(14)
            numbered_format = numbered_style.paragraph_format
            numbered_format.line_spacing_rule = WD_LINE_SPACING.ONE_POINT_FIVE
            numbered_format.space_after = Pt(0)
            numbered_format.left_indent = Cm(1.25)
            numbered_format.first_line_indent = Cm(-0.75)
            
        # Bulleted list style
        if 'GOST Bulleted List' not in self.document.styles:
            bulleted_style = self.document.styles.add_style('GOST Bulleted List', WD_STYLE_TYPE.PARAGRAPH)
            bulleted_style.base_style = self.document.styles['Normal']
            bulleted_style.font.name = 'Times New Roman'
            bulleted_style.font.size = Pt(14)
            bulleted_format = bulleted_style.paragraph_format
            bulleted_format.line_spacing_rule = WD_LINE_SPACING.ONE_POINT_FIVE
            bulleted_format.space_after = Pt(0)
            bulleted_format.left_indent = Cm(1.25)
            bulleted_format.first_line_indent = Cm(-0.75)
            
        # Bibliography style
        if 'GOST Bibliography' not in self.document.styles:
            bib_style = self.document.styles.add_style('GOST Bibliography', WD_STYLE_TYPE.PARAGRAPH)
            bib_style.base_style = self.document.styles['Normal']
            bib_style.font.name = 'Times New Roman'
            bib_style.font.size = Pt(14)
            bib_format = bib_style.paragraph_format
            bib_format.line_spacing_rule = WD_LINE_SPACING.ONE_POINT_FIVE
            bib_format.space_after = Pt(0)
            bib_format.left_indent = Cm(1.25)
            bib_format.first_line_indent = Cm(-1.25)

    def _add_numbering_definition(self, abstractNumId, nsid, bullet=False):
        """Add a numbering definition to the document"""
        # Get the document part
        part = self.document.part
        
        # Check if we already have a numbering part
        try:
            numbering_part = part.numbering_part
        except AttributeError:
            # If not, we need to add it
            from docx.opc.constants import CONTENT_TYPE as CT
            from docx.opc.part import PartFactory
            from docx.opc.packuri import PackURI
            
            partname = PackURI('/word/numbering.xml')
            content_type = CT.WML_NUMBERING
            xml_content = '<w:numbering xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"/>'
            numbering_part = PartFactory(partname, content_type, xml_content, part.package)
            part.relate_to(numbering_part, 'http://schemas.openxmlformats.org/officeDocument/2006/relationships/numbering')
            part.numbering_part = numbering_part
        
        # Get the numbering element
        element = numbering_part.element
        
        # Check if the abstractNum with this ID already exists
        # Instead of using xpath, manually check for existing elements
        abstract_num_exists = False
        num_exists = False
        
        for child in element:
            if child.tag.endswith('abstractNum'):
                abstract_num_id_attr = '{%s}abstractNumId' % 'http://schemas.openxmlformats.org/wordprocessingml/2006/main'
                if child.get(abstract_num_id_attr) == str(abstractNumId):
                    abstract_num_exists = True
                    break
        
        for child in element:
            if child.tag.endswith('num'):
                num_id_attr = '{%s}numId' % 'http://schemas.openxmlformats.org/wordprocessingml/2006/main'
                if child.get(num_id_attr) == str(abstractNumId):
                    num_exists = True
                    break
        
        if abstract_num_exists:
            # If it exists, we don't need to recreate it
            return abstractNumId
        
        # Create a new abstractNum element
        abstractNum = OxmlElement('w:abstractNum')
        abstractNum.set(qn('w:abstractNumId'), str(abstractNumId))
        
        # Add nsid element (optional but helps with uniqueness)
        nsid_element = OxmlElement('w:nsid')
        nsid_element.set(qn('w:val'), nsid)
        abstractNum.append(nsid_element)
        
        # Add multilevel type element
        multiLevelType = OxmlElement('w:multiLevelType')
        multiLevelType.set(qn('w:val'), 'hybridMultilevel')
        abstractNum.append(multiLevelType)
        
        # Add template element for compatibility
        tmpl = OxmlElement('w:tmpl')
        tmpl.set(qn('w:val'), '0409001D')
        abstractNum.append(tmpl)
        
        # Add level for the list (only adding level 0 for simplicity)
        # Level 0
        level = OxmlElement('w:lvl')
        level.set(qn('w:ilvl'), '0')
        
        # Set start at 1
        start = OxmlElement('w:start')
        start.set(qn('w:val'), '1')
        level.append(start)
        
        # Set number format (bullet or decimal)
        numFmt = OxmlElement('w:numFmt')
        if bullet:
            numFmt.set(qn('w:val'), 'bullet')
        else:
            numFmt.set(qn('w:val'), 'decimal')
        level.append(numFmt)
        
        # Level text
        lvlText = OxmlElement('w:lvlText')
        if bullet:
            lvlText.set(qn('w:val'), '•')
        else:
            lvlText.set(qn('w:val'), '%1.')
        level.append(lvlText)
        
        # Level justification
        lvlJc = OxmlElement('w:lvlJc')
        lvlJc.set(qn('w:val'), 'left')
        level.append(lvlJc)
        
        # Font for bullet character
        if bullet:
            rPr = OxmlElement('w:rPr')
            rFonts = OxmlElement('w:rFonts')
            rFonts.set(qn('w:ascii'), 'Symbol')
            rFonts.set(qn('w:hAnsi'), 'Symbol')
            rFonts.set(qn('w:hint'), 'default')
            rPr.append(rFonts)
            level.append(rPr)
        
        # Paragraph spacing
        pPr = OxmlElement('w:pPr')
        ind = OxmlElement('w:ind')
        ind.set(qn('w:left'), '1270')  # 1.25 cm in twips
        ind.set(qn('w:hanging'), '635')  # 0.63 cm in twips
        pPr.append(ind)
        level.append(pPr)
        
        # Add level to abstractNum
        abstractNum.append(level)
        
        # Add abstractNum to numbering
        element.append(abstractNum)
        
        # Create a num element that references the abstractNum if it doesn't exist
        if not num_exists:
            num = OxmlElement('w:num')
            num.set(qn('w:numId'), str(abstractNumId))
            abstractNumId_element = OxmlElement('w:abstractNumId')
            abstractNumId_element.set(qn('w:val'), str(abstractNumId))
            num.append(abstractNumId_element)
            
            # Add num to numbering
            element.append(num)
        
        # Return the numId
        return abstractNumId
        
    def _add_list_item(self, text, is_bullet=True):
        """Add a list item with proper Word list formatting"""
        # Create a paragraph with appropriate style
        if is_bullet:
            p = self.document.add_paragraph(style='GOST Bulleted List')
        else:
            p = self.document.add_paragraph(style='GOST Numbered List')
            
        p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
        
        # Check if we need to remove a bullet character at the start
        if is_bullet and (text.startswith('- ') or text.startswith('• ')):
            text = text[2:]
            
        # Add text content
        p.add_run(text)
        
        # Add numbering property in a safer way
        pPr = p._element.get_or_add_pPr()
        
        # Check if numPr already exists to avoid duplicates
        numPr = None
        for child in pPr:
            if child.tag.endswith('numPr'):
                numPr = child
                break
        
        if numPr is None:
            numPr = OxmlElement('w:numPr')
            pPr.append(numPr)
        else:
            # Clear any existing elements to avoid conflicts
            for child in list(numPr):
                numPr.remove(child)
        
        # Add ilvl element
        ilvl = OxmlElement('w:ilvl')
        ilvl.set(qn('w:val'), '0')
        numPr.append(ilvl)
        
        # Add numId element
        numId = OxmlElement('w:numId')
        if is_bullet:
            numId.set(qn('w:val'), str(self.bullet_list_id))
        else:
            numId.set(qn('w:val'), str(self.number_list_id))
        numPr.append(numId)
        
        return p

    def create_title_page(self, title="", author="", institution="", city="", year=""):
        # Add title page
        title_section = self.document.sections[0]
        
        # Add empty paragraphs to position the title in the middle of the page
        for _ in range(10):
            p = self.document.add_paragraph()
            p.paragraph_format.first_line_indent = Cm(0)  # Ensure no indentation
        
        # Add title
        title_paragraph = self.document.add_paragraph()
        title_paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER
        title_paragraph.paragraph_format.first_line_indent = Cm(0)  # Ensure no indentation
        title_run = title_paragraph.add_run(title)
        title_run.bold = True
        title_run.font.size = Pt(16)
        
        # Add author info at the bottom
        for _ in range(5):
            p = self.document.add_paragraph()
            p.paragraph_format.first_line_indent = Cm(0)  # Ensure no indentation
            
        author_paragraph = self.document.add_paragraph()
        author_paragraph.alignment = WD_ALIGN_PARAGRAPH.RIGHT
        author_paragraph.paragraph_format.first_line_indent = Cm(0)  # Ensure no indentation
        author_paragraph.add_run(f"Автор: {author}")
        
        # Add institution
        if institution:
            inst_paragraph = self.document.add_paragraph()
            inst_paragraph.alignment = WD_ALIGN_PARAGRAPH.RIGHT
            inst_paragraph.paragraph_format.first_line_indent = Cm(0)  # Ensure no indentation
            inst_paragraph.add_run(institution)
        
        # Add city and year at the bottom
        for _ in range(5):
            p = self.document.add_paragraph()
            p.paragraph_format.first_line_indent = Cm(0)  # Ensure no indentation
            
        bottom_paragraph = self.document.add_paragraph()
        bottom_paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER
        bottom_paragraph.paragraph_format.first_line_indent = Cm(0)  # Ensure no indentation
        bottom_paragraph.add_run(f"{city}, {year}")
        
        # Add section break for the next page
        self.document.add_section(WD_SECTION.NEW_PAGE)
        
        # Copy margins from the first section to the new section
        self._copy_section_settings(title_section)
        
        self.current_page += 1

    def is_section_header(self, line):
        """
        Determine if a line is a section header using ML if available,
        otherwise fall back to regex-based detection.
        """
        # First, check with ML classifier if available
        if self.use_ml and self.classifier:
            raw_prediction = self.classifier.predict([line])[0]
            
            # Use post-processing rules if available
            if hasattr(self.classifier, 'post_process_prediction'):
                return self.classifier.post_process_prediction(line, raw_prediction, threshold=0.7)
            
            # Legacy fallback if post_process_prediction is not available
            if raw_prediction > 0.7:  # High confidence for header
                return True
            elif raw_prediction < 0.3:  # High confidence for normal text
                return False
            # If prediction is uncertain (between 0.3 and 0.7), use regex as fallback
        
        # Regular expression patterns for different header types
        main_section_pattern = r'^(ВВЕДЕНИЕ|ГЛАВА\s+\d+\..*|ЗАКЛЮЧЕНИЕ|СПИСОК\s+ИСПОЛЬЗ[УОЫА]ЕМ[ОЫАЙ]*\s+ЛИТЕРАТУРЫ)$'
        subsection_pattern = r'^(\d+\.\d+\.?)\s*[\t\s]*(.*)$'
        
        if re.match(main_section_pattern, line, re.IGNORECASE):
            return True
        elif re.match(subsection_pattern, line):
            return True
        
        return False

    def parse_text(self, text):
        # Split text into lines
        lines = text.split('\n')
        
        # List to store all document elements in order
        document_elements = []
        
        # If ML is available, classify all lines
        if self.use_ml and self.classifier:
            print("Using ML classifier for document structure detection...")
            raw_predictions = self.classifier.predict(lines)
            
            # Apply context-aware document classification if available
            if hasattr(self.classifier, 'predict_document'):
                print("Using context-aware document structure detection...")
                # This uses the document context to improve classification accuracy
                classifications = self.classifier.predict_document(lines)
                
                # Convert class indices to class names
                if hasattr(self.classifier, 'class_names'):
                    header_predictions = [cls == self.classifier.HEADER for cls in classifications]
                    list_predictions = [cls == self.classifier.LIST for cls in classifications]
                else:
                    # Legacy fallback
                    header_predictions = [cls == 0 for cls in classifications]
                    list_predictions = [cls == 1 for cls in classifications]
            # Apply post-processing if available (for individual line classification)
            elif hasattr(self.classifier, 'post_process_prediction'):
                print("Using individual line classification with post-processing...")
                classifications = [self.classifier.post_process_prediction(line, pred) 
                                for line, pred in zip(lines, raw_predictions)]
                
                # Convert class indices to class names
                if hasattr(self.classifier, 'class_names'):
                    header_predictions = [cls == self.classifier.HEADER for cls in classifications]
                    list_predictions = [cls == self.classifier.LIST for cls in classifications]
                else:
                    # Legacy fallback
                    header_predictions = [cls == 0 for cls in classifications]
                    list_predictions = [cls == 1 for cls in classifications]
            else:
                # Legacy processing
                header_predictions = raw_predictions > 0.5
                list_predictions = None
        else:
            print("ML classifier not available, using regex-based detection...")
            header_predictions = None
            list_predictions = None
        
        # Process each line in order
        for i, line in enumerate(lines):
            line = line.strip()
            if not line:
                continue
            
            # Use ML predictions if available
            is_header = header_predictions[i] if header_predictions is not None else self.is_section_header(line)
            is_list_item = list_predictions[i] if list_predictions is not None else False
            
            # Check if this is a section header (main or subsection) for formatting purposes only
            # These checks don't affect the document order, just the formatting
            main_section_match = re.match(r'^(ВВЕДЕНИЕ|ГЛАВА\s+\d+\..*|ЗАКЛЮЧЕНИЕ|СПИСОК\s+ИСПОЛЬЗ[УОЫА]ЕМ[ОЫАЙ]*\s+ЛИТЕРАТУРЫ)$', line, re.IGNORECASE)
            subsection_match = re.match(r'^(\d+\.\d+\.?)\s*[\t\s]*(.*)$', line)  # Handle tabs and multiple spaces
            
            # Additional check for chapter headings that might not match the exact pattern
            chapter_match = re.match(r'^ГЛАВА\s+\d+', line, re.IGNORECASE)
            
            # Debug prints for header detection
            if 'ГЛАВА' in line.upper():
                print(f"Debug - Line {i+1}: '{line}'")
                print(f"  Is header: {is_header}")
                print(f"  Main section match: {main_section_match is not None}")
                print(f"  Chapter match: {chapter_match is not None}")
            
            # Add the element to the document with its type and formatting information
            element = {
                'text': line,
                'type': 'unknown'
            }
            
            if is_header:
                element['type'] = 'header'
                if main_section_match:
                    element['level'] = 1
                    element['format'] = 'main_section'
                    if 'ГЛАВА' in line.upper():
                        print(f"  → Classified as main_section via main_section_match")
                elif chapter_match:  # Add this check for chapter headings
                    element['level'] = 1
                    element['format'] = 'main_section'
                    print(f"  → Classified as main_section via chapter_match")
                elif subsection_match:
                    element['level'] = 2
                    element['format'] = 'subsection'
                    element['number'] = subsection_match.group(1)
                    element['title'] = subsection_match.group(2)
                else:
                    element['level'] = 1
                    element['format'] = 'other_header'
                    if 'ГЛАВА' in line.upper():
                        print(f"  → Classified as other_header")
            elif is_list_item:
                element['type'] = 'list_item'
                # Check if this is a bibliography item
                if re.match(r'^\d+\.\s+', line) and any(prev['text'].upper().find('СПИСОК') >= 0 and prev['text'].upper().find('ЛИТЕРАТУР') >= 0 for prev in document_elements[-10:] if prev['type'] == 'header'):
                    element['format'] = 'bibliography'
                else:
                    element['format'] = 'regular_list'
            else:
                element['type'] = 'text'
                element['format'] = 'paragraph'
                if 'ГЛАВА' in line.upper():
                    print(f"  → Classified as paragraph (not header)")
            
            document_elements.append(element)
        
        # Store the elements for document creation
        self.document_elements = document_elements
        
        # Print a summary of main headers for debugging
        print("\nMain headers detected:")
        for element in document_elements:
            if element['type'] == 'header' and element['level'] == 1:
                print(f"- {element['text']} (format: {element['format']})")

    def _copy_section_settings(self, reference_section):
        """Copy settings from a reference section to the most recent section in the document"""
        if len(self.document.sections) > 0:
            new_section = self.document.sections[-1]
            new_section.left_margin = reference_section.left_margin
            new_section.right_margin = reference_section.right_margin
            new_section.top_margin = reference_section.top_margin
            new_section.bottom_margin = reference_section.bottom_margin
            new_section.page_height = reference_section.page_height
            new_section.page_width = reference_section.page_width
            return True
        return False
        
    def create_document_content(self):
        """Create document content based on the document elements in order"""
        # Flag to track if we're within a section
        current_section = None
        is_first_major_header = True
        
        # Variables to track lists
        in_list = False
        
        # Get reference to the first section for margin settings
        first_section = self.document.sections[0]
        
        for element in self.document_elements:
            if element['type'] == 'header':
                # End any active list
                in_list = False
                
                # For headers, add with appropriate formatting
                if element['level'] == 1:
                    # Main section header - add page break before each main section except the first one
                    if not is_first_major_header:
                        # Check if this is a chapter header for debugging
                        if 'ГЛАВА' in element['text'].upper():
                            print(f'Adding page break for chapter: {element["text"]}')
                        else:
                            print(f'Adding page break for section: {element["text"]}')
                        
                        # Count sections before adding page break
                        section_count_before = len(self.document.sections)
                        
                        # Add the page break
                        self.document.add_page_break()
                        
                        # If this created a new section, copy margins
                        if len(self.document.sections) > section_count_before:
                            self._copy_section_settings(first_section)
                    else:
                        is_first_major_header = False
                        print(f'First major header (no page break): {element["text"]}')
                    
                    # Main section header - using Word's built-in Heading 1 style
                    heading = self.document.add_heading(level=1)
                    heading_run = heading.add_run(element['text'])
                    heading_run.bold = True
                    heading_run.font.size = Pt(14)
                    heading_run.font.name = 'Times New Roman'
                    
                    # Set custom paragraph format to override style defaults
                    heading.alignment = WD_ALIGN_PARAGRAPH.CENTER
                    heading.paragraph_format.space_after = Pt(14)
                    heading.paragraph_format.space_before = Pt(14)
                    heading.paragraph_format.first_line_indent = Cm(0)
                    
                    # Ensure the font is Times New Roman for the entire heading
                    for run in heading.runs:
                        run.font.name = 'Times New Roman'
                    
                    # Update current section for bibliography detection
                    current_section = element['text']
                elif element['level'] == 2:
                    # Subsection header - using Word's built-in Heading 2 style
                    if element.get('number') and element.get('title'):
                        heading_text = f"{element['number']} {element['title']}"
                    else:
                        heading_text = element['text']
                    
                    heading = self.document.add_heading(level=2)
                    heading_run = heading.add_run(heading_text)
                    heading_run.bold = True
                    heading_run.font.name = 'Times New Roman'
                    
                    # Set custom paragraph format to override style defaults
                    heading.alignment = WD_ALIGN_PARAGRAPH.CENTER
                    heading.paragraph_format.space_after = Pt(14)
                    heading.paragraph_format.space_before = Pt(14)
                    heading.paragraph_format.first_line_indent = Cm(0)
                    
                    # Ensure the font is Times New Roman for the entire heading
                    for run in heading.runs:
                        run.font.name = 'Times New Roman'
                else:
                    # Other header - using a lower level heading
                    heading = self.document.add_heading(level=3)
                    heading_run = heading.add_run(element['text'])
                    heading_run.bold = True
                    heading_run.font.name = 'Times New Roman'
                    
                    # Set custom paragraph format to override style defaults
                    heading.alignment = WD_ALIGN_PARAGRAPH.CENTER
                    heading.paragraph_format.space_after = Pt(14)
                    heading.paragraph_format.first_line_indent = Cm(0)
                    
                    # Ensure the font is Times New Roman for the entire heading
                    for run in heading.runs:
                        run.font.name = 'Times New Roman'
            
            elif element['type'] == 'list_item':
                # For list items, format differently based on bibliography or regular list
                if element['format'] == 'bibliography' or (current_section and "СПИСОК" in current_section.upper() and "ЛИТЕРАТУР" in current_section.upper()):
                    p = self.document.add_paragraph(style='GOST Bibliography')
                    p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
                    p.add_run(element['text'])
                else:
                    # Determine list type based on text pattern
                    text = element['text']
                    
                    # Check for different list item patterns
                    if text.startswith('- ') or text.startswith('• '):
                        # Bulleted list
                        self._add_list_item(text, is_bullet=True)
                    elif re.match(r'^[0-9]+[\.\)]\s+', text):
                        # Numbered list
                        self._add_list_item(text, is_bullet=False)
                    elif re.match(r'^[a-zA-Z]+[\.\)]\s+', text):
                        # Lettered list (treat as numbered for now)
                        self._add_list_item(text, is_bullet=False)
                    else:
                        # Default to bulleted for other formats
                        self._add_list_item(text, is_bullet=True)
                    
                    # Flag that we're in a list
                    in_list = True
            
            elif element['type'] == 'text':
                # End any active list
                in_list = False
                
                # Regular paragraph text
                p = self.document.add_paragraph()
                p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
                p.paragraph_format.first_line_indent = Cm(1.25)
                p.paragraph_format.line_spacing_rule = WD_LINE_SPACING.ONE_POINT_FIVE
                p.paragraph_format.space_after = Pt(0)
                p.add_run(element['text'])

    def _add_bibliography_item(self, item):
        """Add a bibliography item formatted according to GOST standards."""
        p = self.document.add_paragraph(style='GOST Bibliography')
        p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
        
        # Add the bibliography item text
        p.add_run(item)

    def create_table_of_contents(self):
        """Create a table of contents using Word's TOC field"""
        # Add table of contents title
        toc_title = self.document.add_paragraph()
        toc_title.alignment = WD_ALIGN_PARAGRAPH.CENTER
        toc_title.paragraph_format.space_after = Pt(24)  # Add some space after the heading
        toc_run = toc_title.add_run("СОДЕРЖАНИЕ")
        toc_run.bold = True
        toc_run.font.size = Pt(14)
        
        # Create TOC field
        paragraph = self.document.add_paragraph()
        run = paragraph.add_run()
        
        # Begin field
        fldChar = OxmlElement('w:fldChar')
        fldChar.set(qn('w:fldCharType'), 'begin')
        run._element.append(fldChar)
        
        # Field instruction text
        instrText = OxmlElement('w:instrText')
        instrText.set(qn('xml:space'), 'preserve')
        instrText.text = ' TOC \\o "1-3" \\h \\z \\u '
        run._element.append(instrText)
        
        # Separate character
        fldChar = OxmlElement('w:fldChar')
        fldChar.set(qn('w:fldCharType'), 'separate')
        run._element.append(fldChar)
        
        # Add a placeholder text that will be replaced when the TOC is updated
        instrText = run.add_text("Щелкните правой кнопкой мыши и выберите 'Обновить поле' для обновления содержания.")
        
        # End field
        fldChar = OxmlElement('w:fldChar')
        fldChar.set(qn('w:fldCharType'), 'end')
        run._element.append(fldChar)
        
        # Get reference to the first section for margin settings
        first_section = self.document.sections[0]
        
        # Count sections before adding page break
        section_count_before = len(self.document.sections)
        
        # Add page break after TOC
        self.document.add_page_break()
        
        # If this creates a new section, copy margins
        if len(self.document.sections) > section_count_before:
            self._copy_section_settings(first_section)
        
        self.current_page += 1

    def apply_page_numbering(self, input_docx, output_docx=None):
        """
        Apply page numbering to a Word document using Spire.Doc
        
        Parameters:
        input_docx (str): Path to the input DOCX file
        output_docx (str, optional): Path to save the output DOCX file. If None, overwrites the input file.
        
        Returns:
        str: Path to the output file
        """
        if not SPIRE_AVAILABLE:
            print("Warning: Spire.Doc not available. Page numbering was not applied.")
            return input_docx
        
        output_file = output_docx if output_docx else input_docx
        
        try:
            # Create a Document object
            document = SpireDocument()
            
            # Load the Word file
            document.LoadFromFile(input_docx)
            
            # Set up page numbering in GOST style (centered page numbers in the footer)
            for i in range(document.Sections.Count):
                section = document.Sections[i]
                
                # Get the footer of the section
                footer = section.HeadersFooters.Footer
                
                # No page number on first page (title page)
                if i == 0:
                    section.PageSetup.DifferentFirstPageHeaderFooter = True
                    continue
                
                # Clear existing footer content to avoid positioning issues
                footer.ChildObjects.Clear()
                
                # Add page number to the footer
                footerParagraph = footer.AddParagraph()
                
                # For GOST style, typically just the page number (not "Page X of Y")
                footerParagraph.AppendField("page number", FieldType.FieldPage)
                
                # Make sure the paragraph is cleared of any other formatting or content
                footerParagraph.Format.HorizontalAlignment = HorizontalAlignment.Center
                footerParagraph.Format.SetFirstLineIndent(0)
                
                # Apply GOST styling to the page number (Times New Roman, 14pt)
                style = ParagraphStyle(document)
                style.CharacterFormat.FontName = "Times New Roman"
                style.CharacterFormat.FontSize = 14
                
                # Ensure the style also has centering
                style.ParagraphFormat.HorizontalAlignment = HorizontalAlignment.Center
                
                # Apply the style both to the document styles collection and directly to the paragraph
                document.Styles.Add(style)
                footerParagraph.ApplyStyle(style)
                
                # Ensure alignment after style is applied (some styles might override it)
                footerParagraph.Format.HorizontalAlignment = HorizontalAlignment.Center
            
            # Save the document
            document.SaveToFile(output_file)
            print(f"Page numbering applied to {output_file}")
            
            # Dispose resources
            document.Dispose()
            
            return output_file
        
        except Exception as e:
            print(f"Error applying page numbering: {e}")
            return input_docx

    def create_gost_document(self, input_text, output_file, title="", author="", institution="", city="", year=""):
        # Parse input text
        self.parse_text(input_text)
        
        # Create title page
        self.create_title_page(title, author, institution, city, year)
        
        # Create table of contents
        self.create_table_of_contents()
        
        # Create document content
        self.create_document_content()
        
        # Ensure all sections have correct margins
        first_section = self.document.sections[0]
        for i in range(1, len(self.document.sections)):
            section = self.document.sections[i]
            section.left_margin = first_section.left_margin
            section.right_margin = first_section.right_margin
            section.top_margin = first_section.top_margin
            section.bottom_margin = first_section.bottom_margin
            section.page_height = first_section.page_height
            section.page_width = first_section.page_width
        
        # Save the document with python-docx
        self.document.save(output_file)
        print(f"Document saved as {output_file}")
        
        # Apply page numbering if Spire.Doc is available
        if SPIRE_AVAILABLE:
            output_file = self.apply_page_numbering(output_file)
        
        return output_file

def train_ml_classifier():
    """Train the ML classifier if not already trained."""
    try:
        from ml_classifier import train_and_save_model
        
        model_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'models')
        os.makedirs(model_dir, exist_ok=True)
        
        model_path = os.path.join(model_dir, 'section_classifier.pt')
        if not os.path.exists(model_path):
            print("Training ML classifier model...")
            train_and_save_model(model_path)
            print("Training complete!")
        else:
            print("ML model already exists.")
    except ImportError:
        print("ML dependencies not available. Skipping training.")
    except Exception as e:
        print(f"Error training ML model: {e}")

def main():
    parser = argparse.ArgumentParser(description='Convert plaintext to ГОСТ formatted document')
    parser.add_argument('input_file', help='Input text file')
    parser.add_argument('output_file', help='Output DOCX file')
    parser.add_argument('--title', default='ЗАГОЛОВОК РАБОТЫ', help='Document title')
    parser.add_argument('--author', default='Автор: ФИО', help='Author name')
    parser.add_argument('--institution', default='Название учебного заведения', help='Institution name')
    parser.add_argument('--city', default='Город', help='City')
    parser.add_argument('--year', default='2023', help='Year')
    parser.add_argument('--use-ml', action='store_true', help='Use ML for section detection')
    parser.add_argument('--train-ml', action='store_true', help='Train ML model before processing')
    
    args = parser.parse_args()
    
    # Train ML model if requested
    if args.train_ml:
        train_ml_classifier()
    
    # Read input file
    with open(args.input_file, 'r', encoding='utf-8') as f:
        input_text = f.read()
    
    # Create formatter and generate document
    formatter = GostFormatter(use_ml=args.use_ml)
    formatter.create_gost_document(
        input_text, 
        args.output_file,
        args.title,
        args.author,
        args.institution,
        args.city,
        args.year
    )

if __name__ == "__main__":
    main() 