import os
from qgis.core import (
    QgsProject,
    QgsVectorLayer,
    QgsFeatureRequest,
    QgsMapSettings,
    QgsMapRendererCustomPainterJob,
    QgsSingleSymbolRenderer,
    QgsLineSymbol,
    QgsRectangle
)
from qgis.PyQt.QtGui import QImage, QPainter, QColor
from qgis.PyQt.QtCore import QSize
from osgeo import gdal

# Define input shapefile and output folder
input_shapefile = "C:/Users/shubh/OneDrive/Desktop/sahara/Windhoek_Land_use_reprojected.shp"
output_folder = "C:/Users/shubh/OneDrive/Desktop/sahara/output_sat_hires"

# Load the shapefile
layer = QgsVectorLayer(input_shapefile, "Sub_saharan_african_cities", "ogr")
if not layer.isValid():
    print("Layer failed to load!")
    exit()

# Set the layer style to border only (no fill), with a red outline
symbol = QgsLineSymbol.createSimple({'color': 'red', 'width': '0.5'})
renderer = QgsSingleSymbolRenderer(symbol)
layer.setRenderer(renderer)

# Add the layer to the QGIS project (this includes any loaded basemaps)
QgsProject.instance().addMapLayer(layer)

# Define the scale (1:6464)
scale = 6464

# Set higher DPI for better resolution
dpi = 300  # Increased DPI from 96 to 300 for higher resolution

# Get the CRS of the layer
crs = layer.crs()

# Iterate over each feature in the layer
for feature in layer.getFeatures():
    # Get the geometry (polygon) and attributes for naming
    geom = feature.geometry()
    feature_id = feature["ID"]
    feature_label = feature["Label"]
    filename = f"{feature_id}_{feature_label}".replace(" ", "_")  # Replace spaces with underscores

    # Calculate the center of the geometry to set the extent
    center = geom.centroid().asPoint()

    # Calculate the map extent in map units (meters for projected CRS)
    # Adjusting the width and height calculation to maintain the same geographic area
    pixel_to_meter_conversion = scale / 96 * 0.0254  # Keep original pixel-to-meter conversion for the area
    map_width = 800 * pixel_to_meter_conversion
    map_height = map_width  # Keep image square

    half_width = map_width / 2
    half_height = map_height / 2

    extent = QgsRectangle(
        center.x() - half_width,
        center.y() - half_height,
        center.x() + half_width,
        center.y() + half_height
    )

    # Create a QgsMapSettings object
    map_settings = QgsMapSettings()
    map_settings.setLayers(QgsProject.instance().mapLayers().values())  # Include all layers in the project
    map_settings.setDestinationCrs(crs)
    map_settings.setExtent(extent)

    # Set the size of the output image
    # Increase image size to account for higher DPI and resolution
    image_size = QSize(3000, 3000)  # Increased from 800x800 to 3000x3000 for higher resolution
    map_settings.setOutputSize(image_size)
    map_settings.setOutputDpi(dpi)  # Set the DPI to the higher value

    # Create a QImage to render the map
    image = QImage(image_size, QImage.Format_RGB32)
    image.fill(QColor(255, 255, 255).rgb())  # Set background to white

    # Create a QPainter object
    painter = QPainter(image)

    # Create a map renderer job and render the image
    render_job = QgsMapRendererCustomPainterJob(map_settings, painter)
    render_job.start()
    render_job.waitForFinished()
    painter.end()

    # Define the output file path
    output_path = os.path.join(output_folder, f"{filename}.tiff")

    # Save the rendered image as a TIFF
    image.save(output_path, "TIFF")

    # Georeference the TIFF using GDAL
    ds = gdal.Open(output_path, gdal.GA_Update)
    gt = [
        extent.xMinimum(),  # top left x
        (extent.xMaximum() - extent.xMinimum()) / image_size.width(),  # w-e pixel resolution
        0,  # rotation, 0 if image is "north up"
        extent.yMaximum(),  # top left y
        0,  # rotation, 0 if image is "north up"
        (extent.yMinimum() - extent.yMaximum()) / image_size.height()  # n-s pixel resolution
    ]
    ds.SetGeoTransform(gt)
    ds.SetProjection(crs.toWkt())
    ds = None

print("Export and georeferencing completed.")
