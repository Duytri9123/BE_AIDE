from pydantic import BaseModel
from typing import Optional

class BrandResponse(BaseModel):
    id: int
    name: str

class CategoryResponse(BaseModel):
    id: int
    name: str

class SeriesResponse(BaseModel):
    id: int
    name: str
    brand_id: int

class ModelResponse(BaseModel):
    id: int
    code: str
    name: str

class UserItemCreate(BaseModel):
    brand: str
    code: str
    name: str
    spec: str
    unit_price: float

class CatalogSearchRequest(BaseModel):
    category: Optional[str] = None
    brand: Optional[str] = None
    in_a: Optional[float] = None
    icu_ka: Optional[float] = None
    poles: Optional[int] = None
