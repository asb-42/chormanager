from typing import List, Optional
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape, portrait
from reportlab.lib.units import inch, mm
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet


class PDFExporter:
    VOICE_COLORS = {
        'Sopran': colors.Color(1.0, 0.85, 0.85),
        'Alt': colors.Color(0.85, 0.85, 1.0),
        'Tenor': colors.Color(0.85, 1.0, 0.85),
        'Bass': colors.Color(1.0, 1.0, 0.85)
    }
    
    VOICE_COLORS_BW = {
        'Sopran': colors.Color(0.9, 0.9, 0.9),
        'Alt': colors.Color(0.8, 0.8, 0.8),
        'Tenor': colors.Color(0.7, 0.7, 0.7),
        'Bass': colors.Color(0.6, 0.6, 0.6)
    }
    
    def __init__(self):
        self.styles = getSampleStyleSheet()
    
    def export_formation(self, singers: List, rows: int, cols: int,
                        filename: str, title: str = "Choraufstellung",
                        subtitle: str = "",
                        staggered: bool = False,
                        orientation: str = "landscape",
                        color_mode: str = "color") -> bool:
        try:
            if orientation == "landscape":
                page_size = landscape(A4)
            else:
                page_size = portrait(A4)
            
            margin_left = 30
            margin_right = 30
            margin_top = 30
            margin_bottom = 30
            
            doc = SimpleDocTemplate(
                filename,
                pagesize=page_size,
                leftMargin=margin_left,
                rightMargin=margin_right,
                topMargin=margin_top,
                bottomMargin=margin_bottom
            )
            
            story = []
            
            story.append(Paragraph(title, self.styles['Title']))
            if subtitle:
                story.append(Paragraph(subtitle, self.styles['Normal']))
            story.append(Spacer(1, 12))
            
            info_text = f"Reihen: {rows}, Spalten: {cols}, Sänger: {len([s for s in singers if s.row >= 0])}"
            if staggered:
                info_text += " (versetzte Anordnung)"
            story.append(Paragraph(info_text, self.styles['Normal']))
            story.append(Spacer(1, 12))
            
            page_width = page_size[0] - margin_left - margin_right
            page_height = page_size[1] - margin_top - margin_bottom - 100
            
            if staggered:
                display_data, style_commands = self._create_staggered_grid(
                    singers, rows, cols, page_width, page_height, color_mode
                )
            else:
                display_data, style_commands = self._create_standard_grid(
                    singers, rows, cols, page_width, page_height, color_mode
                )
            
            if not display_data:
                story.append(Paragraph("Keine Sänger im Raster platziert.", self.styles['Normal']))
            else:
                table = Table(display_data)
                
                base_style = [
                    ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                    ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                    ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
                    ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
                    ('FONTSIZE', (0, 0), (-1, -1), 8),
                ]
                
                table.setStyle(TableStyle(base_style + style_commands))
                story.append(table)
            
            doc.build(story)
            return True
            
        except Exception as e:
            print(f"Error exporting PDF: {e}")
            return False
    
    def _create_standard_grid(self, singers, rows, cols, page_width, page_height, color_mode):
        col_width = page_width / cols
        row_height = min(page_height / rows, 40)
        
        display_data = []
        style_commands = []
        
        color_map = self.VOICE_COLORS if color_mode == "color" else self.VOICE_COLORS_BW
        
        for r in range(rows):
            row_data = []
            for c in range(cols):
                singer = self._get_singer_at(singers, r, c)
                if singer:
                    name = singer.name
                    vg = singer.voice_group.value if hasattr(singer.voice_group, 'value') else str(singer.voice_group)
                    vg_short = vg.split()[0] if vg else ""
                    cell_text = f"{name}\n{vg}"
                    row_data.append(cell_text)
                    
                    bg_color = color_map.get(vg_short, colors.white)
                    style_commands.append(('BACKGROUND', (c, r), (c, r), bg_color))
                else:
                    row_data.append("")
            display_data.append(row_data)
        
        col_widths = [col_width] * cols
        row_heights = [row_height] * rows
        
        return display_data, style_commands
    
    def _create_staggered_grid(self, singers, rows, cols, page_width, page_height, color_mode):
        effective_cols = cols * 2 + 1
        col_width = page_width / effective_cols
        row_height = min(page_height / rows, 40)
        
        display_data = []
        style_commands = []
        
        color_map = self.VOICE_COLORS if color_mode == "color" else self.VOICE_COLORS_BW
        
        for r in range(rows):
            row_data = []
            for c in range(effective_cols):
                if r % 2 == 1:
                    if c == 0:
                        row_data.append("")
                        continue
                    real_col = (c - 1) // 2
                    is_offset = (c - 1) % 2 == 0
                else:
                    real_col = c // 2
                    is_offset = c % 2 == 1
                
                if is_offset:
                    row_data.append("")
                    continue
                
                singer = self._get_singer_at(singers, r, real_col)
                if singer:
                    name = singer.name
                    vg = singer.voice_group.value if hasattr(singer.voice_group, 'value') else str(singer.voice_group)
                    vg_short = vg.split()[0] if vg else ""
                    cell_text = f"{name}\n{vg}"
                    row_data.append(cell_text)
                    
                    bg_color = color_map.get(vg_short, colors.white)
                    style_commands.append(('BACKGROUND', (c, r), (c, r), bg_color))
                else:
                    row_data.append("")
            
            display_data.append(row_data)
        
        return display_data, style_commands
    
    def _get_singer_at(self, singers, row, col):
        for s in singers:
            if s.row == row and s.col == col:
                return s
        return None
