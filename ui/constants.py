# Script de inicialización del puente (Inyectado en cada carga)
QWEBCHANNEL_INIT_SCRIPT = """
(function() {
    if (typeof QWebChannel !== 'function') {
        console.error('[Thor] ❌ QWebChannel.js no detectado. Revisa tu base.html');
        return;
    }
    if (typeof qt === 'undefined' || !qt.webChannelTransport) {
        console.warn('[Thor] ⚠️ Transporte Qt no disponible.');
        return;
    }
    
    new QWebChannel(qt.webChannelTransport, function(channel) {
        window.thorBridge = channel.objects.backend;
        
        // Disparar evento global cuando el puente esté listo
        const eventData = { 
            detail: { 
                bridge: window.thorBridge,
                deviceId: window.thorBridge.device_id,
                version: window.thorBridge.version
            },
            bubbles: true 
        };
        
        window.dispatchEvent(new CustomEvent('thor-ready', eventData));
        document.dispatchEvent(new CustomEvent('thor-ready', eventData));
        
        console.log('[Thor] ✅ Puente Hardware Conectado | ID:', window.thorBridge.device_id);
    });
})();
"""