from typing import List
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape, portrait
from reportlab.lib.units import mm
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
            
            margin = 20 * mm
            
            doc = SimpleDocTemplate(
                filename,
                pagesize=page_size,
                leftMargin=margin,
                rightMargin=margin,
                topMargin=margin,
                bottomMargin=margin
            )
            
            story = []
            
            title_style = self.styles['Title']
            title_style.fontSize = 16
            story.append(Paragraph(title, title_style))
            
            if subtitle:
                subtitle_style = self.styles['Normal']
                subtitle_style.fontSize = 12
                story.append(Paragraph(subtitle, subtitle_style))
            
            story.append(Spacer(1, 8))
            
            placed_count = len([s for s in singers if s.row >= 0])
            info_text = f"Reihen: {rows}, Spalten: {cols}, Sänger: {placed_count}"
            if staggered:
                info_text += " (versetzte Anordnung)"
            info_style = self.styles['Normal']
            info_style.fontSize = 10
            story.append(Paragraph(info_text, info_style))
            story.append(Spacer(1, 12))
            
            page_width = page_size[0] - 2 * margin
            page_height = page_size[1] - 2 * margin - 80
            
            if staggered:
                display_data, style_commands, col_widths, row_heights = self._create_staggered_grid(
                    singers, rows, cols, page_width, page_height, color_mode
                )
            else:
                display_data, style_commands, col_widths, row_heights = self._create_standard_grid(
                    singers, rows, cols, page_width, page_height, color_mode
                )
            
            if not display_data:
                story.append(Paragraph("Keine Sänger im Raster platziert.", self.styles['Normal']))
            else:
                table = Table(display_data, colWidths=col_widths, rowHeights=row_heights)
                
                base_style = [
                    ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                    ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                    ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
                    ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
                ]
                
                table.setStyle(TableStyle(base_style + style_commands))
                story.append(table)
            
            doc.build(story)
            return True
            
        except Exception as e:
            print(f"Error exporting PDF: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def _create_standard_grid(self, singers, rows, cols, page_width, page_height, color_mode):
        col_width = page_width / cols
        row_height = min(page_height / rows, 40 * mm)
        
        font_size = min(8, col_width / 5)
        
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
        
        style_commands.append(('FONTSIZE', (0, 0), (-1, -1), font_size))
        
        col_widths = [col_width] * cols
        row_heights = [row_height] * rows
        
        return display_data, style_commands, col_widths, row_heights
    
    def _create_staggered_grid(self, singers, rows, cols, page_width, page_height, color_mode):
        half_col_width = page_width / (2 * cols)
        row_height = min(page_height / rows, 40 * mm)
        
        font_size = min(8, half_col_width / 3)
        
        display_data = []
        style_commands = []
        
        color_map = self.VOICE_COLORS if color_mode == "color" else self.VOICE_COLORS_BW
        
        total_cols = 2 * cols
        
        for r in range(rows):
            row_data = [''] * total_cols
            
            for c in range(cols):
                singer = self._get_singer_at(singers, r, c)
                if singer:
                    name = singer.name
                    vg = singer.voice_group.value if hasattr(singer.voice_group, 'value') else str(singer.voice_group)
                    vg_short = vg.split()[0] if vg else ""
                    cell_text = f"{name}\n{vg}"
                    
                    if r % 2 == 0:
                        col_idx = 2 * c
                    else:
                        col_idx = 2 * c + 1
                    
                    if col_idx + 1 < total_cols:
                        row_data[col_idx] = cell_text
                        bg_color = color_map.get(vg_short, colors.white)
                        style_commands.append(('BACKGROUND', (col_idx, r), (col_idx, r), bg_color))
                        style_commands.append(('SPAN', (col_idx, r), (col_idx + 1, r)))
                    else:
                        row_data[col_idx] = cell_text
                        bg_color = color_map.get(vg_short, colors.white)
                        style_commands.append(('BACKGROUND', (col_idx, r), (col_idx, r), bg_color))
            
            display_data.append(row_data)
        
        style_commands.append(('FONTSIZE', (0, 0), (-1, -1), font_size))
        
        col_widths = [half_col_width] * total_cols
        row_heights = [row_height] * rows
        
        return display_data, style_commands, col_widths, row_heights
    
    def _get_singer_at(self, singers, row, col):
        for s in singers:
            if s.row == row and s.col == col:
                return s
        return None
