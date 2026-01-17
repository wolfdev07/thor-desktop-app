from typing import Optional
from PySide6.QtCore import Qt, QUrl, Slot, QEvent
from PySide6.QtWidgets import QMainWindow
from PySide6.QtWebEngineWidgets import QWebEngineView
from PySide6.QtWebEngineCore import QWebEnginePage, QWebEngineSettings
from PySide6.QtWebChannel import QWebChannel
from PySide6.QtGui import QCloseEvent

from utils.logger import app_logger
from config.settings import DEV_MODE

from ui.constants import QWEBCHANNEL_INIT_SCRIPT

class CustomWebPage(QWebEnginePage):
    """Maneja permisos y logs de la consola del navegador."""
    
    # Mapeo de niveles de log JS a Python
    LOG_LEVELS = {
        QWebEnginePage.JavaScriptConsoleMessageLevel.InfoMessageLevel: "INFO",
        QWebEnginePage.JavaScriptConsoleMessageLevel.WarningMessageLevel: "WARNING",
        QWebEnginePage.JavaScriptConsoleMessageLevel.ErrorMessageLevel: "ERROR"
    }

    # Permisos que aceptamos automáticamente
    AUTO_GRANT_PERMISSIONS = {
        QWebEnginePage.Feature.MediaAudioCapture,
        QWebEnginePage.Feature.MediaVideoCapture,
        QWebEnginePage.Feature.MediaAudioVideoCapture,
    }

    def javaScriptConsoleMessage(self, level, message, lineNumber, sourceID):
        """Redirige logs de JS al logger de Python."""
        if DEV_MODE:
            return
        
        log_level = self.LOG_LEVELS.get(level, "INFO")
        # Filtramos logs ruidosos si no estamos en DEBUG
        if "Thor" in message or DEV_MODE: 
            app_logger.debug(f"🌐 [JS-{log_level}] {message} (Línea: {lineNumber})")

    @Slot(QUrl, 'QWebEnginePage::Feature')
    def _on_feature_permission_requested(self, origin: QUrl, feature):
        """Gestor centralizado de permisos de hardware."""
        if feature in self.AUTO_GRANT_PERMISSIONS:
            app_logger.info(f"Permiso concedido auto: {feature} para {origin.host()}")
            self.setFeaturePermission(origin, feature, self.PermissionPolicy.PermissionGrantedByUser)
            return

        if feature == self.Feature.Geolocation and DEV_MODE:
            self.setFeaturePermission(origin, feature, self.PermissionPolicy.PermissionGrantedByUser)
            return

        app_logger.warning(f"Permiso denegado: {feature} para {origin.host()}")
        self.setFeaturePermission(origin, feature, self.PermissionPolicy.PermissionDeniedByUser)


class MainWebView(QMainWindow):
    """
    Ventana principal del navegador.
    Actúa como contenedor y orquestador entre Django y el Hardware.
    """
    
    def __init__(self, base_url: str, hardware_bridge=None, parent=None):
        super().__init__(parent)
        self.base_url = base_url.rstrip('/') 
        self.hardware_bridge = hardware_bridge
        self.channel = None
        self._init_ui()
        self._setup_webengine()
        self._setup_bridge()
        self._load_initial_url()

    def _init_ui(self):
        self.setWindowTitle("Thor Desktop Agent")
        self.resize(1800, 1080)
        
        self.web_view = QWebEngineView()
        self.setCentralWidget(self.web_view)
        
        # Conectamos la página personalizada
        self.custom_page = CustomWebPage(self.web_view)
        # Importante: conectar la señal de permisos en el __init__ de la página o aquí
        self.custom_page.featurePermissionRequested.connect(self.custom_page._on_feature_permission_requested)
        self.web_view.setPage(self.custom_page)

    def _setup_webengine(self):
        settings = self.web_view.settings()
        
        # Configuración Base
        attrs = {
            QWebEngineSettings.WebAttribute.LocalStorageEnabled: True,
            QWebEngineSettings.WebAttribute.JavascriptEnabled: True,
            # MEJORA DE FLUIDEZ:
            QWebEngineSettings.WebAttribute.Accelerated2dCanvasEnabled: True,
            QWebEngineSettings.WebAttribute.WebGLEnabled: True,
            QWebEngineSettings.WebAttribute.FocusOnNavigationEnabled: False,
        }

        for attr, value in attrs.items():
            settings.setAttribute(attr, value)

        if not DEV_MODE:
            self.web_view.setContextMenuPolicy(Qt.ContextMenuPolicy.NoContextMenu)

    def _setup_bridge(self):
        """Configura el puente Python <-> JS."""
        if not self.hardware_bridge:
            app_logger.warning("⚠️ Sin Hardware Bridge: Funciones nativas deshabilitadas.")
            return

        self.channel = QWebChannel()
        # Registramos el objeto 'backend' que JS podrá llamar
        self.channel.registerObject("backend", self.hardware_bridge)
        self.custom_page.setWebChannel(self.channel)
        
        app_logger.info("QWebChannel registrado correctamente.")

    def _load_initial_url(self):
        app_logger.info(f"Cargando aplicación: {self.base_url}")
        self.web_view.setUrl(QUrl(self.base_url))
        
        # Conexión de señales de carga
        self.web_view.loadFinished.connect(self._on_load_finished)

    @Slot(bool)
    def _on_load_finished(self, success: bool):
        if not success:
            app_logger.error("Fallo al cargar la página web.")
            return

        app_logger.info("Página cargada. Inyectando scripts del puente...")
        # Inyectamos el JS que inicializa 'window.thorBridge'
        self.custom_page.runJavaScript(QWEBCHANNEL_INIT_SCRIPT)

    def navigate_to(self, path: str):
        """Navegación segura concatenando rutas."""
        # Asegura que el path empiece con /
        if not path.startswith('/'):
            path = f"/{path}"
        
        full_url = f"{self.base_url}{path}"
        app_logger.info(f"Navegando a: {full_url}")
        self.web_view.setUrl(QUrl(full_url))

    def closeEvent(self, event: QCloseEvent):
        """Limpieza de recursos al cerrar la ventana."""
        app_logger.info("Cerrando Thor Desktop Agent...")
        
        # Desconectar hardware si es necesario
        if self.hardware_bridge and hasattr(self.hardware_bridge, 'cleanup'):
            self.hardware_bridge.cleanup()
            
        # Liberar recursos de WebEngine explícitamente suele ser buena práctica
        self.web_view.setPage(None)
        event.accept()