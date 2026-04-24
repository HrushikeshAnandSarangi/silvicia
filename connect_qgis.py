import urllib.request
from qgis.core import (
    QgsVectorLayer,
    QgsProject,
    QgsCategorizedSymbolRenderer,
    QgsRendererCategory,
    QgsSymbol,
    QgsPalLayerSettings,
    QgsTextFormat,
    QgsVectorLayerSimpleLabeling,
    QgsExpression
)
from qgis.PyQt.QtGui import QColor

def connect_to_backend():
    # 1. URL to our live GeoJSON endpoint
    url = "http://localhost:8000/api/tasks.geojson"
    
    # 2. Create the Vector Layer
    layer_name = "Live Task Pipeline"
    
    # Check if a layer with this name already exists, remove it if so
    existing_layers = QgsProject.instance().mapLayersByName(layer_name)
    for existing_layer in existing_layers:
        QgsProject.instance().removeMapLayer(existing_layer)
        
    # 'ogr' provider handles GeoJSON natively
    layer = QgsVectorLayer(url, layer_name, "ogr")
    
    if not layer.isValid():
        print("Failed to load the layer! Make sure the Django backend is running.")
        return
        
    # 3. Add layer to the project
    QgsProject.instance().addMapLayer(layer)
    
    # 4. Set up Auto-Refresh (Every 1000 milliseconds = 1 second)
    layer.setAutoRefreshInterval(1000)
    layer.setAutoRefreshEnabled(True)
    
    # 5. Apply Categorized Styling based on the 'status' property
    field_name = 'status'
    categories = []
    
    # Define colors for our statuses
    status_colors = {
        'PENDING': QColor(220, 53, 69),      # Bootstrap Red
        'PROCESSING': QColor(255, 193, 7),   # Bootstrap Yellow
        'COMPLETED': QColor(40, 167, 69)     # Bootstrap Green
    }
    
    for status, color in status_colors.items():
        from qgis.core import QgsWkbTypes, QgsFillSymbol
        geom_type = layer.geometryType()
        
        # If the backend is currently empty, QGIS won't know the geometry type.
        # We'll default to Polygon in that case.
        if geom_type == QgsWkbTypes.UnknownGeometry or geom_type == QgsWkbTypes.NullGeometry:
            geom_type = QgsWkbTypes.PolygonGeometry
            
        symbol = QgsSymbol.defaultSymbol(geom_type)
        
        # Absolute fallback just in case
        if symbol is None:
            symbol = QgsFillSymbol.createSimple({'color': 'white'})
            
        symbol.setColor(color)
        
        # Optional: Add an outline to make polygons look nicer
        if symbol.type() == QgsSymbol.Fill:  # Polygon/Fill symbol
            symbol.symbolLayer(0).setStrokeColor(QColor("black"))
            symbol.symbolLayer(0).setStrokeWidth(0.2)
            
        category = QgsRendererCategory(status, symbol, status)
        categories.append(category)
        
    renderer = QgsCategorizedSymbolRenderer(field_name, categories)
    layer.setRenderer(renderer)
    
    # 6. Add Labels to show the 'worker_id' when processing
    settings = QgsPalLayerSettings()
    # Use QGIS expression to show "Worker: X" or nothing
    settings.fieldName = """CASE WHEN "worker_id" IS NOT NULL THEN 'Worker ' || "worker_id" ELSE '' END"""
    settings.isExpression = True
    
    text_format = QgsTextFormat()
    text_format.setSize(10)
    text_format.setColor(QColor("black"))
    
    # Add a white buffer around the text so it's readable over geometries
    buffer_settings = text_format.buffer()
    buffer_settings.setEnabled(True)
    buffer_settings.setSize(1)
    buffer_settings.setColor(QColor("white"))
    text_format.setBuffer(buffer_settings)
    
    settings.setFormat(text_format)
    
    labeling = QgsVectorLayerSimpleLabeling(settings)
    layer.setLabelsEnabled(True)
    layer.setLabeling(labeling)
    
    # Trigger a redraw
    layer.triggerRepaint()
    print("Successfully connected QGIS to the live backend!")

# Execute the connection
connect_to_backend()
