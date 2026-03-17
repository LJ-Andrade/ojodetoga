# ESPECIFICACIÓN: Integración de MediaPipe y Selector de Modelos

## 📋 Resumen

Implementar soporte para **MediaPipe** como motor de detección facial alternativo al Haar Cascade actual, con un selector en la interfaz web para cambiar entre modelos en tiempo real.

## 🎯 Objetivos

1. **Agregar MediaPipe** como motor de detección facial (más preciso que Haar Cascade)
2. **Crear selector de modelos** en el panel de control (Haar vs MediaPipe)
3. **Mantener compatibilidad** con el sistema actual
4. **Actualizar requirements.txt** con nueva dependencia

## 📁 Archivos a Modificar

### 1. `requirements.txt`
**Ubicación:** `/home/leandro/LADev/ojodegato/processing/ojodetoga/requirements.txt`

**Acción:** Agregar al final:
```
mediapipe>=0.10.0
```

**Nota:** MediaPipe (~50MB) incluye modelos pre-entrenados, no requiere descargas adicionales.

---

### 2. `src/stream_processor.py`
**Ubicación:** `/home/leandro/LADev/ojodegato/processing/ojodetoga/src/stream_processor.py`

#### Cambio 2.1: Agregar import de MediaPipe
**Línea ~1:** Después de los imports existentes, agregar:
```python
import mediapipe as mp
```

#### Cambio 2.2: Agregar parámetro de modelo facial
**En `__init__()` método (línea ~14):**

Después de:
```python
self.camera_mode = camera_mode  # 'auto', 'stream', or 'capture'
```

Agregar:
```python
# Face detection model selection
self.face_model = 'haar'  # 'haar' or 'mediapipe'
```

#### Cambio 2.3: Modificar `_load_models()`
**Método `_load_models()` (línea ~44):**

Después de cargar Haar Cascade (línea ~48-49), agregar inicialización de MediaPipe:

```python
# MediaPipe Face Detection
self.mp_face_detection = mp.solutions.face_detection
self.mp_drawing = mp.solutions.drawing_utils
self.face_detection = None  # Se inicializa en detect_faces si es necesario
```

#### Cambio 2.4: Modificar `detect_faces()`
**Método `detect_faces()` (línea ~80):**

Reemplazar TODO el método con:

```python
def detect_faces(self, frame):
    """Detect faces with selected model."""
    if not self.enable_face_detection:
        return []
    
    if self.face_model == 'mediapipe':
        return self._detect_faces_mediapipe(frame)
    else:
        return self._detect_faces_haar(frame)

def _detect_faces_haar(self, frame):
    """Detect faces using Haar Cascade."""
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    faces = self.face_cascade.detectMultiScale(
        gray,
        scaleFactor=self.face_scale_factor,
        minNeighbors=self.face_min_neighbors,
        minSize=(30, 30)
    )
    return faces

def _detect_faces_mediapipe(self, frame):
    """Detect faces using MediaPipe."""
    # Initialize if needed
    if self.face_detection is None:
        self.face_detection = self.mp_face_detection.FaceDetection(
            model_selection=0,  # 0=short range, 1=full range
            min_detection_confidence=0.5
        )
    
    # Convert BGR to RGB (MediaPipe uses RGB)
    rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    
    # Process
    results = self.face_detection.process(rgb_frame)
    
    # Convert MediaPipe format to OpenCV format (x, y, w, h)
    faces = []
    if results.detections:
        h, w = frame.shape[:2]
        for detection in results.detections:
            bbox = detection.location_data.relative_bounding_box
            x = int(bbox.xmin * w)
            y = int(bbox.ymin * h)
            width = int(bbox.width * w)
            height = int(bbox.height * h)
            faces.append((x, y, width, height))
    
    return faces
```

#### Cambio 2.5: Actualizar `update_params()`
**Método `update_params()` (línea ~417):**

Después de:
```python
if 'enable_object' in kwargs:
    val = kwargs['enable_object']
    if isinstance(val, str):
        self.enable_object_detection = val.lower() == 'true'
    else:
        self.enable_object_detection = bool(val)
```

Agregar:
```python
if 'face_model' in kwargs:
    new_model = kwargs['face_model']
    if new_model in ['haar', 'mediapipe']:
        self.face_model = new_model
        # Reset MediaPipe instance if switching
        if new_model == 'haar':
            self.face_detection = None
        print(f"Face detection model changed to: {new_model}")
```

#### Cambio 2.6: Limpiar recursos al detener
**En `stop()` método:**

Agregar antes del return:
```python
# Clean up MediaPipe
if self.face_detection:
    self.face_detection.close()
    self.face_detection = None
```

---

### 3. `src/web_server.py`
**Ubicación:** `/home/leandro/LADev/ojodegato/processing/ojodetoga/src/web_server.py`

**Cambio 3.1:** Agregar mensaje de inicio actualizado
**Línea ~92:** Cambiar:
```python
print("🚀 Starting ESP32CAM Web Interface")
```
A:
```python
print("🚀 Starting 0J0 de T0GA - Sistema de Vigilancia Inteligente")
```

---

### 4. `src/templates/index.html`
**Ubicación:** `/home/leandro/LADev/ojodegato/processing/ojodetoga/src/templates/index.html`

#### Cambio 4.1: Agregar selector de modelo facial
**Ubicación:** Después de los toggles de detección (línea ~617), antes de "Configuración de Detección"

Agregar:
```html
<div class="control-group">
    <label class="control-label">Motor de Detección Facial</label>
    <select id="faceModel" style="width: 100%; padding: 12px; border: 2px solid rgba(0, 212, 255, 0.2); border-radius: 8px; background: rgba(20, 20, 35, 0.6); color: #e0e0e0;">
        <option value="haar">⚡ Haar Cascade (Rápido)</option>
        <option value="mediapipe">🎯 MediaPipe (Preciso)</option>
    </select>
    <small style="color: #888; font-size: 12px;">MediaPipe es más preciso pero consume más recursos</small>
</div>
```

#### Cambio 4.2: Agregar event listener
**Ubicación:** En la sección de event listeners (línea ~735)

Después de:
```javascript
document.getElementById('enableObject').addEventListener('change', function() {
    updateParams();
});
```

Agregar:
```javascript
document.getElementById('faceModel').addEventListener('change', function() {
    updateParams();
});
```

#### Cambio 4.3: Actualizar función `updateParams()`
**Función `updateParams()` (línea ~808):**

Agregar al objeto params:
```javascript
const params = {
    confidence: parseFloat(document.getElementById('confidence').value),
    scale_factor: parseFloat(document.getElementById('scaleFactor').value),
    min_neighbors: parseInt(document.getElementById('minNeighbors').value),
    frame_width: parseInt(document.getElementById('frameWidth').value),
    target_fps: parseInt(document.getElementById('targetFps').value),
    enable_face: document.getElementById('enableFace').checked,
    enable_object: document.getElementById('enableObject').checked,
    face_model: document.getElementById('faceModel').value  // NUEVO
};
```

---

## 🧪 Testing

### Test 1: Verificar instalación
```bash
./venv/bin/python -c "import mediapipe; print('MediaPipe OK')"
```

### Test 2: Verificar selector
1. Abrir interfaz web
2. Cambiar selector a "MediaPipe"
3. Verificar que detecta caras
4. Cambiar a "Haar Cascade"
5. Verificar que sigue funcionando

### Test 3: Rendimiento
Comparar FPS entre:
- Haar Cascade: ~15-20 FPS
- MediaPipe: ~10-15 FPS (más preciso)

## 📊 Comparación de Modelos

| Característica | Haar Cascade | MediaPipe |
|---------------|--------------|-----------|
| Precisión | ⭐⭐ | ⭐⭐⭐⭐ |
| Velocidad | ⚡⚡⚡ | ⚡⚡ |
| Tamaño | 1MB | 50MB (incluido) |
| Detección de angulos | Solo frontal | Frontal + perfil |
| Landmarks | No | Sí (opcional) |
| Sin conexión | ✅ | ✅ |

## ⚠️ Consideraciones Importantes

1. **Primera ejecución:** MediaPipe puede tardar ~5-10 segundos en cargar el modelo
2. **Memoria:** MediaPipe usa ~100MB más de RAM
3. **Formato de color:** MediaPipe usa RGB, OpenCV usa BGR (ya manejado en código)
4. **Coordenadas:** MediaPipe usa coordenadas relativas (0-1), convertir a píxeles

## 🚀 Plan de Implementación Sugerido

1. **Paso 1:** Actualizar `requirements.txt` y reinstalar dependencias
2. **Paso 2:** Modificar `stream_processor.py` (backend)
3. **Paso 3:** Modificar `index.html` (frontend)
4. **Paso 4:** Actualizar `web_server.py` (mensaje)
5. **Paso 5:** Testing completo

**Tiempo estimado:** 2-3 horas

## 📝 Notas para el Implementador

- Mantener Haar Cascade como opción por defecto (más rápida)
- MediaPipe se activa manualmente desde el selector
- Si hay errores con MediaPipe, fallback automático a Haar
- Los parámetros de Haar (scale_factor, min_neighbors) no aplican a MediaPipe
- MediaPipe tiene su propio parámetro de confianza (min_detection_confidence)

## ✅ Checklist de Verificación

- [ ] `requirements.txt` actualizado con mediapipe
- [ ] `stream_processor.py` tiene método `_detect_faces_mediapipe()`
- [ ] Selector en HTML funciona correctamente
- [ ] Cambio de modelo en tiempo real funciona
- [ ] FPS se mantiene aceptable (>10 FPS)
- [ ] Detección es visiblemente mejor con MediaPipe
- [ ] No hay errores en consola del navegador
- [ ] No hay errores en terminal del servidor

---

**Creado:** 2026-03-17
**Versión:** 1.0
**Estado:** Listo para implementación
