# Thor Desktop Agent (Stormbreaker Version)🔨

**Agente de escritorio híbrido web-nativo para gestión de gimnasios con control biométrico.**

Thor es una aplicación de escritorio basada en **Qt WebEngine** (Chromium) que carga tu aplicación Django localmente, proporcionando acceso nativo al hardware (lectores de huella ZKTeco) mediante un puente JavaScript ↔ Python (QWebChannel).

## ✨ Características Principales

### 🌐 Arquitectura Híbrida
- **WebView Mode**: Interfaz 100% Django (HTML/CSS/JS)
- **Hardware Bridge**: Acceso a dispositivos biométricos desde JavaScript
- **QWebChannel**: Comunicación bidireccional Python ↔ JavaScript
- **Sistema Tray**: Notificaciones y control en segundo plano
- **Permisos WebRTC**: Acceso automático a cámara y micrófono desde JavaScript

### 🔐 Seguridad
- ✅ **Autenticación JWT** con Django (Valhalla API)
- ✅ **Device Fingerprinting** único por dispositivo
- ✅ **Keyring nativo** del sistema (Secret Service/Credential Vault)
- ✅ **Base de datos local encriptada** (SQLite + Fernet PBKDF2)
- ✅ **Comunicación segura** via QWebChannel (memoria interna)

### 📡 Conectividad
- ✅ **WebSocket Heimdall** - Eventos en tiempo real (enrollment, verificación)
- ✅ **Django REST API** - Autenticación y sincronización
- ✅ **Redis Pub/Sub** - Broadcasting multi-dispositivo

### 🖐️ Biometría
- ✅ **ZKTeco ZK9500 Integration** - Lector de huellas USB (producción)
- ✅ **4-touch enrollment** - Captura real de huellas con evaluación de calidad
- ✅ **Template consolidation** - Algoritmo de combinación de múltiples capturas
- ✅ **Verification** - Comparación de huellas con templates guardados
- 🔧 **Simulación 4-touch** - Modal de prueba (Verdadero/Falso) para desarrollo

---

## 🏗️ Nueva Arquitectura (Comunicación Directa)

```
┌─────────────────────────────────────────────────────────────┐
│                    Thor Desktop Agent                        │
│                  (PySide6 + QWebEngine)                      │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  ┌──────────────────────────────────────────────────┐      │
│  │         QWebEngineView (Chromium)                │      │
│  │   ┌──────────────────────────────────────────┐   │      │
│  │   │   Django App (localhost:8000)           │   │      │
│  │   │   • Login UI                            │   │      │
│  │   │   • Enrollment UI (JavaScript)          │   │      │
│  │   │   • Dashboard                           │   │      │
│  │   │   • Members Management                  │   │      │
│  │   └──────────────────────────────────────────┘   │      │
│  │              ▲                  │                 │      │
│  │              │ QWebChannel      │                 │      │
│  │              │ (Direct Memory)  ▼                 │      │
│  │   ┌──────────────────────────────────────────┐   │      │
│  │   │   HardwareBridge (Python @Slot)         │   │      │
│  │   │  ✅ iniciar_enrollment()                │   │      │
│  │   │  ✅ registrar_toque()                   │   │      │
│  │   │  ✅ verificar_huella()                  │   │      │
│  │   │  ✅ test_modal_nativo()                 │   │      │
│  │   │  📡 Signals: progress, completed        │   │      │
│  │   └──────────────────────────────────────────┘   │      │
│  └──────────────────────────────────────────────────┘      │
│                                                              │
│  ┌───────────────┐  ┌──────────────┐  ┌─────────────┐     │
│  │ WebSocket     │  │  SQLite DB   │  │ System Tray │     │
│  │ (Opcional)    │  │  (Encrypted) │  │             │     │
│  │ Notificaciones│  │              │  │             │     │
│  └───────────────┘  └──────────────┘  └─────────────┘     │
│                                                              │
└─────────────────────────────────────────────────────────────┘
         │                    │                   │
         ▼                    ▼                   ▼
    Heimdall WS         Valhalla API         ZKTeco SDK
   (Notificaciones)   (Autenticación)        (Futuro)

⚡ COMUNICACIÓN DIRECTA: JavaScript ↔ QWebChannel ↔ Python
   NO WebSocket intermediario para enrollment/verificación
   WebSocket SOLO para notificaciones push (opcional)
```

### Estructura del Proyecto

```
thor-desktop-app/
├── bridge/                    # 🌉 QWebChannel Bridge
│   └── hardware_bridge.py     #    Puente JS ↔ Python
├── ui/
│   ├── web_view.py           # 🌐 Navegador WebEngine
│   └── system_tray.py        # 📍 Bandeja del sistema
├── services/
│   ├── auth_service.py       # 🔐 Autenticación Django
│   ├── websocket_service.py  # 📡 Cliente WebSocket
│   └── websocket_manager.py  # 🔌 Manager + Signals Qt
├── core/
│   ├── database.py           # 💾 SQLite ORM
│   ├── encryption.py         # 🔒 Fernet + PBKDF2
│   └── device_fingerprint.py # 🆔 Device ID único
├── config/
│   ├── settings.py           # ⚙️  Configuración central
│   └── constants.py          # 📋 Constantes
├── examples/
│   ├── test_bridge.html      # 🧪 UI de prueba standalone
│   └── test_webview.py       # 🧪 Script de prueba
├── main.py                   # 🚀 Entry point
└── DJANGO_INTEGRATION.md     # 📚 Guía completa
```

---

## 🚀 Inicio Rápido

### 1. Instalación

```bash
# Activar entorno virtual
source env/bin/activate

# Instalar dependencias (INCLUYE WebEngine)
pip install -r requirements.txt

# Configurar .env
cp .env.example .env
```

### 2. Configurar `.env`

```env
# Modo desarrollo
DEV_MODE=true

# Django App URL (IMPORTANTE)
DJANGO_WEB_URL=http://localhost:8000

# APIs
API_BASE_URL=http://localhost:8000
HEIMDALL_WS_URL=ws://localhost:8080
```

### 3. Ejecutar

```bash
# Asegúrate que Django esté corriendo en puerto 8000
# En otra terminal: cd valhalla && python manage.py runserver 8000

# Iniciar Thor
python main.py
```

Thor abrirá una ventana de navegador cargando tu app de Django.

---

## 🔌 Integración con Django

### En tu template base de Django

```html
<!-- base.html -->
<script src="qrc:///qtwebchannel/qwebchannel.js"></script>
<script>
  // Inicializar bridge cuando esté disponible
  window.addEventListener('DOMContentLoaded', function() {
    if (typeof qt !== 'undefined' && qt.webChannelTransport) {
      new QWebChannel(qt.webChannelTransport, function(channel) {
        window.backend = channel.objects.backend;
        console.log('✅ Thor Hardware Bridge conectado');
        
        // Escuchar eventos de enrollment de Heimdall
        window.onThorEnrollmentRequest = function(data) {
          // Abrir modal de enrollment en tu UI
          openEnrollmentModal(data);
        };
      });
    }
  });
</script>
```

### Ejemplo: Registrar Huella (4 toques)

```javascript
// Cuando Heimdall envía evento "fingerprint_enroll"
function startEnrollment(requestId, memberNumber, memberName) {
  // 1. Iniciar enrollment en el bridge
  backend.iniciar_enrollment(requestId, memberNumber, memberName, 
    function(started) {
      if (started) {
        // Mostrar UI de enrollment
        showEnrollmentUI();
      }
    }
  );
}

// Usuario presiona botón "VERDADERO" o "FALSO"
function registerTouch(success) {
  backend.registrar_toque(success, function(resultJson) {
    const result = JSON.parse(resultJson);
    
    // Actualizar progreso visual
    updateProgress(result.successful_touches, 4);
    
    if (result.status === 'complete') {
      // ¡Enrollment completado!
      console.log('Token:', result.enrollment_token);
      closeEnrollmentUI();
    }
  });
}
```

**Ver guía completa**: [DJANGO_INTEGRATION.md](DJANGO_INTEGRATION.md)

---

## 🧪 Testing (Sin Django)

```bash
# Probar bridge con página HTML standalone
cd examples
python test_webview.py

# Se abrirá ventana con UI de prueba completa
# - Simular enrollment 4-touch
# - Ver progreso en tiempo real
# - Verificar signals Python ↔ JS
```

### 📷 Test de Cámara WebRTC

```bash
# Verificar permisos de cámara y micrófono
cd examples
python test_camera.py

# Funcionalidades del test:
# ✅ Solicitud automática de permisos (cámara + micrófono)
# ✅ Lista de dispositivos disponibles
# ✅ Cambio entre cámaras
# ✅ Captura de fotos
# ✅ Preview en tiempo real
```

**Permisos otorgados automáticamente**:
- 📷 Cámara (`MediaVideoCapture`)
- 🎤 Micrófono (`MediaAudioCapture`)
- 🎥 Cámara + Micrófono (`MediaAudioVideoCapture`)
- 📍 Geolocalización (solo en DEV_MODE)

---

## 📡 API del Hardware Bridge

### Métodos Disponibles en JavaScript

```javascript
// Device Info (properties)
backend.device_id    // "8bed4791c745..."
backend.version      // "1.0.0"

// Enrollment
backend.iniciar_enrollment(requestId, memberNumber, memberName, callback)
backend.registrar_toque(success, callback)  // success = true/false
backend.cancelar_enrollment(callback)

// Verificación (futuro)
backend.verificar_huella(memberNumber, callback)

// Utilidades
backend.mostrar_notificacion(title, message)
backend.obtener_estado(callback)
backend.log_debug(message)
```

### Signals (Eventos Python → JavaScript)

```javascript
// Progreso de enrollment
backend.enrollment_progress.connect(function(memberNumber, touchCount, success) {
  console.log(`Touch ${touchCount}: ${success ? 'OK' : 'FAIL'}`);
});

// Enrollment completado
backend.enrollment_completed.connect(function(memberNumber, token) {
  console.log(`✅ Token: ${token}`);
});

// Notificaciones
backend.notification.connect(function(title, message) {
  showToast(title, message);
});
```

---

## 🔐 Flujo de Autenticación

### Modo WebView (Actual)

1. **Thor inicia** → Carga `http://localhost:8000`
2. **Django verifica sesión**:
   - ✅ Tiene sesión → Muestra dashboard
   - ❌ No tiene sesión → Redirect a `/login`
3. **Usuario hace login en Django** → Django crea sesión
4. **Thor detecta login exitoso** → Conecta WebSocket a Heimdall
5. **Heimdall envía eventos** → Thor los inyecta en Django vía JavaScript

### Login desde Django

```javascript
// Después de login exitoso en tu frontend
if (window.backend) {
  backend.log_debug('User logged in successfully');
  
  // Thor detectará esto y conectará a Heimdall
  window.location.href = '/dashboard';
}
```

---

## 🌊 Flujo Completo de Enrollment

```
Valhalla Frontend
    │ POST /heimdall/api/v1/fingerprint/enroll
    ▼
Heimdall (FastAPI)
    │ Broadcast via Redis: fingerprint_enroll
    ▼
Thor WebSocket
    │ Recibe evento
    ▼
main.py: _on_fingerprint_enroll()
    │ JavaScript injection
    ▼
Django App (en WebView)
    │ window.onThorEnrollmentRequest(data)
    ▼
Usuario presiona "VERDADERO" (4 veces)
    │ backend.registrar_toque(true)
    ▼
HardwareBridge.registrar_toque()
    │ Guarda en DB local
    │ Envía progress a Heimdall
    ▼
Heimdall → Valhalla Frontend
    │ Actualiza UI en tiempo real
    ▼
4/4 toques completados
    │ enrollment_completed signal
    ▼
Django muestra éxito ✅
```

---

## 🗄️ Base de Datos Local

- **FingerprintEnrollment**: Registros de enrollment
  - `membership_number` (encriptado)
  - `enrollment_token` (UUID)
  - `touch_count` (1-4)

- **Member**: Cache de socios (futuro)
- **Setting**: Configuraciones de la app

**Encriptación**: Fernet con clave derivada de device fingerprint (PBKDF2)

---

## 📦 Dependencias Clave

```
PySide6==6.10.1               # Qt Framework
PySide6-WebEngine==6.10.1     # Chromium Browser (NEW!)
qasync==0.28.0                # Async Qt integration
websockets==16.0              # WebSocket client
cryptography==44.0.0          # Fernet encryption
keyring==26.2.1               # OS Keyring
SQLAlchemy==2.0.39            # ORM
```

---

## 🔧 Configuración Avanzada

### Modo Desarrollo vs Producción

```env
# Desarrollo (DEV_MODE=true)
DJANGO_WEB_URL=http://localhost:8000
# - DevTools habilitados (F12)
# - Menú contextual (click derecho)
# - Console logs visibles

# Producción (DEV_MODE=false)
DJANGO_WEB_URL=https://tu-dominio.com
# - DevTools deshabilitados
# - Sin menú contextual
# - Navegación bloqueada (no puede salir de tu app)
```

### System Tray Actions

- **Mostrar** → Trae WebView al frente
- **Cerrar Sesión** → Logout en Django + desconectar Heimdall
- **Salir** → Cierra Thor completamente

---

## 📝 Logs

```bash
# Logs de Thor
tail -f logs/thor_agent.log

# Buscar eventos de enrollment
grep "enrollment" logs/thor_agent.log

# Ver comunicación WebSocket
grep "WebSocket" logs/thor_agent.log
```

---

## 🐛 Troubleshooting

### "QWebChannel not available"
→ Asegúrate de cargar `qrc:///qtwebchannel/qwebchannel.js` en tu HTML

### "Backend undefined"
→ El bridge se inicializa después de DOMContentLoaded, usa evento `thor-ready`

### "Django no carga"
→ Verifica que Django esté corriendo: `curl http://localhost:8000`

### "WebSocket no conecta"
→ Verifica Heimdall: `curl http://localhost:8080/health`

---

## 🚀 Próximos Pasos

- [x] ✅ Arquitectura WebView + QWebChannel
- [x] ✅ Hardware Bridge funcional
- [x] ✅ Simulación 4-touch enrollment
- [x] ✅ Integración WebSocket Heimdall
- [ ] 🔜 ZKTeco SDK Integration (Live 20R, 9500)
- [ ] 🔜 Verificación biométrica en tiempo real
- [ ] 🔜 Sincronización automática con Django
- [ ] 🔜 Instalador Windows (.exe)
- [ ] 🔜 Firma digital de código

---

## 🌍 Platform Support

| OS      | Status | Keyring          | WebEngine |
|---------|--------|------------------|-----------|
| Linux   | ✅     | Secret Service   | ✅        |
| Windows | ✅     | Credential Vault | ✅        |
| macOS   | ⚠️     | Keychain         | ✅        |

---

## 📚 Documentación

- **[DJANGO_INTEGRATION.md](DJANGO_INTEGRATION.md)** - Guía completa de integración
- **[QUICKSTART.md](QUICKSTART.md)** - Inicio rápido paso a paso
- **[examples/test_bridge.html](examples/test_bridge.html)** - Código de ejemplo completo

---

## 🤝 Contribuir

1. Fork el proyecto
2. Crea una rama: `git checkout -b feature/mi-feature`
3. Commit: `git commit -am 'Add: nueva funcionalidad'`
4. Push: `git push origin feature/mi-feature`
5. Pull Request

---

## 📄 Licencia

Proyecto privado - Forza Gym Management System

---

**Desarrollado con ❤️ usando PySide6 + Qt WebEngine**
