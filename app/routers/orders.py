from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import List
from database import get_db
from models.models import Order, OrderItem, Product, User

router = APIRouter(prefix="/orders", tags=["orders"])

# --- Pydantic schemas ---

class OrderItemCreate(BaseModel):
    product_id: str
    quantity: int

class OrderCreate(BaseModel):
    user_id: str
    items: List[OrderItemCreate]

class OrderItemResponse(BaseModel):
    product_id: str
    quantity: int
    unit_price: float

class OrderResponse(BaseModel):
    id: str
    user_id: str
    status: str
    total_amount: float
    items: List[OrderItemResponse] = []

    class Config:
        from_attributes = True

# --- Endpoints ---

@router.post("/", response_model=OrderResponse, status_code=201)
def create_order(body: OrderCreate, db: Session = Depends(get_db)):

    # 1. check user exists
    user = db.query(User).filter(User.id == body.user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # 2. check all products exist and have enough stock
    total_amount = 0
    order_items = []

    for item in body.items:
        product = db.query(Product).filter(Product.id == item.product_id).first()
        if not product:
            raise HTTPException(status_code=404, detail=f"Product {item.product_id} not found")
        if not product.is_active:
            raise HTTPException(status_code=400, detail=f"Product {product.name} is not available")
        if product.stock_quantity < item.quantity:
            raise HTTPException(status_code=400, detail=f"Not enough stock for {product.name}")

        total_amount += float(product.price) * item.quantity
        order_items.append((product, item.quantity, float(product.price)))

    # 3. create order + items + deduct stock — all in one transaction
    try:
        order = Order(
            user_id=body.user_id,
            total_amount=total_amount,
            status="pending"
        )
        db.add(order)
        db.flush()  # gets the order.id without committing yet

        for product, quantity, unit_price in order_items:
            order_item = OrderItem(
                order_id=order.id,
                product_id=product.id,
                quantity=quantity,
                unit_price=unit_price
            )
            db.add(order_item)
            product.stock_quantity -= quantity  # deduct stock

        db.commit()
        db.refresh(order)

    except Exception as e:
        db.rollback()  # if anything fails, undo everything
        raise HTTPException(status_code=500, detail="Order creation failed")

    return {
        "id": str(order.id),
        "user_id": str(order.user_id),
        "status": order.status,
        "total_amount": float(order.total_amount),
        "items": [
            {
                "product_id": str(i.product_id),
                "quantity": i.quantity,
                "unit_price": float(i.unit_price)
            }
            for i in order.items
        ]
    }


@router.get("/{order_id}", response_model=OrderResponse)
def get_order(order_id: str, db: Session = Depends(get_db)):
    order = db.query(Order).filter(Order.id == order_id).first()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")

    return {
        "id": str(order.id),
        "user_id": str(order.user_id),
        "status": order.status,
        "total_amount": float(order.total_amount),
        "items": [
            {
                "product_id": str(i.product_id),
                "quantity": i.quantity,
                "unit_price": float(i.unit_price)
            }
            for i in order.items
        ]
    }