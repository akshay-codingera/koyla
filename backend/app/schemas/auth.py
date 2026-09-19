from pydantic import BaseModel
from typing import List, Optional

class Token(BaseModel):
    access_token: str
    token_type: str
    user: dict
    
class TokenData(BaseModel):
    username: Optional[str] = None
