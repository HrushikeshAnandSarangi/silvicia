import json
import zipfile
import os
import shutil
import tempfile
from django.shortcuts import render
from django.http import JsonResponse, HttpResponse
from django.views.decorators.csrf import csrf_exempt
import geopandas as gpd
from .models import Task
from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer

@csrf_exempt
def upload_project(request):
    if request.method == 'POST' and request.FILES.get('file'):
        uploaded_file = request.FILES['file']
        
        # Save securely to a temporary directory
        temp_dir = tempfile.mkdtemp()
        file_path = os.path.join(temp_dir, uploaded_file.name)
        with open(file_path, 'wb+') as destination:
            for chunk in uploaded_file.chunks():
                destination.write(chunk)
                
        extracted_data_file = None
        
        # If it's a QGZ, unzip and find the geopackage or shapefile
        if uploaded_file.name.endswith('.qgz') or uploaded_file.name.endswith('.zip'):
            extract_dir = os.path.join(temp_dir, 'extracted')
            with zipfile.ZipFile(file_path, 'r') as zip_ref:
                zip_ref.extractall(extract_dir)
                
            # Naively look for a geopackage or geojson
            for root, dirs, files in os.walk(extract_dir):
                for file in files:
                    if file.endswith('.gpkg') or file.endswith('.geojson') or file.endswith('.shp'):
                        extracted_data_file = os.path.join(root, file)
                        break
        else:
            extracted_data_file = file_path
            
        if not extracted_data_file:
            return JsonResponse({'error': 'No valid geospatial data found in the archive (.gpkg, .geojson, .shp)'}, status=400)
            
        try:
            # Read geometries
            gdf = gpd.read_file(extracted_data_file)
            gdf = gdf.to_crs(epsg=4326) # Make sure it is WGS84 for GeoJSON Map
            
            # Convert datetime columns to strings to avoid Timestamp JSON serialization errors
            for col in gdf.select_dtypes(include=['datetime64', 'datetimetz']).columns:
                gdf[col] = gdf[col].astype(str)
                
            # Convert to standard dictionary
            features = json.loads(gdf.to_json())['features']
            
            created_tasks = 0
            for feature in features:
                geom_str = json.dumps(feature['geometry'])
                props = feature.get('properties', {})
                Task.objects.create(
                    geometry=geom_str,
                    properties=props,
                    status='PENDING'
                )
                created_tasks += 1
                
            shutil.rmtree(temp_dir, ignore_errors=True) # Cleanup
            
            # Notify frontend of new tasks
            channel_layer = get_channel_layer()
            async_to_sync(channel_layer.group_send)(
                "dashboard",
                {"type": "send_update", "message": "Tasks uploaded"}
            )
            
            return JsonResponse({'message': f'Successfully ingested {created_tasks} tasks!'})
        except Exception as e:
            return JsonResponse({'error': f'Failed to process data: {str(e)}'}, status=500)
            
    return JsonResponse({'error': 'Invalid request'}, status=400)


@csrf_exempt
def clear_database(request):
    if request.method == 'DELETE' or request.method == 'POST':
        Task.objects.all().delete()
        
        # Notify via channels if running via Daphne cross-process (optional)
        channel_layer = get_channel_layer()
        async_to_sync(channel_layer.group_send)(
            "dashboard",
            {"type": "send_update", "message": "Database Purged"}
        )
        return JsonResponse({'message': 'Database completely erased.'})
    return JsonResponse({'error': 'Invalid request'}, status=400)

def tasks_geojson(request):
    tasks = Task.objects.all()
    features = []
    
    # QGIS expects numeric values or distinct strings to colorize.
    # We will compute a simple distinct color / state property
    state_map = {
        'PENDING': 0,
        'PROCESSING': 1,
        'COMPLETED': 2
    }
    
    for task in tasks:
        features.append({
            "type": "Feature",
            "geometry": json.loads(task.geometry),
            "properties": {
                "id": str(task.id),
                "status": task.status,
                "status_code": state_map.get(task.status, 0),
                "worker_id": task.worker_id,
                **task.properties
            }
        })
        
    fc = {
        "type": "FeatureCollection",
        "features": features
    }
    
    return JsonResponse(fc)

def dashboard(request):
    return render(request, 'dashboard.html')
