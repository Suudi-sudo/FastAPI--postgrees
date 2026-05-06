from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional, List
from app.database import get_db
from app.models.models import Product

router = APIRouter(prefix="/products", tags=["products"])

# --- Pydantic schemas ---

class ProductCreate(BaseModel):
    name: str
    description: Optional[str] = None
    price: float
    stock_quantity: int = 0

class ProductResponse(BaseModel):
    id: str
    name: str
    description: Optional[str]
    price: float
    stock_quantity: int
    is_active: bool

    class Config:
        from_attributes = True

# --- Endpoints ---

@router.post("/", response_model=ProductResponse, status_code=201)
def create_product(body: ProductCreate, db: Session = Depends(get_db)):
    if body.price < 0:
        raise HTTPException(status_code=400, detail="Price cannot be negative")
    if body.stock_quantity < 0:
        raise HTTPException(status_code=400, detail="Stock cannot be negative")

    product = Product(
        name=body.name,
        description=body.description,
        price=body.price,
        stock_quantity=body.stock_quantity
    )
    db.add(product)
    db.commit()
    db.refresh(product)
    return {**product.__dict__, "id": str(product.id)}


@router.get("/", response_model=List[ProductResponse])
def get_products(
    is_active: Optional[bool] = Query(None),
    min_price: Optional[float] = Query(None),
    max_price: Optional[float] = Query(None),
    db: Session = Depends(get_db)
):
    query = db.query(Product)

    if is_active is not None:
        query = query.filter(Product.is_active == is_active)
    if min_price is not None:
        query = query.filter(Product.price >= min_price)
    if max_price is not None:
        query = query.filter(Product.price <= max_price)

    products = query.all()
    return [{**p.__dict__, "id": str(p.id)} for p in products]


@router.get("/{product_id}", response_model=ProductResponse)
def get_product(product_id: str, db: Session = Depends(get_db)):
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    return {**product.__dict__, "id": str(product.id)}