# 0J0 de T0GA

Sistema de Vigilancia Inteligente con IA - Procesador de stream MJPEG desde ESP32CAM/webcam con detección facial y de objetos en tiempo real.

## Características

- **Interfaz Web Moderna**: Controla todo desde el navegador (celular, tablet o PC)
- **Detección Facial**: Usa Haar Cascades con parámetros ajustables
- **Detección de Objetos**: MobileNet SSD con threshold configurable
- **Controles en Tiempo Real**: Sliders para ajustar sensibilidad, calidad, etc.
- **Stream en Vivo**: Visualización con bounding boxes en el navegador
- **Multi-dispositivo**: Accede desde cualquier dispositivo en la red

## Instalación

```bash
cd ojodetoga
./setup.sh
```

**Nota**: La primera ejecución descargará automáticamente los modelos MobileNet SSD (~20MB).

## Uso

### Opción 1: Interfaz Web (Recomendada)

```bash
./start.sh
```

Luego abre en tu navegador:
- **Local**: http://localhost:5000
- **Desde otro dispositivo**: http://`<ip-de-tu-laptop>`:5000

**Controles disponibles:**
- **Stream URL**: Cambiar la fuente de video (ESP32CAM, webcam IP, etc.)
- **Camera Mode**: Tipo de conexión (importante para ESP32CAM)
  - **Auto-detect**: Intenta detectar automáticamente
  - **ESP32CAM/MJPEG Stream**: Para ESP32CAM y cámaras con stream continuo
  - **Webcam IP/Single Capture**: Para apps de webcam en celular
- **Detección Facial**: Activar/desactivar detección de caras (afecta FPS)
- **Detección de Objetos**: Activar/desactivar detección de objetos (afecta FPS)
- **Confidence Threshold**: Sensibilidad de detección de objetos (0.1 - 1.0)
- **Face Scale Factor**: Precisión vs velocidad en detección facial
- **Min Neighbors**: Filtro de falsos positivos en caras
- **Frame Width**: Resolución del video (afecta FPS)
- **Target FPS**: Controla la fluidez vs el delay (5-30 FPS)
  - **Alto (20-30)**: Video más fluido pero más delay
  - **Medio (10-15)**: Balance (recomendado)
  - **Bajo (5-10)**: Menos delay pero video más cortado
- **Start/Stop**: Iniciar o detener el procesamiento

**💡 Para mejorar FPS (si se ve lento):**
1. **Desactivá Detección Facial y Objetos** - Ahora funcionan correctamente y saltan el procesamiento completamente
2. Bajá **Frame Width** a 480 o 320 (reduce resolución después de recibir)
3. Para bajar resolución de la cámara fuente: Probá agregar a la URL `?resolution=640x480` o similar (depende de la app)
4. Subí **Target FPS** a 20-30

**⚠️ Nota importante:** Las detecciones se desactivan completamente ahora (no solo el dibujado). Con ambas desactivadas, el procesamiento es instantáneo.

### Opción 2: Línea de Comandos (CLI)

```bash
# Con interfaz gráfica (ventana OpenCV)
python src/processor.py --url http://192.168.1.63:8080/video

# Modo consola (headless)
python src/processor.py --url http://192.168.1.63:8080/video --headless
```

**Controles CLI:**
- `--url`: URL del stream (default: http://192.168.1.48/)
- `--confidence`: Umbral de confianza 0.0-1.0 (default: 0.5)
- `--headless`: Sin ventana gráfica
- `q`: Salir (modo GUI)
- `Ctrl+C`: Salir (modo headless)

## Ejemplos de URLs

**ESP32CAM (CameraWebServer):**
- Stream MJPEG: `http://192.168.1.48:81/stream`
- Captura única: `http://192.168.1.48/capture`

**Webcam IP (Android):**
- IP Webcam: `http://192.168.1.63:8080/video`
- DroidCam: `http://192.168.1.63:4747/video`
- Iriun: `http://192.168.1.63:8080/mjpeg`

**RTSP/HTTP:**
- Cámaras IP: `http://usuario:pass@192.168.1.100:8080/video`

## Estructura

```
processing/ojodetoga/
├── src/
│   ├── processor.py           # Script CLI original
│   ├── stream_processor.py    # Procesador con controles dinámicos
│   ├── web_server.py          # Servidor Flask + WebSocket
│   └── templates/
│       └── index.html         # Interfaz web
├── requirements.txt           # Dependencias
├── setup.sh                   # Script de instalación
├── start.sh                   # Ejecutable principal (interfaz web)
└── README.md                  # Este archivo
```

## Clases detectadas (MobileNet SSD)

- **Personas**: person
- **Vehículos**: car, bus, motorbike, bicycle, aeroplane, boat, train
- **Animales**: cat, dog, bird, horse, cow, sheep
- **Objetos**: chair, sofa, diningtable, bottle, pottedplant, tvmonitor

**Total**: 20 clases + background

## Solución de problemas

### "No se conecta al stream"

1. Verificar que la URL es correcta probando en navegador
2. Asegurar que ESP32CAM/cámara esté en la misma red WiFi
3. Probar diferentes endpoints: `/stream`, `/video`, `/capture`, `/mjpeg`

### "ESP32CAM solo muestra el primer frame"

**Solución:** Seleccioná **"ESP32CAM / MJPEG Stream"** en el campo **Camera Mode** antes de iniciar.

La ESP32CAM usa un stream MJPEG continuo que requiere tratamiento especial. Si dejás en "Auto-detect" puede fallar.

### "Se congela después de unos segundos"

1. **Bajá el Target FPS** a 5-10
2. **Seleccioná el modo correcto** (Stream para ESP32, Capture para webcam)
3. Verificá la conexión WiFi de la cámara
4. Reiniciá la ESP32CAM

### "Bajo FPS"

1. **Bajar Frame Width** a 480 o 320
2. **Subir Confidence Threshold** a 0.7 (menos objetos a procesar)
3. **Usar escala más alta** en Face Scale Factor (1.3 o más)
4. Verificar conexión WiFi (señal débil = menos FPS)

### "No detecta caras"

1. **Bajar Face Scale Factor** a 1.05 o 1.1 (más sensible)
2. **Bajar Min Neighbors** a 3 o 4 (menos estricto)
3. Asegurar buena iluminación
4. Acercar la cara a la cámara

### "No detecta objetos"

1. **Bajar Confidence Threshold** a 0.3 o 0.4
2. Probar con objetos grandes y claros (person, car, chair)
3. Mejorar iluminación

### Interfaz web no carga

1. Verificar que el puerto 5000 no esté en uso: `lsof -i :5000`
2. Permitir firewall: `sudo ufw allow 5000/tcp`
3. Probar con IP local: `http://127.0.0.1:5000`

## Mejoras futuras

- [x] Interfaz web con controles en tiempo real
- [ ] Grabación de video automática
- [ ] Alertas cuando se detecte movimiento/personas
- [ ] Integración con API Laravel
- [ ] Soporte para múltiples cámaras simultáneas
- [ ] Dashboard con estadísticas históricas
- [ ] Reconocimiento facial (identificar personas específicas)

## Tips

1. **Para mejor FPS**: Usar resolución 640x480 o menor
2. **Para mejor detección**: Buena iluminación frontal
3. **Para webcam IP**: Apps como "IP Webcam" (Android) funcionan excelente
4. **Para ESP32CAM**: El stream en puerto 81 es más rápido que /capture

## Licencia

MIT - Libre para usar y modificar
