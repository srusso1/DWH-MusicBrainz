"""Cuenta filas y MBID distintos de la capa Bronze del lago local (parquet).

Uso (dentro del contenedor Spark):
  /opt/spark/bin/spark-submit /opt/app/streaming/inspeccionar_lago.py
Imprime una linea JSON: {"filas": N, "mbid_distintos": M, "particiones": [...]}.
"""

import json
import os

from pyspark.sql import SparkSession
from pyspark.sql import functions as F

ruta = os.getenv("RUTA_LAGO", "/opt/lake") + "/bronze/lanzamientos"
spark = SparkSession.builder.appName("dwmb-inspeccion-lago").getOrCreate()
spark.sparkContext.setLogLevel("ERROR")
# Leer por la ruta del sumidero respeta _spark_metadata: solo archivos confirmados.
df = spark.read.parquet(ruta)
fila = df.agg(F.count(F.lit(1)).alias("filas"), F.countDistinct("mbid").alias("distintos")).first()
particiones = [str(r[0]) for r in df.select("fecha_ingesta").distinct().collect()]
print("RESULTADO_LAGO " + json.dumps({"filas": fila["filas"], "mbid_distintos": fila["distintos"],
                                      "particiones": sorted(particiones)}))
spark.stop()
