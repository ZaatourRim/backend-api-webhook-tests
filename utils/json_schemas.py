# Schema for GET /api/users/{id} (user object inside "data")
USER_SCHEMA = {
    "type": "object",
    "required": ["data"],
    "properties": {
        "data": {
            "type": "object",
            "required": ["id", "email", "first_name", "last_name", "avatar"],
            "properties": {
                "id": {"type": "integer"},
                "email": {"type": "string", "format": "email"},
                "first_name": {"type": "string"},
                "last_name": {"type": "string"},
                "avatar": {"type": "string"}
            },
            "additionalProperties": True
        },
        "support": {
            "type": "object",
            "additionalProperties": True
        },
    },
    "additionalProperties": True
}

# Schema for POST /api/users creation response
CREATED_USER_SCHEMA = {
    "type": "object",
    "required": ["name", "job", "id", "createdAt"],
    "properties": {
        "name": {"type": "string"},
        "job": {"type": "string"},
        "id": {"type": "string"},
        "createdAt": {"type": "string", "format": "date-time"}
    },
    "additionalProperties": True
}

# Schema for error response like POST /api/login with missing password or email
ERROR_SCHEMA = {
    "type": "object",
    "required": ["error"],
    "properties": {
        "error": {"type": "string"}
    },
    "additionalProperties": True
}
