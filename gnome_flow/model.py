import json
import uuid
from pathlib import Path
from dataclasses import dataclass, field, asdict
from typing import List, Dict, Any

CONFIG_DIR = Path.home() / ".config" / "gnome-flow"
FLOWS_FILE = CONFIG_DIR / "flows.json"


@dataclass
class Block:
    """Egyetlen építőkocka (Trigger, Action vagy Condition)."""
    id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    category: str = ""      # pl. 'keyboard', 'app', 'file', 'dbus', 'time', 'system', 'flow'
    type: str = ""          # pl. 'drive_mounted', 'dir_changed', 'open_app', 'notify'
    label: str = ""         # Megjelenő cím a kártyán
    subtitle: str = ""      # Másodlagos leírás (pl. '/media/user/...' vagy 'F1')
    params: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ValidityScope:
    """Érvényességi kör (Smart Life minta alapján)."""
    time_enabled: bool = False
    start_time: str = "08:00"
    end_time: str = "17:00"
    days: List[int] = field(default_factory=lambda: [0, 1, 2, 3, 4, 5, 6])  # 0=Hétfő .. 6=Vasárnap
    condition_mode: str = "any"  # 'any' (Bármilyen) vagy 'all' (Összes)
    conditions: List[Block] = field(default_factory=list)


@dataclass
class Flow:
    """Egy teljes automatizmus."""
    id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    name: str = "New Flow"
    slug: str = "new-flow"
    enabled: bool = True
    trigger_mode: str = "any"    # 'any' (Bármelyik) vagy 'all' (Minden)
    triggers: List[Block] = field(default_factory=list)
    actions: List[Block] = field(default_factory=list)
    scope: ValidityScope = field(default_factory=ValidityScope)

    @staticmethod
    def make_slug(name: str) -> str:
        tr = str.maketrans("áéíóöőúüűÁÉÍÓÖŐÚÜŰ ", "aeiooouuuAEIOOOUUU-")
        clean = "".join(c for c in name.translate(tr).lower() if c.isalnum() or c == "-")
        return clean.strip("-") or "flow"

    @classmethod
    def make_unique_name(
        cls,
        base_name: str,
        existing_flows: List["Flow"],
        ignore_id: str | None = None,
    ) -> str:
        taken_slugs = {
            f.slug for f in existing_flows if f.id != ignore_id
        }
        if cls.make_slug(base_name) not in taken_slugs:
            return base_name

        counter = 2
        while True:
            candidate = f"{base_name} {counter}"
            if cls.make_slug(candidate) not in taken_slugs:
                return candidate
            counter += 1

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Flow":
        scope_data = data.get("scope", {})
        scope = ValidityScope(
            time_enabled=scope_data.get("time_enabled", False),
            start_time=scope_data.get("start_time", "08:00"),
            end_time=scope_data.get("end_time", "17:00"),
            days=scope_data.get("days", [0, 1, 2, 3, 4, 5, 6]),
            condition_mode=scope_data.get("condition_mode", "any"),
            conditions=[Block(**c) for c in scope_data.get("conditions", [])],
        )
        return cls(
            id=data.get("id", str(uuid.uuid4())[:8]),
            name=data.get("name", "Unnamed Flow"),
            slug=data.get("slug", cls.make_slug(data.get("name", "unnamed-flow"))),
            enabled=data.get("enabled", True),
            trigger_mode=data.get("trigger_mode", "any"),
            triggers=[Block(**t) for t in data.get("triggers", [])],
            actions=[Block(**a) for a in data.get("actions", [])],
            scope=scope,
        )


def load_flows() -> List[Flow]:
    if not FLOWS_FILE.exists():
        return []
    try:
        raw = json.loads(FLOWS_FILE.read_text(encoding="utf-8"))
        return [Flow.from_dict(item) for item in raw]
    except Exception as e:
        print(f"Hiba a flows.json betöltésekor: {e}")
        return []


def save_flows(flows: List[Flow]) -> None:
    seen_slugs: set[str] = set()
    for f in flows:
        if f.slug in seen_slugs:
            raise ValueError(f"Duplicate flow CLI slug: '{f.slug}'")
        seen_slugs.add(f.slug)

    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    data = [f.to_dict() for f in flows]
    FLOWS_FILE.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")