from models.db_manager import FingerPrintRepository

async def sync_database_to_reader(zk9500, repo: FingerPrintRepository):
    """Sincroniza los templates de SQLAlchemy con la memoria del dispositivo."""
    fps = repo.get_all()
    for fp in fps:
        # Add each fingerprint to the device memory
        zk9500.zkfp2.DBAdd(fp.id, fp.template)
    print(f"Sincronizadas {len(fps)} huellas al lector.")
