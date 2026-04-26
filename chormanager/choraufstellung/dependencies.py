# TDD: Centralized dependency management with graceful fallbacks
import os
import sys
import json
from typing import List, Dict, Any, Optional, Tuple, Callable

SINGER_MODEL_AVAILABLE = False
STORAGE_AVAILABLE = False
PDF_EXPORT_AVAILABLE = False
CONFIG_AVAILABLE = False

VoiceGroup = None
Singer = None
voice_group_color = None
FormationStorage = None
PDFExporter = None
load_settings = None
save_settings = None

try:
    from singer_model import Singer, VoiceGroup, voice_group_color
    from storage import FormationStorage
    from pdf_export import PDFExporter
    from config import load_settings, save_settings
    SINGER_MODEL_AVAILABLE = True
    STORAGE_AVAILABLE = True
    PDF_EXPORT_AVAILABLE = True
    CONFIG_AVAILABLE = True
except ImportError:
    pass


def get_voice_group_value(vg) -> str:
    if hasattr(vg, 'value'):
        return vg.value
    return str(vg)


def create_singer_fallback(name: str, voice_group, height: int = 0, singer_id: str = "1") -> Any:
    class FallbackVoiceGroup:
        def __init__(self, val):
            self.value = val
    class FallbackSinger:
        def __init__(self, name, voice_group, height, singer_id):
            self.name = name
            self.voice_group = voice_group
            self.height = height
            self.singer_id = singer_id
            self.row = -1
            self.col = -1
            self.affinity = ""
        def to_dict(self):
            return {
                "name": self.name,
                "voice_group": get_voice_group_value(self.voice_group),
                "height": self.height,
                "singer_id": self.singer_id,
                "row": self.row,
                "col": self.col,
                "affinity": self.affinity
            }
        @classmethod
        def from_dict(cls, data):
            vg_val = data.get("voice_group", "Sopran 1")
            try:
                if VoiceGroup:
                    vg = VoiceGroup(vg_val)
                else:
                    vg = FallbackVoiceGroup(vg_val)
            except:
                vg = FallbackVoiceGroup(vg_val)
            return cls(
                name=data.get("name", ""),
                voice_group=vg,
                height=data.get("height", 0),
                singer_id=data.get("singer_id", "1")
            )
    return FallbackSinger(name, voice_group, height, singer_id)


def get_valid_voice_groups() -> List[str]:
    try:
        config_file = "config/voice_groups.json"
        if os.path.exists(config_file):
            with open(config_file, 'r', encoding='utf-8') as f:
                return [vg["id"] for vg in json.load(f).get("voice_groups", [])]
    except:
        pass
    return ["Sopran 1", "Sopran 2", "Alt 1", "Alt 2", "Tenor 1", "Tenor 2", "Bass 1", "Bass 2"]


def get_voice_group_color_fallback(vid: str) -> str:
    try:
        config_file = "config/voice_groups.json"
        if os.path.exists(config_file):
            with open(config_file, 'r', encoding='utf-8') as f:
                for vg in json.load(f).get("voice_groups", []):
                    if vg["id"] == vid:
                        return vg["color"]
    except:
        pass
    return "#cccccc"


def get_storage_fallback() -> Any:
    class FallbackStorage:
        def load_formation(self, fp: str) -> Optional[Dict]:
            return None
        def save_formation(self, *args, **kwargs) -> bool:
            return True
    return FallbackStorage() if not STORAGE_AVAILABLE else None


def get_pdf_exporter_fallback() -> Any:
    class FallbackPDFExporter:
        def export_formation(self, *args, **kwargs) -> bool:
            return True
    return FallbackPDFExporter() if not PDF_EXPORT_AVAILABLE else None


def get_settings_fallback() -> Dict[str, str]:
    return {"theme": "light"}


__all__ = [
    'VoiceGroup', 'Singer', 'voice_group_color',
    'FormationStorage', 'PDFExporter',
    'load_settings', 'save_settings',
    'SINGER_MODEL_AVAILABLE', 'STORAGE_AVAILABLE', 
    'PDF_EXPORT_AVAILABLE', 'CONFIG_AVAILABLE',
    'get_voice_group_value', 'create_singer_fallback',
    'get_valid_voice_groups', 'get_voice_group_color_fallback',
    'get_storage_fallback', 'get_pdf_exporter_fallback', 'get_settings_fallback'
]