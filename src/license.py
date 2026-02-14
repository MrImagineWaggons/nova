import uuid

def generate_license_key(plan: str) -> str:
    return f"NOVA-{plan.upper()}-{uuid.uuid4().hex[:16].upper()}"