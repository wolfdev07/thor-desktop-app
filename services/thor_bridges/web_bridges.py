import asyncio
from PySide6.QtCore import QObject, QThread, Signal, Slot

# Thor Imports
from utils.logger import app_logger
from services.finger_print.enroll_service import AsyncZKTecoReader

class HardwareBridge(QObject):
    # Señales para notificar a la UI/JS
    enrollmentSuccess = Signal(str, arguments=['uid'])
    enrollmentError = Signal(str, arguments=['message'])
    logMessage = Signal(str, arguments=['message'])
    
    # Señal interna para pedirle al hilo de fondo que trabaje
    requestEnrollment = Signal()

    def __init__(self):
        super().__init__()
        self.device_id = "ZK-SCANNER-01"
        self.version = "1.0.0"

    @Slot()
    def start_enrollment_from_js(self):
        """
        Este método es llamado desde JavaScript: window.thorBridge.start_enrollment_from_js()
        No bloquea, solo emite una señal al worker.
        """
        app_logger.info("UI solicitó enrolamiento")
        self.requestEnrollment.emit()

    def cleanup(self):
        """Llamado al cerrar la ventana"""
        pass

class AsyncWorker(QThread):
    # Señales de vuelta hacia el Bridge
    finished = Signal()
    
    def __init__(self, bridge: HardwareBridge):
        super().__init__()
        self.bridge = bridge
        self.loop = None
        self.reader = None
        self._is_running = True

    def run(self):
        """Este método se ejecuta en un hilo separado del sistema."""
        # Creamos un nuevo loop de eventos para este hilo
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)
        
        # Inicializamos el lector dentro del hilo correcto
        self.reader = AsyncZKTecoReader()
        
        # Conectamos la señal del Bridge para ejecutar la tarea asíncrona
        # Usamos call_soon_threadsafe para meter la tarea en el loop de asyncio
        self.bridge.requestEnrollment.connect(
            lambda: asyncio.run_coroutine_threadsafe(self._process_enrollment(), self.loop)
        )

        app_logger.info("Hilo de Hardware iniciado y esperando comandos...")
        
        # Corremos el loop indefinidamente hasta que se detenga
        self.loop.run_forever()

    async def _process_enrollment(self):
        """Lógica asíncrona de enrolamiento."""
        app_logger.info("Iniciando proceso de enrolamiento en background...")
        
        # Llamamos a tu servicio existente
        success, template = await self.reader.enroll()

        if success:
            app_logger.info("Enrolamiento exitoso en hilo de fondo")
            # Emitimos señal al Bridge (Thread-Safe automáticamente por Qt)
            self.bridge.enrollmentSuccess.emit("NuevoUsuario_UID") 
        else:
            app_logger.warning("Falló el enrolamiento")
            self.bridge.enrollmentError.emit("No se pudo capturar la huella o tiempo agotado")

    def stop(self):
        """Detiene el loop y el hilo de forma segura."""
        self._is_running = False
        if self.loop:
            self.loop.call_soon_threadsafe(self.loop.stop)
        self.quit()
        self.wait()