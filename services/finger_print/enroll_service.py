import asyncio
from typing import Optional, List, Tuple, Callable
from pyzkfp import ZKFP2
from models.db_manager import FingerPrintRepository, init_db
from utils.logger import app_logger

class AsyncZKTecoReader:
    def __init__(self):
        self.zkfp2 = None
        self.is_initialized = False
        self.is_connected = False
        self.init_db = False
    
    def initialize(self) -> bool:
        """Initialize the ZKTeco SDK."""
        try:
            if not self.is_initialized:
                try:
                    self.zkfp2 = ZKFP2()
                    self.zkfp2.Init()
                    self.is_initialized = True
                    init_db()
                    self.init_db = True
                except Exception as e:
                    app_logger.error(f"Error initializing ZKFP2 SDK: {e}")
                    return False
            
            count = self.zkfp2.GetDeviceCount()
            if count > 0:
                app_logger.info(f"Scanner ZKTeco detectado ({count} dispositivo(s))")
                return True
            app_logger.warning("No se detectaron dispositivos ZKTeco.")
            return False
        except Exception as e:
            app_logger.error(f"Error de inicialización: {e}")
            return False
    
    async def wait_for_finger(self, timeout: int = 20) -> Optional[bytes]:
        """Wait for a finger to be placed on the scanner and capture the fingerprint template."""
        start_time = asyncio.get_event_loop().time()

        while (asyncio.get_event_loop().time() - start_time) < timeout:
            capture = self.zkfp2.AcquireFingerprint()
            if capture:
                template, img = capture
                return template
            
            # Pausa mínima para no saturar el CPU, pero permite que otros 
            # procesos asíncronos se ejecuten.
            await asyncio.sleep(0.1)
        
        return None
    
    async def enroll(self, required_touches: int = 3) -> Tuple[bool, Optional[bytes]]:
        if not self.is_initialized and not self.initialize():
            return False, None
        
        try:
            self.zkfp2.OpenDevice(0)
            self.is_connected = True
            templates: List[bytes] = []

            app_logger.info(f"Iniciando enrolamiento: {required_touches} toques necesarios.")

            for i in range(required_touches):
                self.zkfp2.Light('green')
                app_logger.info(f"Toque {i+1}/{required_touches}: Coloque el dedo...")
                
                template = await self.wait_for_finger(timeout=15)

                if template:
                    templates.append(template)
                    app_logger.info(f"Toque {i+1} capturado.")
                    await asyncio.sleep(1.0)
                else:
                    return False, None
            
            if len(templates) >= 3:
                # DBMerge necesita 3 plantillas para crear una "RegTemplate" (consolidada)
                reg_temp, reg_temp_len = self.zkfp2.DBMerge(templates[0], templates[1], templates[2])

                if reg_temp:
                    app_logger.info(f"Plantilla consolidada generada correctamente.")
                    # Guardamos en DB
                    await self.enroll_persistence("artu", reg_temp)
                    return True, reg_temp
            
            return False, None

        except Exception as e:
            app_logger.error(f"Error durante enrolamiento: {e}")
            return False, None
        finally:
            if self.is_connected:
                self.zkfp2.CloseDevice()
                self.is_connected = False

    async def enroll_persistence(self, uid: str, consolidated_template: bytes):
        # Usamos un bloque try para asegurar que el repo se cierre
        repo = FingerPrintRepository()
        try:
            if self.is_initialized:
                # Guardar en SQLite vía SQLAlchemy
                user_fp = repo.save_fingerprint(uid, consolidated_template)
                
                # Cargar en la RAM del lector para identificación inmediata
                # IMPORTANTE: El dispositivo debe estar abierto para DBAdd
                self.zkfp2.DBAdd(user_fp.id, user_fp.template)
                
                app_logger.info(f"Persistencia exitosa: Usuario {uid} (ID DB: {user_fp.id})")
        except Exception as e:
            app_logger.error(f"Fallo en persistencia: {e}")
        finally:
            repo.close()