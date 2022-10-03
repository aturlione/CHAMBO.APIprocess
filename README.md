# SATD-KATARI.Apiprocess

Api en la que se ejecutan geoprocesos.

## Hydrobid

Para la ejecución de hydrobid necesitamos tener los siguientes parámetros:

```
{
  "comid": 0,
  "url_opendap_data": "string",
  "variable_precipitation": "string",
  "variable_temperature": "string",
  "start_date": "string",
  "end_date": "string"
}
```


Todoos los parámetros son obligatorios.

Los datos se devuelven en formato JSON.

Se pueden pedir todos los datos llamando a Geoprocess/Hydrobid.

Se pueden pedir los datos individuales día, mes, año, llamando a Geoprocess/Hydrobid/daily, Geoprocess/Hydrobid/monthly, Geoprocess/Hydrobid/annual respectivamente.

## Regional stats

A partir de estos parámetros se pueden pedir los datos de estadísticas regionales.

```
{
  "product_id": 0,
  "geojson_region_to_clip": "string",
  "variable_name": "string"
}
```

Devuelve un JSON con los datos de estadísticas regionales (max, min, mean).