from datetime import datetime
from typing import Optional, List, Dict
from pydantic import BaseModel, ConfigDict, Field


class LoginInput(BaseModel):
    username: str
    password: str


class UserOut(BaseModel):
    id: int
    username: str
    full_name: str
    role: str
    employee_code: Optional[str] = None
    model_config = ConfigDict(from_attributes=True)


class TokenOut(BaseModel):
    access_token: str
    token: str
    token_type: str = "bearer"
    role: str
    isStaff: bool
    staffProfile: Optional[Dict] = None
    user: UserOut


class ProductInput(BaseModel):
    name: str = Field(min_length=1, max_length=160)
    description: str = ""
    price: int = Field(gt=0)
    image_url: str = ""
    tag: Optional[str] = None
    category_code: str
    is_available: bool = True


class ProductOut(BaseModel):
    id: int
    name: str
    description: str
    price: int
    image_url: str
    tag: Optional[str]
    category_code: str
    category_name: str
    is_available: bool


class OrderLineInput(BaseModel):
    product_id: int
    quantity: int = Field(gt=0, le=99)
    options: List[Dict] = []


class OrderInput(BaseModel):
    order_type: str = "dine-in"
    table_code: Optional[str] = None
    customer_name: str = "Khách lẻ"
    student_id: Optional[str] = None
    address: Optional[str] = None
    phone_number: Optional[str] = None
    payment_method: str = "cash"
    cash_received: int = 0
    discount: int = Field(default=0, ge=0)
    items: List[OrderLineInput] = Field(min_length=1)


class StatusInput(BaseModel):
    status: str


class OrderOut(BaseModel):
    id: int
    order_code: str
    order_type: str
    table_code: Optional[str]
    customer_name: str
    student_id: Optional[str]
    address: Optional[str]
    phone_number: Optional[str]
    payment_method: str
    subtotal: int
    discount: int
    total: int
    cash_received: int
    status: str
    created_at: datetime
    items: List[Dict]

