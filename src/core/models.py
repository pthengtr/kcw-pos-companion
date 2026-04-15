from dataclasses import dataclass
from typing import Optional


@dataclass
class Product:
    bcode: str
    descr: Optional[str] = None
    model: Optional[str] = None
    brand: Optional[str] = None
    price1: Optional[float] = None