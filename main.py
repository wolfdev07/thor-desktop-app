"""Thor Desktop Agent - Main application entry point.
"""
import sys
import asyncio
from services.finger_print.enroll_service import AsyncZKTecoReader

async def main():
    reader = AsyncZKTecoReader()

    # Enroll a new fingerprint
    success, new_template = await reader.enroll()

    if success:
        print("¡Dedo registrado con éxito!")
        # Aquí guardarías 'new_template' en tu base de datos
    



if __name__ == "__main__":
    asyncio.run(main())
