
from pathlib import Path
from ruamel.yaml import YAML
from pydantic import BaseModel, Field, ValidationError
from typing import Optional, List, Dict, Literal

yaml = YAML(typ='safe')

class Anchor(BaseModel):
    find: List[str]
    direction: Optional[Literal['right','below','same_line']] = None
    regex: Optional[str] = None
    region: Optional[Literal['lines','summary']] = None

class Precedence(BaseModel):
    force_pattern_over_dictionary: bool = False

class Pattern(BaseModel):
    proveedor: str
    aliases: Optional[List[str]] = None
    anchors: Optional[Dict[str, Anchor]] = None
    rules: List[str] = []
    descripcion: Dict[str, Optional[str]] = Field(default_factory=dict)
    iva_default: Optional[float] = None
    grouping: Optional[str] = None
    portes: Optional[Dict[str, str]] = None
    precedence: Precedence = Precedence()

def load_patterns(dirpath: Path) -> Dict[str, Pattern]:
    patterns: Dict[str, Pattern] = {}
    for path in dirpath.glob('*.yml'):
        try:
            text = path.read_text(encoding='utf-8')
            data = yaml.load(text)
        except Exception as e:
            raise RuntimeError(f"Error YAML en {path.name}: {e}")

        try:
            p = Pattern(**data)
            key = p.proveedor.upper()
            patterns[key] = p
            if p.aliases:
                for a in p.aliases:
                    patterns[a.upper()] = p
        except ValidationError as e:
            raise RuntimeError(f"Patrón inválido {path.name}: {e}")

    return patterns
