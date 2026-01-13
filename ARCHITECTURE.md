# Arquitectura Modular de Thor Desktop Agent

## 📐 Principios de Diseño

El refactor de `main.py` sigue los principios **SOLID** y **Clean Architecture**:

- ✅ **Single Responsibility**: Cada clase tiene una responsabilidad única y bien definida
- ✅ **Open/Closed**: Abierto a extensión, cerrado a modificación
- ✅ **Liskov Substitution**: Las implementaciones son intercambiables
- ✅ **Interface Segregation**: Interfaces específicas y cohesivas
- ✅ **Dependency Inversion**: Dependencias hacia abstracciones, no implementaciones

---

## 🏗️ Estructura Modular

```
main.py (67 líneas)
    ↓
ThorDesktopAgent (Orquestador)
    ├── ApplicationController    (Qt Lifecycle)
    ├── SessionManager           (Authentication)
    ├── WebSocketEventHandler    (Heimdall Events)
    └── WebViewManager           (Django Integration)
```

### Antes (434 líneas monolíticas)
```python
class ThorDesktopAgent:
    - 20+ métodos en una sola clase
    - Responsabilidades mezcladas
    - Difícil de testear
    - Alto acoplamiento
```

### Después (Modular + Clean)
```python
main.py                         # 67 líneas - Solo orquestación
core/application_controller.py  # 95 líneas - Qt lifecycle
core/session_manager.py         # 141 líneas - Auth & sessions
core/websocket_event_handler.py # 107 líneas - Event delegation
core/webview_manager.py         # 149 líneas - WebView & Bridge
```

---

## 📦 Módulos

### 1. `core/application_controller.py`

**Responsabilidad**: Gestión del ciclo de vida de Qt y señales del sistema.

```python
class ApplicationController:
    """Manages Qt application initialization and lifecycle."""
    
    def initialize() -> tuple[QApplication, QEventLoop]
    def setup_signal_handlers(quit_callback)
    def check_system_tray_support() -> bool
    def run_event_loop() -> int
    def stop_event_loop()
```

**Funciones**:
- ✅ Inicializar `QApplication` y `QEventLoop`
- ✅ Configurar manejadores de señales Unix (SIGINT, SIGTERM)
- ✅ Validar soporte de system tray
- ✅ Limpiar credenciales en modo desarrollo
- ✅ Ejecutar y detener event loop

---

### 2. `core/session_manager.py`

**Responsabilidad**: Gestión de autenticación, sesión de usuario y conexión a Heimdall.

```python
class SessionManager:
    """Manages user session, authentication, and WebSocket connectivity."""
    
    def restore_existing_session() -> bool
    def logout(on_success: Callable = None) -> bool
    def confirm_logout() -> bool
    def confirm_quit() -> bool
```

**Funciones**:
- ✅ Restaurar sesión existente (validar token)
- ✅ Logout (local + Heimdall disconnect)
- ✅ Actualizar system tray con estado de usuario
- ✅ Diálogos de confirmación (logout, quit)
- ✅ Auto-conectar a Heimdall cuando hay sesión válida

---

### 3. `core/websocket_event_handler.py`

**Responsabilidad**: Delegación de eventos de WebSocket desde Heimdall.

```python
class WebSocketEventHandler:
    """Handles WebSocket events from Heimdall and delegates to appropriate handlers."""
    
    # Event handlers (configured externally)
    on_fingerprint_enroll: Callable
    
    # Auto-configured
    def _on_connected()
    def _on_disconnected()
    def _on_checkin(data: dict)
    def _on_verify_access(data: dict)
    def clear_enrollment(member_number: str)
```

**Funciones**:
- ✅ Conectar señales Qt a manejadores
- ✅ Prevenir enrollments duplicados (tracking set)
- ✅ Delegar eventos a handlers externos
- ✅ Mostrar notificaciones en system tray
- ✅ Logging estructurado de eventos

---

### 4. `core/webview_manager.py`

**Responsabilidad**: Gestión de WebView, Hardware Bridge y comunicación con Django.

```python
class WebViewManager:
    """Manages WebView window, hardware bridge, and Django app integration."""
    
    def create_webview() -> MainWebView
    def show_webview()
    def handle_enrollment_request(enrollment_data: dict)
    def trigger_django_logout()
    def reload_to_login()
    def close()
```

**Funciones**:
- ✅ Crear y mostrar ventana WebView
- ✅ Inicializar Hardware Bridge (QWebChannel)
- ✅ Inyectar JavaScript en Django app
- ✅ Manejar enrollment requests (forward a Django)
- ✅ Conectar notificaciones del bridge al system tray

---

### 5. `main.py` (Orquestador)

**Responsabilidad**: Coordinar todos los módulos - **Solo 67 líneas**.

```python
class ThorDesktopAgent:
    """Main application orchestrator - delegates to specialized managers."""
    
    def run() -> int:
        # Initialize Qt & event loop
        # Setup signal handlers
        # Check system tray
        # Initialize components
        # Show WebView
        # Restore session
        # Run event loop
    
    def _initialize_components():
        # WebSocket Manager
        # System Tray
        # Session Manager
        # WebSocket Event Handler
        # WebView Manager
    
    # Thin delegation methods
    def _on_fingerprint_enroll(enrollment_data)
    def _on_show_requested()
    def _on_logout_requested()
    def _on_quit_requested()
    def _quit()
```

**Características**:
- ✅ No lógica de negocio - solo coordinación
- ✅ Delega todo a managers especializados
- ✅ Fácil de leer y entender
- ✅ Testeable con mocks

---

## 🔄 Flujo de Ejecución

```
1. main() → ThorDesktopAgent()
        ↓
2. ApplicationController.initialize()
        ↓ (QApplication, QEventLoop)
3. ApplicationController.setup_signal_handlers(_quit)
        ↓
4. ApplicationController.check_system_tray_support()
        ↓
5. _initialize_components():
        ├── WebSocketManager()
        ├── SystemTray()
        ├── SessionManager(ws, tray)
        ├── WebSocketEventHandler(ws, tray)
        └── WebViewManager(ws, tray)
        ↓
6. WebViewManager.show_webview()
        ↓ (Django app loads)
7. SessionManager.restore_existing_session()
        ├── Validate token
        ├── Update tray
        └── Connect to Heimdall
        ↓
8. ApplicationController.run_event_loop()
        ↓ (User interactions)
9. System Tray Events:
        ├── Show → WebViewManager.show_webview()
        ├── Logout → SessionManager.logout()
        └── Quit → _quit()
```

---

## 🧪 Testabilidad

### Antes
```python
# Difícil de testear - todo mezclado
class ThorDesktopAgent:
    def run(self):
        # 100+ líneas con Qt, WS, Auth, WebView mezclados
```

### Después
```python
# Fácil de testear - cada módulo aislado
def test_session_manager():
    ws_mock = Mock(spec=WebSocketManager)
    tray_mock = Mock(spec=SystemTray)
    
    sm = SessionManager(ws_mock, tray_mock)
    assert sm.restore_existing_session() == False

def test_webview_manager():
    ws_mock = Mock()
    tray_mock = Mock()
    
    wm = WebViewManager(ws_mock, tray_mock)
    wm.handle_enrollment_request({"request_id": "123"})
    
    assert wm.hardware_bridge.iniciar_enrollment.called
```

---

## 📊 Métricas de Código

| Métrica | Antes | Después | Mejora |
|---------|-------|---------|--------|
| **Líneas en main.py** | 434 | 67 | ⬇️ 85% |
| **Responsabilidades** | 1 clase gigante | 5 módulos especializados | ✅ SOLID |
| **Acoplamiento** | Alto | Bajo | ✅ DI |
| **Testabilidad** | Difícil | Fácil | ✅ Mocks |
| **Legibilidad** | Baja | Alta | ✅ Clean |
| **Mantenibilidad** | Baja | Alta | ✅ Modular |

---

## 🎯 Beneficios

### ✅ **Separación de Responsabilidades**
- Cada módulo tiene un propósito claro
- Fácil ubicar dónde hacer cambios
- Reduce bugs por efectos colaterales

### ✅ **Reutilización**
- `SessionManager` puede usarse en otros proyectos
- `ApplicationController` es agnóstico al dominio
- `WebViewManager` es un patrón reutilizable

### ✅ **Testing**
- Módulos pequeños y testeables
- Mocks fáciles de inyectar
- Tests unitarios independientes

### ✅ **Escalabilidad**
- Agregar nuevos event handlers es trivial
- Extender funcionalidad sin modificar core
- Reemplazar implementaciones sin romper nada

### ✅ **Legibilidad**
- main.py se lee como pseudocódigo
- Cada archivo tiene <150 líneas
- Nombres descriptivos y autoexplicativos

---

## 🔍 Patrones Aplicados

### 1. **Facade Pattern**
`ThorDesktopAgent` es una fachada que simplifica el uso de múltiples subsistemas.

### 2. **Dependency Injection**
Todos los managers reciben sus dependencias como parámetros.

### 3. **Observer Pattern**
Qt Signals/Slots para comunicación entre componentes.

### 4. **Strategy Pattern**
`on_fingerprint_enroll` es configurable externamente.

### 5. **Single Responsibility Principle**
Cada clase tiene una razón única para cambiar.

---

## 📝 Cómo Extender

### Agregar nuevo evento WebSocket

```python
# 1. En core/websocket_event_handler.py
def _on_new_event(self, data: dict):
    """Handle new event from Heimdall."""
    app_logger.info(f"New event: {data}")
    
    if self.on_new_event:
        self.on_new_event(data)

# 2. En main.py
def _initialize_components(self):
    # ...
    self.ws_event_handler.on_new_event = self._on_new_event

def _on_new_event(self, data: dict):
    """Handle new event."""
    # Tu lógica aquí
```

### Agregar nueva funcionalidad a WebView

```python
# En core/webview_manager.py
def execute_custom_script(self, script: str):
    """Execute custom JavaScript in Django app."""
    if self.web_view:
        self.web_view.execute_javascript(script)
        app_logger.debug(f"Custom script executed: {script[:50]}...")

# Uso en main.py
self.webview_manager.execute_custom_script("alert('Hello!')")
```

---

## 🚀 Próximos Pasos

- [ ] Agregar tests unitarios para cada módulo
- [ ] Documentar API de cada manager
- [ ] Agregar type hints completos
- [ ] Crear interfaces abstractas (ABC)
- [ ] Implementar logging estructurado
- [ ] Agregar métricas de performance

---

**Desarrollado con ❤️ siguiendo Clean Architecture y SOLID principles**
