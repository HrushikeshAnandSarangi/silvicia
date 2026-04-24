import os
import tempfile
import requests
from qgis.core import (
    QgsVectorLayer,
    QgsProject,
    QgsVectorFileWriter,
    QgsCategorizedSymbolRenderer,
    QgsRendererCategory,
    QgsSymbol,
    QgsPalLayerSettings,
    QgsTextFormat,
    QgsVectorLayerSimpleLabeling,
    QgsWkbTypes,
    QgsFillSymbol
)
from qgis.utils import iface
from qgis.PyQt.QtGui import QColor

# Config
UPLOAD_URL = "http://localhost:8000/api/upload/"
GEOJSON_URL = "http://localhost:8000/api/tasks.geojson"

def upload_active_layer():
    # 1. Get the currently active layer in QGIS
    layer = iface.activeLayer()
    
    if not layer:
        print("Error: No layer selected. Please click on a vector layer in the Layers panel.")
        return
        
    if layer.type() != QgsVectorLayer.VectorLayer:
        print(f"Error: Selected layer '{layer.name()}' is not a vector layer.")
        return
        
    # Ask user if they want to clear the database first
    # For now, we'll just append to keep it simple, but we could make a DELETE request to /api/clear/ here.
    
    # 2. Export the layer to a temporary GeoJSON file
    temp_dir = tempfile.gettempdir()
    temp_path = os.path.join(temp_dir, f"{layer.name()}_upload.geojson")
    
    print(f"Exporting '{layer.name()}' to GeoJSON...")
    
    save_options = QgsVectorFileWriter.SaveVectorOptions()
    save_options.driverName = "GeoJSON"
    save_options.fileEncoding = "UTF-8"
    
    error, error_string = QgsVectorFileWriter.writeAsVectorFormatV2(
        layer, 
        temp_path, 
        QgsProject.instance().transformContext(), 
        save_options
    )
    
    if error != QgsVectorFileWriter.NoError:
        print(f"Failed to export layer: {error_string}")
        return
        
    file_size = os.path.getsize(temp_path)
    print(f"Exported {layer.featureCount()} features to GeoJSON ({file_size} bytes).")
    
    # 3. Upload the GeoJSON to the backend
    print("Uploading to Django backend...")
    try:
        with open(temp_path, 'rb') as f:
            files = {'file': (os.path.basename(temp_path), f, 'application/geo+json')}
            response = requests.post(UPLOAD_URL, files=files)
            
        if response.status_code == 200:
            msg = response.json().get('message', '')
            print(f"Server Response: {msg}")
            
            if "ingested 0 tasks" in msg:
                print("WARNING: The server processed the file but found 0 tasks. Check if your layer is empty or if edits need to be saved!")
                
            # Clean up temp file
            try:
                os.remove(temp_path)
            except:
                pass
                
            # 4. Connect the Live View automatically!
            connect_live_view()
        else:
            print(f"Upload failed (HTTP {response.status_code}): {response.text}")
    except Exception as e:
        print(f"Error connecting to backend: {str(e)}")


def connect_live_view():
    layer_name = "Live Task Pipeline"
    
    # Check if a layer with this name already exists, remove it if so
    existing_layers = QgsProject.instance().mapLayersByName(layer_name)
    for existing_layer in existing_layers:
        QgsProject.instance().removeMapLayer(existing_layer)
        
    layer = QgsVectorLayer(GEOJSON_URL, layer_name, "ogr")
    
    if not layer.isValid():
        print("Failed to load the Live View layer!")
        return
        
    QgsProject.instance().addMapLayer(layer)
    layer.setAutoRefreshInterval(1000)
    layer.setAutoRefreshEnabled(True)
    
    field_name = 'status'
    categories = []
    
    status_colors = {
        'PENDING': QColor(220, 53, 69),
        'PROCESSING': QColor(255, 193, 7),
        'COMPLETED': QColor(40, 167, 69)
    }
    
    for status, color in status_colors.items():
        geom_type = layer.geometryType()
        if geom_type == QgsWkbTypes.UnknownGeometry or geom_type == QgsWkbTypes.NullGeometry:
            geom_type = QgsWkbTypes.PolygonGeometry
            
        symbol = QgsSymbol.defaultSymbol(geom_type)
        if symbol is None:
            symbol = QgsFillSymbol.createSimple({'color': 'white'})
            
        symbol.setColor(color)
        if symbol.type() == QgsSymbol.Fill:
            symbol.symbolLayer(0).setStrokeColor(QColor("black"))
            symbol.symbolLayer(0).setStrokeWidth(0.2)
            
        category = QgsRendererCategory(status, symbol, status)
        categories.append(category)
        
    renderer = QgsCategorizedSymbolRenderer(field_name, categories)
    layer.setRenderer(renderer)
    
    settings = QgsPalLayerSettings()
    settings.fieldName = """CASE WHEN "worker_id" IS NOT NULL THEN 'Worker ' || "worker_id" ELSE '' END"""
    settings.isExpression = True
    
    text_format = QgsTextFormat()
    text_format.setSize(10)
    text_format.setColor(QColor("black"))
    
    buffer_settings = text_format.buffer()
    buffer_settings.setEnabled(True)
    buffer_settings.setSize(1)
    buffer_settings.setColor(QColor("white"))
    text_format.setBuffer(buffer_settings)
    settings.setFormat(text_format)
    
    labeling = QgsVectorLayerSimpleLabeling(settings)
    layer.setLabelsEnabled(True)
    layer.setLabeling(labeling)
    
    layer.triggerRepaint()
    print("Live view connected and automatically refreshing!")

# Execute the upload
upload_active_layer()
