import sys
import os
from pathlib import Path

_choraufstellung_src = os.path.join(os.path.dirname(__file__))
if _choraufstellung_src not in sys.path:
    sys.path.insert(0, _choraufstellung_src)

import core.grid_engine as _core_ge
GridEngine = _core_ge.GridEngine
GridConfig = _core_ge.GridConfig
SingerRef = _core_ge.SingerRef

import core.optimizer as _core_opt
FormationOptimizer = _core_opt.FormationOptimizer

import core.rules as _core_rules
ArrangementRule = _core_rules.ArrangementRule

import singer_model as _singer
Singer = _singer.Singer
VoiceGroup = _singer.VoiceGroup
voice_group_color = _singer.voice_group_color

import storage as _storage
FormationStorage = _storage.FormationStorage

import pdf_export as _pdf
PDFExporter = _pdf.PDFExporter

import config as _config
load_settings = _config.load_settings
save_settings = _config.save_settings
load_voice_groups_config = _config.load_voice_groups_config
get_valid_voice_groups = _config.get_valid_voice_groups

import ui.grid_widget as _ui_grid
FormationGrid = _ui_grid.FormationGrid

import ui.pool_widget as _ui_pool
SingerPool = _ui_pool.SingerPool

import ui.optimizer_dialog as _ui_opt
OptimizerDialog = _ui_opt.OptimizerDialog


def get_choraufstellung_data_dir():
    from ..config import get_data_dir
    return get_data_dir()


def get_choraufstellung_config_path():
    return Path(__file__).parent.parent.parent / "config" / "app.yaml"


class ChorAufstellungIntegration:
    
    def __init__(self, db_path=None, project_name=None, event_date=None):
        self.db_path = db_path
        self.project_name = project_name
        self.event_date = event_date
        self._singer_data = None
        self._event_data = None
    
    def load_from_chormanager(self):
        if not self.db_path:
            return False
        
        try:
            from chormanager.export import chormanager_db
            db = chormanager_db.ChorManagerDB(self.db_path)
            
            singers = db.get_available_singers(self.project_name, self.event_date)
            self._singer_data = singers
            
            return True
        except Exception as e:
            print(f"Failed to load from ChorManager: {e}")
            return False
    
    def get_singers_for_choraufstellung(self):
        if self._singer_data:
            return self._singer_data
        return []
    
    def get_event_info(self):
        return self._event_data
