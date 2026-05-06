from fastapi import FastAPI
from app.database import engine, Base
from app.routers import users, products, orders

app = FastAPI(title="E-commerce API")

@app.on_event("startup")
def startup():
    Base.metadata.create_all(bind=engine)

app.include_router(users.router)
app.include_router(products.router)
app.include_router(orders.router)

@app.get("/health")
def health():
    return {"status": "ok"}