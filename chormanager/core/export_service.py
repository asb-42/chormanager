"""Export service for ChorManager - pure Python logic for exporting data."""

import csv
import io
from typing import List, Dict, Any


class ExportService:
    """Service for exporting data to various formats."""
    
    def get_export_data(self, items: List[Any], fields: List[str]) -> List[Dict[str, Any]]:
        """Convert items to exportable dictionary list.
        
        Args:
            items: List of objects to export (projects, singers, etc.)
            fields: List of field names to include.
            
        Returns:
            List of dictionaries with selected fields.
        """
        data = []
        for item in items:
            row = {}
            for field in fields:
                # Handle computed fields
                if field == "age" and hasattr(item, 'age'):
                    value = item.age()
                elif hasattr(item, field):
                    value = getattr(item, field)
                else:
                    value = ""
                
                # Convert None to empty string
                row[field] = str(value) if value is not None else ""
            
            data.append(row)
        
        return data
    
    def export_to_csv(self, data: List[Dict[str, Any]], fields: List[str], 
                        delimiter: str = ",") -> str:
        """Export data to CSV format.
        
        Args:
            data: List of dictionaries to export.
            fields: List of field names (column order).
            delimiter: CSV delimiter (default: comma).
            
        Returns:
            CSV string.
        """
        output = io.StringIO()
        
        if not data:
            return ""
        
        writer = csv.DictWriter(output, fieldnames=fields, delimiter=delimiter)
        writer.writeheader()
        writer.writerows(data)
        
        return output.getvalue()
    
    def export_to_libreoffice_calc(self, data: List[Dict[str, Any]], 
                                 fields: List[str]) -> str:
        """Export data to LibreOffice Calc format (.ods).
        
        Args:
            data: List of dictionaries to export.
            fields: List of field names.
            
        Returns:
            ODS file content as string (tab-separated, suitable for Calc).
        """
        # Use tab delimiter for Calc compatibility
        return self.export_to_csv(data, fields, delimiter="\t")
    
    def export_to_libreoffice_writer(self, data: List[Dict[str, Any]], 
                                  fields: List[str]) -> str:
        """Export data to LibreOffice Writer format (.odt compatible HTML).
        
        Args:
            data: List of dictionaries to export.
            fields: List of field names.
            
        Returns:
            HTML string that can be opened by LibreOffice Writer.
        """
        html = ['<html><body>']
        html.append('<table border="1">')
        
        # Header
        html.append('<tr>')
        for field in fields:
            html.append(f'<th>{field}</th>')
        html.append('</tr>')
        
        # Data rows
        for row in data:
            html.append('<tr>')
            for field in fields:
                value = row.get(field, "")
                html.append(f'<td>{value}</td>')
            html.append('</tr>')
        
        html.append('</table></body></html>')
        return '\n'.join(html)
