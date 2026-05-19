from bson import ObjectId
from typing import Any, Dict, List, Union, Optional

def bson_to_dict(doc: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    """Convert a MongoDB document's _id ObjectId to a string 'id'."""
    if doc is None:
        return None
    
    # Deep copy or mutate safely
    result = dict(doc)
    if "_id" in result:
        result["id"] = str(result["_id"])
        # Keep _id for DB references or delete it for Pydantic schema validation
        del result["_id"]
        
    # Recursively format nested list of dicts if any
    for key, value in result.items():
        if isinstance(value, ObjectId):
            result[key] = str(value)
        elif isinstance(value, list):
            result[key] = [str(item) if isinstance(item, ObjectId) else item for item in value]
            
    return result

def bson_list_to_dict_list(docs: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Convert a list of MongoDB documents to standard dicts."""
    return [bson_to_dict(doc) for doc in docs if doc is not None]

def to_object_id(id_str: Union[str, ObjectId]) -> ObjectId:
    """Convert a string ID to MongoDB ObjectId safely."""
    if isinstance(id_str, ObjectId):
        return id_str
    try:
        return ObjectId(id_str)
    except Exception:
        raise ValueError(f"Invalid ObjectId format: {id_str}")
