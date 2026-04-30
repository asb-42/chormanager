from enum import Enum
from dataclasses import dataclass, field
import json
import uuid


class VoiceGroup(Enum):
    SOPRAN_1 = "Sopran 1"
    SOPRAN_2 = "Sopran 2"
    ALT_1 = "Alt 1"
    ALT_2 = "Alt 2"
    TENOR_1 = "Tenor 1"
    TENOR_2 = "Tenor 2"
    BASS_1 = "Bass 1"
    BASS_2 = "Bass 2"


@dataclass
class Singer:
    name: str
    voice_group: VoiceGroup
    height: int = 0
    singer_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    row: int = -1
    col: int = -1
    affinity: str = ""
    external_id: str = ""
    affinity_uuid: str = ""
    
    def to_dict(self):
        # Handle both string and enum voice_group
        vg = self.voice_group
        if hasattr(vg, 'value'):
            vg_str = vg.value
        else:
            vg_str = str(vg) if vg else ""
        return {
            "name": self.name,
            "voice_group": vg_str,
            "height": self.height,
            "singer_id": self.singer_id,
            "row": self.row,
            "col": self.col,
            "affinity": self.affinity,
            "external_id": self.external_id,
            "affinity_uuid": self.affinity_uuid
        }
    
    @classmethod
    def from_dict(cls, data, use_external_id=False):
        singer_id = data.get("singer_id")
        if not singer_id and use_external_id and data.get("external_id"):
            singer_id = data.get("external_id")
        if not singer_id:
            singer_id = str(uuid.uuid4())
        
        affinity_uuid = data.get("affinity_uuid", "")
        
        return cls(
            name=data["name"],
            voice_group=VoiceGroup(data["voice_group"]),
            height=data.get("height", 0),
            singer_id=singer_id,
            row=data.get("row", -1),
            col=data.get("col", -1),
            affinity=data.get("affinity", ""),
            external_id=data.get("external_id", ""),
            affinity_uuid=affinity_uuid
        )


def voice_group_color(voice_group: VoiceGroup) -> str:
    """Return hex color for voice group - loads from central config."""
    try:
        from config import get_voice_group_color
        vg_id = voice_group.value if hasattr(voice_group, 'value') else str(voice_group)
        return get_voice_group_color(vg_id)
    except Exception:
        return "#cccccc"
