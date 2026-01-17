"""
Thor Desktop Agent - Main application entry point.
"""
import sys
import asyncio
import signal
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication

# Thor Imports
from models.db_manager import init_db
from services.thor_bridges.web_bridges import HardwareBridge, AsyncWorker
from ui.web_view import MainWebView


def main():
    # 1. Inicializar Base de Datos (Siempre antes de arrancar hilos)
    init_db()

    # 2. Configurar la aplicación Qt
    QApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
    )
    app = QApplication(sys.argv)
    
    # 3. Instanciar el Puente (Bridge)
    bridge = HardwareBridge()

    # 4. Iniciar el Hilo de Fondo (Worker)
    worker = AsyncWorker(bridge)
    worker.start()

    # 5. Iniciar la Ventana Principal (UI)
    # URL apuntando a tu servidor Django
    webview = MainWebView(
        base_url="http://localhost:8000", 
        hardware_bridge=bridge
    )
    
    # Manejo correcto de cierre (CTRL+C en terminal)
    signal.signal(signal.SIGINT, signal.SIG_DFL)

    # 6. Mostrar y Ejecutar
    webview.show()
    
    # Hook para limpiar el hilo cuando se cierra la ventana
    app.aboutToQuit.connect(worker.stop)
    
    sys.exit(app.exec())
    

if __name__ == "__main__":
    main()