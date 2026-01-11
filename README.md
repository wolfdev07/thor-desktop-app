# Thor Desktop Agent

Agente de escritorio para gestión de autenticación y control de dispositivos biométricos ZKTeco.

## Características

- ✅ **Autenticación JWT** con backend Django
- ✅ **Device Fingerprinting** único por dispositivo
- ✅ **Almacenamiento seguro** de tokens (keyring nativo del sistema)
- ✅ **Base de datos local encriptada** (SQLite + Fernet)
- ✅ **System Tray** - ejecuta en segundo plano
- ✅ **WebSocket** para eventos en tiempo real
- 🔜 **ZKTeco 9500** - control de lectores de huellas

## Arquitectura

```
thor-desktop-app/
├── config/          # Configuración (settings, constants)
├── core/            # Funcionalidad core
│   ├── device_fingerprint.py   # Generación de device ID
│   ├── encryption.py            # Encriptación Fernet
│   └── database.py              # ORM SQLite
├── services/        # Servicios externos
│   ├── auth_service.py          # API de autenticación
│   └── websocket_service.py     # Cliente WebSocket
├── ui/              # Interfaz PySide6
│   ├── login_window.py          # Ventana de login
│   └── system_tray.py           # Icono de bandeja
├── models/          # Modelos de datos
├── utils/           # Utilidades (logger, keyring)
└── main.py          # Punto de entrada
```

## Seguridad

- **Tokens**: Almacenados en keyring nativo (Secret Service/Credential Vault)
- **DB Encriptada**: Clave derivada con PBKDF2 del fingerprint del dispositivo
- **Datos sensibles**: Nombres, emails y huellas encriptados con Fernet
- **Auto-refresh**: Tokens se renuevan automáticamente

## Base de Datos Local

- **Member**: Socios (backend_id + datos encriptados)
- **Fingerprint**: Huellas biométricas encriptadas
- **Setting**: Configuraciones de la app

## Instalación

```bash
# Activar entorno virtual
source env/bin/activate

# Instalar dependencias
pip install -r requirements.txt

# Configurar variables de entorno
cp .env.example .env
# Editar .env con la URL de tu backend
```

## Uso

```bash
# Ejecutar en desarrollo
python main.py

# Compilar para distribución
pyinstaller --onefile --windowed \
  --name ThorDesktopAgent \
  main.py
```

## Configuración Backend

La app consume estos endpoints del backend Django:

- `POST /api/v1/desktop/auth/login` - Login con fingerprint
- `POST /api/v1/desktop/auth/refresh` - Renovar tokens
- `POST /api/v1/desktop/auth/logout` - Cerrar sesión
- `WS /ws/events` - WebSocket de eventos

Configurar en `.env`:
```
API_BASE_URL=http://localhost:8000
```

## Flujo de Autenticación

1. Usuario ingresa credenciales
2. App genera device fingerprint (UUID + CPU + MAC + OS)
3. Envía login al backend con fingerprint
4. Backend valida y retorna access_token + refresh_token + device_id
5. Tokens se almacenan en keyring del sistema
6. Access token se renueva automáticamente cada 10 min
7. App corre en system tray en segundo plano

## Próximos Pasos

- [ ] Integración con ZKTeco SDK
- [ ] Sincronización de huellas con backend
- [ ] Manejo de eventos WebSocket (verificación de acceso)
- [ ] UI de gestión de dispositivos
- [ ] Instalador para Windows

## Logs

Los logs se guardan en `logs/thor_agent.log` con rotación automática (10 MB).

## Platform Support

- **Linux**: ✅ Debian/Ubuntu (Secret Service)
- **Windows**: ✅ 10/11 (Credential Vault)
- **macOS**: ⚠️ Sin probar (debería funcionar con Keychain)
